#!/usr/bin/env python3
"""Run several pytest gate files in ONE interpreter, keeping per-file verdicts (#165 lever C).

WHY THIS EXISTS, and what the saving actually IS.

The premise this was built on -- "pytest boot is 3.15s and logfire's plugin is 2.11s of it"
-- is measurably WRONG for a gate file in this tree, and the difference matters because it
names the real cost:

    pytest boot, min-of-7, a trivial file OUTSIDE tests/     1.94s with logfire / 0.86s without
    the same trivial file INSIDE tests/ (tests/conftest.py)  9.08-11.80s
    that file, COLLECTION ONLY (`--co`, no fixtures run)     1.20-1.23s
    `from app.common.llm_budget import validate_llm_config`  7.73-8.70s
    `-X importtime` on that import: `aiogram` alone          6.70s of the 6.74s total

So ~8s of every gate session is `tests/conftest.py`'s autouse session fixture
`_validate_llm_config_for_test_session`, which imports `app.common.llm_budget` ->
`app.common.utils` -> `aiogram`. ZERO of the 20 pytest-form gates request it. That is the
same class #165 already closed for `app.database` in the same conftest, and this fixture is
the hole it left; it is NOT pytest boot and NOT the logfire plugin, both of which are ~1s.

Looping `pytest.main()` in one process does not remove that import, it AMORTISES it: the
module lands in `sys.modules` on the first file and every later file finds it there.
Measured over the 20 live pytest-form gates, whole-command wall, same box same session:

    unbatched (one subprocess per gate, fresh interpreter)   246.75s
    batched   (one process, pytest.main() per file)           68.71s   3.59x

THE TRADE, and why the audit's default stays OFF. Amortising the import makes the gates
NON-HERMETIC: file N runs with whatever module state file 1 left in `sys.modules`, so a
gate whose behaviour depended on a FRESH import would see a different world here than in
the unbatched audit. That is a real hazard for gates that touch shared state, and it is why
`AUDIT_PYTEST_BATCH` defaults to OFF with these numbers recorded beside it -- the same
disposition `AUDIT_GATE_WORKERS` was left at 1.

A FORK-PER-FILE driver was tried and REJECTED on measurement, both times:
  * fork before warming -> 232.98s over the same 20 gates, i.e. no gain at all: each child
    inherits a parent that never imported the fixture's target, so every child re-pays it;
  * fork AFTER warming the parent -> the parent is multi-threaded by the time pytest has
    loaded (Python itself warns "use of fork() may lead to deadlocks"), and the run wedged.

WHAT THIS DRIVER GUARANTEES -- each is asserted in `tests/test_audit_pytest_batch.py`:

  * ONE LINE OF JSON PER FILE on stdout, carrying that file's OWN return code and wall. A
    broken file is reported as THAT file failing; the loop does not abort and its
    neighbours still run. pytest's own progress output is captured, not printed, so the
    caller can parse stdout alone; its last line is carried as `output_tail` because a
    failing gate's cause lives there.
  * NO per-file timeout. This is a LIMITATION, stated rather than faked: pytest catches
    exceptions raised inside a test and records them as test FAILURES, so a SIGALRM fired
    to interrupt a hung file surfaced as `1 failed` (rc=1) -- a hang reported as a VERDICT,
    which is the one thing it must never be. The caller therefore applies ONE budget to the
    whole batch and treats any file with no result line as UNKNOWN, never as passed.

Exit: 0 whenever the driver ran to completion -- the verdicts are in the JSON, not in this
      exit code. 2 when invoked with nothing to run, because an empty batch that exits 0
      reads as "all gates passed".
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import time

# The audit's own kill code, mirrored rather than imported: this module must stay runnable
# as `python3 tools/pytest_gate_batch.py` without dragging `audit.py` in.
# `tests/test_audit_pytest_batch.py` asserts the two values are equal, so it cannot drift.
TIMEOUT_EXIT_CODE = 124

def run_one(path: str) -> dict:
    """Run ONE gate file through `pytest.main` in this process.

    In-process on purpose: that is what keeps the modules the first file imported resident
    for the rest, which is the entire speedup. The cost is the hermeticity stated above.
    """
    import pytest

    started = time.monotonic()
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        code = int(
            pytest.main(
                [path, "-q", "--tb=no", "-p", "no:cacheprovider",
                 "-p", "no:logfire", "-p", "no:pytest_logfire"]
            )
        )
    tail = [ln for ln in captured.getvalue().splitlines() if ln.strip()]
    return {
        "path": path,
        "exit_code": code,
        "duration_sec": round(time.monotonic() - started, 2),
        "output_tail": " ".join(tail[-1].split())[:200] if tail else "",
    }

def main(argv: list[str]) -> int:
    """`argv` is one or more gate file paths."""
    if not argv:
        print(
            "usage: pytest_gate_batch.py <gate file> [<gate file> ...] -- refusing an "
            "empty batch, which would exit 0 and read as all-pass",
            file=sys.stderr,
        )
        return 2
    for path in argv:
        print(json.dumps(run_one(path)), flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
