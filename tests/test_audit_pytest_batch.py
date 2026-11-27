#!/usr/bin/env python3
"""Gate: the batched pytest driver keeps per-file verdicts, and its audit wiring is OFF.

WHY THIS FILE EXISTS (#165 lever C). The audit can run its 20 pytest-form gates through ONE
interpreter (`tools/pytest_gate_batch.py`, behind `AUDIT_PYTEST_BATCH`). That is a 3.59x
wall-clock win -- measured 246.75s unbatched against 68.71s batched, whole-command wall over
the same 20 files on this box 2026-11-27 -- bought by sharing `sys.modules` between files.

A speedup that loses verdicts is worthless, so the properties that make it shippable are
asserted here rather than described:

  1. A BROKEN FILE IS REPORTED AS THAT FILE. The driver emits one JSON line per file with
     that file's OWN return code; the loop does not abort, and a healthy file AFTER the
     broken one still runs and still passes. Driven through the real driver with a real
     failing file, not a stub.
  2. THE AUDIT'S KNOB IS OFF BY DEFAULT. `AUDIT_PYTEST_BATCH` unset, `0`, and a typo all
     read False; only the four affirmative spellings read True. A default that flipped
     silently would make every audit non-hermetic without anyone asking.
  3. A FILE WITH NO RESULT LINE IS UNKNOWN, NEVER PASSED. That is what happens when the
     batch wall kills the driver, and reporting it as a pass would be the exact fabricated
     green the audit's three-state verdict exists to prevent.
  4. THE AUDIT'S RESULT SHAPE IS `run_gate`'s. The report, the score arithmetic and the
     verdict all read the per-gate dicts positionally, so a batched result missing a key
     would break a surface far from here.
  5. THE TIMEOUT CODE IS THE AUDIT'S OWN, not a second constant that can drift.

The BATCH ITSELF IS NOT RUN IN THIS GATE. Running 20 gate files from inside a gate is the
recursion #165 already avoids (`--no-gates` exists for it), and the 3.59x is a measurement
recorded in `evidence/165-levers-abc.md`, not a property a gate can re-assert cheaply. What
this gate holds is the CORRECTNESS contract, which is cheap and is what could regress.

Run:  python3 -m pytest tests/test_audit_pytest_batch.py -q
Exit: 0 clean, non-zero on any regression in the driver's per-file contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DRIVER = REPO / "tools" / "pytest_gate_batch.py"

sys.path.insert(0, str(REPO / "tools"))

# The audit's own kill code, read from the module that OWNS it. The driver mirrors it (it
# must stay importable without dragging `audit.py` in), and clause 5 is that the mirror
# cannot drift.
from gate_budget import TIMEOUT_EXIT_CODE as AUDIT_TIMEOUT_EXIT_CODE  # noqa: E402

def _load_audit():
    """`tools/audit.py` itself, registered before exec (`@dataclass` needs `sys.modules`)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("audit_batch_under_test", REPO / "tools" / "audit.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["audit_batch_under_test"] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop("audit_batch_under_test", None)
        raise
    return mod

def _load_driver():
    import importlib.util

    spec = importlib.util.spec_from_file_location("pytest_gate_batch_under_test", DRIVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pytest_gate_batch_under_test"] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop("pytest_gate_batch_under_test", None)
        raise
    return mod

def check_a_broken_file_is_reported_as_that_file() -> list[str]:
    """Clause 1: the driver keeps per-file verdicts and survives a failure.

    The fixture files are written into a temp dir and run through the REAL driver as a
    subprocess, because the property is about what the driver PRINTS, and a stub that
    returned the same dict would prove nothing about the printed contract.
    """
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="batch-verdict-") as td:
        root = Path(td)
        broken = root / "test_deliberately_broken.py"
        broken.write_text("def test_fails():\n    assert False, 'deliberate'\n", encoding="utf-8")
        healthy = root / "test_healthy_after.py"
        healthy.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(DRIVER), str(broken), str(healthy)],
            cwd=str(REPO), capture_output=True, text=True, timeout=180,
        )
        if res.returncode != 0:
            return [f"the driver exited {res.returncode} on a normal run: {res.stderr[-300:]}"]

        records = {}
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                rec = json.loads(line)
                records[rec["path"]] = rec

        if str(broken) not in records:
            problems.append("the broken file produced NO record -- its verdict was lost")
        elif records[str(broken)]["exit_code"] == 0:
            problems.append("the broken file was reported as PASSING")

        if str(healthy) not in records:
            problems.append(
                "the healthy file AFTER the broken one produced no record -- the loop "
                "aborted on the failure instead of carrying on"
            )
        elif records[str(healthy)]["exit_code"] != 0:
            problems.append("the healthy file was reported as failing")

        # The population is asserted non-empty: a driver that printed nothing at all would
        # otherwise satisfy every `not in records` arm above by way of an empty dict.
        if len(records) != 2:
            problems.append(f"expected 2 records, got {len(records)}: {sorted(records)}")
    return problems

def check_the_knob_is_off_by_default() -> list[str]:
    """Clause 2: unset / `0` / a typo read False; the four affirmative spellings read True."""
    problems: list[str] = []
    audit = _load_audit()
    prior = os.environ.get("AUDIT_PYTEST_BATCH")

    def _read(value: str | None) -> bool:
        if value is None:
            os.environ.pop("AUDIT_PYTEST_BATCH", None)
        else:
            os.environ["AUDIT_PYTEST_BATCH"] = value
        return audit._pytest_batch_enabled()

    try:
        if _read(None) is not False:
            problems.append("AUDIT_PYTEST_BATCH unset did NOT read False -- the default moved")
        for falsy in ("0", "false", "no", "off", ""):
            if _read(falsy) is not False:
                problems.append(f"AUDIT_PYTEST_BATCH={falsy!r} did NOT read False")
        for typo in ("2", "maybe", "ture"):
            if _read(typo) is not False:
                problems.append(f"AUDIT_PYTEST_BATCH={typo!r} (a typo) did NOT fall back to False")
        for truthy in ("1", "true", "yes", "on", "TRUE", "On"):
            if _read(truthy) is not True:
                problems.append(f"AUDIT_PYTEST_BATCH={truthy!r} did NOT read True")
    finally:
        if prior is None:
            os.environ.pop("AUDIT_PYTEST_BATCH", None)
        else:
            os.environ["AUDIT_PYTEST_BATCH"] = prior
    return problems

def check_a_missing_record_is_unknown_never_passed() -> list[str]:
    """Clause 3: no record for a file is UNKNOWN (the kill code + `unknown`), not a pass."""
    problems: list[str] = []
    audit = _load_audit()
    cmd = [sys.executable, "-m", "pytest", "tests/test_registry_attest.py", "-q"]
    res = audit._batched_result(cmd, None, 150.0)
    if res["passed"] is not False:
        problems.append("a file with NO record read as passed -- a kill published as a verdict")
    if res.get("unknown") is not True:
        problems.append("a file with NO record did not carry unknown=True")
    if res["exit_code"] != AUDIT_TIMEOUT_EXIT_CODE:
        problems.append(
            f"a file with NO record carried exit_code {res['exit_code']}, expected the kill "
            f"code {AUDIT_TIMEOUT_EXIT_CODE}"
        )
    if not res.get("duration_is_lower_bound"):
        problems.append("a killed file's duration was NOT marked a lower bound")

    # The DISCRIMINATING arm: a real record with a real exit is a verdict, not UNKNOWN. A
    # predicate that answered UNKNOWN unconditionally would pass every arm above.
    ok = audit._batched_result(cmd, {"path": "x", "exit_code": 0, "duration_sec": 1.5}, 150.0)
    if ok["passed"] is not True or ok.get("unknown") is not False:
        problems.append(f"a clean batched record did not read as a pass: {ok}")
    failed = audit._batched_result(cmd, {"path": "x", "exit_code": 1, "duration_sec": 1.5}, 150.0)
    if failed["passed"] is not False or failed.get("unknown") is not False:
        problems.append(f"a genuine non-zero exit was not a plain FAIL: {failed}")
    return problems

def check_the_batched_result_has_run_gates_shape() -> list[str]:
    """Clause 4: the batched dict carries every key the reporting surfaces read."""
    problems: list[str] = []
    audit = _load_audit()
    cmd = [sys.executable, "-m", "pytest", "tests/test_registry_attest.py", "-q"]
    required = (
        "cmd", "exit_code", "passed", "unknown", "duration_sec",
        "duration_is_lower_bound", "budget_sec", "attempts", "retried", "stdout", "stderr",
    )
    for label, record in (
        ("a real record", {"path": "x", "exit_code": 0, "duration_sec": 1.0}),
        ("no record", None),
    ):
        got = audit._batched_result(cmd, record, 150.0)
        missing = [k for k in required if k not in got]
        if missing:
            problems.append(f"{label} is missing {missing}")
        if got.get("cmd") != " ".join(cmd):
            problems.append(f"{label} does not carry the command it describes")
    return problems

def check_the_timeout_code_is_the_audits_own() -> list[str]:
    """Clause 5: the driver's mirrored kill code equals the audit's."""
    problems: list[str] = []
    driver = _load_driver()
    if driver.TIMEOUT_EXIT_CODE != AUDIT_TIMEOUT_EXIT_CODE:
        problems.append(
            f"the driver mirrors {driver.TIMEOUT_EXIT_CODE} but the audit uses "
            f"{AUDIT_TIMEOUT_EXIT_CODE} -- a second constant that has drifted"
        )
    return problems

def check_an_empty_batch_is_refused() -> list[str]:
    """An empty batch must exit 2, not 0 -- an empty map reads as "all gates passed"."""
    problems: list[str] = []
    res = subprocess.run(
        [sys.executable, str(DRIVER)], cwd=str(REPO), capture_output=True, text=True, timeout=60
    )
    if res.returncode != 2:
        problems.append(f"an empty batch exited {res.returncode}, expected 2")
    if res.stdout.strip():
        problems.append("an empty batch printed to STDOUT -- a caller would read an empty map")
    return problems

def check_the_registration_is_structurally_read() -> list[str]:
    """`_is_pytest_form` reads the `-m pytest` PAIR, never a substring of a filename."""
    problems: list[str] = []
    audit = _load_audit()
    cases = [
        ([sys.executable, "-m", "pytest", "tests/test_audit_rates.py", "-q"], True),
        # A FILENAME containing "pytest" under a script runner is NOT pytest form.
        ([sys.executable, "tests/test_pytest_form.py"], False),
        ([sys.executable, "tools/ledger.py", "verify"], False),
    ]
    for cmd, expected in cases:
        got = audit._is_pytest_form(cmd)
        if got is not expected:
            problems.append(f"_is_pytest_form({cmd[1:]}) = {got}, expected {expected}")
    return problems

# --- pytest wrappers -------------------------------------------------------

def test_a_broken_file_is_reported_as_that_file() -> None:
    assert check_a_broken_file_is_reported_as_that_file() == []

def test_the_knob_is_off_by_default() -> None:
    assert check_the_knob_is_off_by_default() == []

def test_a_missing_record_is_unknown_never_passed() -> None:
    assert check_a_missing_record_is_unknown_never_passed() == []

def test_the_batched_result_has_run_gates_shape() -> None:
    assert check_the_batched_result_has_run_gates_shape() == []

def test_the_timeout_code_is_the_audits_own() -> None:
    assert check_the_timeout_code_is_the_audits_own() == []

def test_an_empty_batch_is_refused() -> None:
    assert check_an_empty_batch_is_refused() == []

def test_the_registration_is_structurally_read() -> None:
    assert check_the_registration_is_structurally_read() == []

# --- standalone entry point -------------------------------------------------

def main() -> int:
    checks = [value for name, value in sorted(globals().items()) if name.startswith("check_")]
    problems: list[str] = []
    for check in checks:
        found = check()
        if found:
            problems.extend(f"{check.__name__}: {p}" for p in found)
    if problems:
        print(f"pytest-batch driver guard FAILED ({len(problems)} problem(s)):")
        for p in problems:
            print(f"  {p}")
        return 1
    print(
        f"pytest-batch driver guard clean: {len(checks)} check(s) -- per-file verdicts "
        f"survive a failure, the knob is off by default, a missing record is UNKNOWN"
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
