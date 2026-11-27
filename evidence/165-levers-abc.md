# 165 — Three Measured Speed Levers (A, B, C) — 2026-11-27

> Interpreter for every command below: `/usr/bin/python3.14` (3.14.6).
> Box: 4 cores, shared co-tenant — load was 4.25–10.6 during these measurements
> (`uptime` read before/after each block). Every figure names the command that
> produced it; nothing here is derived from a previous run's artifact except the
> one row explicitly marked "baseline, this run did not re-derive".

## What actually dominates a pytest-form gate (finding, not a lever)

The brief's premise — boot 3.15s, logfire's plugin 2.11s of it — holds for a file
run OUTSIDE `tests/`, and is **wrong by 8x for a gate file**, because
`tests/conftest.py` runs an autouse session fixture on every run:

| Probe (all /usr/bin/python3.14, cwd=/root/ai-antispam) | Wall | Command |
|---|---|---|
| trivial file outside tests/, min-of-7, with logfire | **1.94s** | `/usr/bin/python3.14 -m pytest /tmp/bootprobe/test_ok2.py -q -p no:cacheprovider` ×7, min |
| same, `-p no:logfire -p no:pytest_logfire` | **0.86s** | same + flags, ×7, min |
| trivial file INSIDE tests/ (conftest runs) | **9.08–11.80s** | `/usr/bin/python3.14 -m pytest tests/test_zz_zz_trivial_probe.py -q -p no:cacheprovider [-p no:logfire -p no:pytest_logfire]` ×3 each (temp probe file, removed after) |
| same, collection only (`--co` — fixtures never run) | **1.20–1.23s** | same file, `--co` ×3 |
| `from app.common.llm_budget import validate_llm_config` + call | **7.73–8.70s** | `/usr/bin/python3.14 -c "import sys;sys.path.insert(0,'src');from app.common.llm_budget import validate_llm_config;validate_llm_config()"` ×2 |
| `-X importtime` on that import: `aiogram` alone | **6.70s of 6.74s** | `/usr/bin/python3.14 -X importtime -c ...` (largest cumulative row: `aiogram.types`) |

**The ~8s per gate session is `tests/conftest.py`'s autouse session fixture
`_validate_llm_config_for_test_session` importing `app.common.llm_budget` →
`app.common.utils` → `aiogram`, paid by every pytest-form gate and requested by
none of them.** This is the same class #165 already closed for `app.database` in
the same conftest; the fixture is the hole it left. Logfire's plugin is real but
small (~1.1s). This finding is what lever C's speedup actually is, and it is
also why lever A measures smaller than the brief predicted.

## Lever A — drop the logfire pytest plugin from GATE invocations — SHIPPED

Change: all 20 `-m pytest` registrations in `tools/audit.py` gained
`-p no:logfire -p no:pytest_logfire`. NOT a helper function — see the comment
block at `PYTEST_FORM_GATES` in `tools/audit.py` for the measured reason:
`tests/gate_registry.py::registration_entries` classifies a registration's
runner from the QUOTED literals of its own append, so a helper call renders as
`<expr>` and reads as script-form, failing the runner-form gate. A helper was
proven wrong before it was rejected: a synthetic append through the real parser
returned `runner=script`.

Scope held: the flags are in `tools/audit.py` only. `pytest.ini` addopts was
touched by nobody — the four non-gate files that import logfire
(`tests/common/test_logfire_lookup.py`, `tests/handlers/test_channel_management.py`,
`tests/handlers/test_status_handlers.py`, `tests/database/test_admin_operations.py`)
still load the plugins on their own runs.

| Measurement | With logfire | Without | Command |
|---|---|---|---|
| pytest boot, trivial file, min-of-7 | 1.94s | 0.86s | as in the table above |
| one gate, interleaved A/B, 3 pairs | 10.98/10.85/11.65s | 11.24/12.59/11.79s | `/usr/bin/python3.14 -m pytest tests/test_registry_attest.py -q --tb=no -p no:cacheprovider [flags]` |
| one gate, interleaved A/B, 3 pairs | 11.80/11.45/11.30s | 10.15/10.20/10.15s | same on tests/test_ledger_event_authorized.py |
| 20 pytest gates, full audit, summed | baseline **502.60s** (2026-11-27 13:47 artifact) | **247.37s** | full `tools/audit.py` run, per-gate rows summed (this run) |

**Honest reading:** the interleaved single-gate A/B shows the ~1.1s boot saving
DISAPPEARS into box noise (load 8–11; one "without" pair measured slower). The
credible per-run figure is the boot delta measured min-of-7 (~1.1s), and the
audit-level drop from 502.60s → 247.37s is mostly NOT lever A — it is box load
being lower today than at 13:47 (4–7 vs the earlier run's regime) plus the
conftest work already on HEAD. I cannot decompose those two cleanly with the
runs I have; the defensible lever-A-only claim is ~1.1s/session × 20 gates.

`_gate_wall_key` still resolves correctly with the extra flags — verified by
importing the audit module and probing:

```
key=tests/test_audit_rates.py     wall=90.0   (the mis-key-sensitive gate)
key=tests/test_registry_attest.py wall=150.0
key=tests/test_cron_thinness.py   wall=121.07
```

## Lever B — dedupe the identical `--help` spawn in test_sync_group_admins.py — SHIPPED

Change: a `@functools.cache`-memoised zero-argument helper
`_help_probe_from_repo_root()` wrapping the exact `["scripts/sync_group_admins.py",
"--help"]` probe that `test_cli_help_from_repo_root` and
`test_cli_dry_run_is_the_default` both run. Deliberately NOT a memo on
`_run_script`: `test_cli_help_via_pythonpath_only` uses a different cwd and env
and must keep its own run — the docstring in the test file states why a general
memo would make that test assert nothing.

| File total (`pytest tests/test_sync_group_admins.py -q --durations=5`) | Wall | Command |
|---|---|---|
| BEFORE (this run, pre-change) | **45.42s** | `/usr/bin/time -f "TOTAL %e" /usr/bin/python3.14 -m pytest tests/test_sync_group_admins.py -q --durations=5 -p no:cacheprovider` (16 passed in 38.19s; two `--help` probes 9.99s + 9.03s) |
| BEFORE, 3 more runs | 38.16 / 37.26 / 40.02s | same, no durations flag |
| AFTER | **29.51s** (16 passed in 25.28s) | same command post-change |
| AFTER, 3 more runs | 28.65 / 28.94 / 27.53s | same |

**56.5s from the brief was not reproduced on this tree/box; the measured before
is 37.3–45.4s. After: 27.5–29.5s. Saving ~10s, matching the removed duplicate
spawn.** Exit code 0 (pytest form). The file has no `__main__` at HEAD either, so
the script form was never a runner for it; not an audit gate, so no registration.

## Lever C — batch the 20 pytest-form gates — SHIPPED, DEFAULT OFF

Two artifacts: `tools/pytest_gate_batch.py` (the driver) and
`tests/test_audit_pytest_batch.py` (its correctness gate, registered script-form
in `tools/audit.py`). The audit runs the driver only when `AUDIT_PYTEST_BATCH`
is one of `1/true/yes/on`; default and anything unrecognised are OFF with a
warning, mirroring `AUDIT_GATE_WORKERS`' disposition.

### The measurements (all whole-command wall)

| Set | Wall | Command |
|---|---|---|
| 20 gates, unbatched, fresh interpreter each | **246.75s** | `/usr/bin/python3.14 /tmp/unbatched_baseline.py` (subprocess per gate, `-p no:cacheprovider -p no:logfire -p no:pytest_logfire`) |
| 20 gates, batched in one process | **68.71s** | `/usr/bin/python3.14 /tmp/count_probe.py` (pytest.main per file in-process) |
| same batch, repeat run | 73.24s | `/usr/bin/python3.14 /tmp/batch_counts.py` |
| 20 gates, fork-per-file (fork BEFORE warming) | **232.98s** | `/usr/bin/python3.14 /tmp/fork_driver.py` — rejected: no gain, each child re-pays the ~8s import |
| fork AFTER warming the parent | wedged | parent is multi-threaded once pytest has loaded (CPython warns; the run stalled) — rejected on evidence |
| **full audit, 66 gates, unbatched** | **369.39s** summed / 416.85s wall | `/usr/bin/python3.14 tools/audit.py` |
| **full audit, 66 gates, batched** | **199.25s** summed / 202.49s wall | `AUDIT_PYTEST_BATCH=1 /usr/bin/python3.14 tools/audit.py` |

### Verdict parity (the hard requirement)

* In-process batch vs one-process-per-file, per-file rc AND per-file pass/fail
  counts read from pytest's own terminal reporter, same session: **0
  divergences of 20**.
* Order sensitivity, full 20-gate loop forward then reversed: **0 rc
  divergences** (walls moved with box load: FWD total 241.79s vs REV 74.01s —
  the box is shared; treat wall numbers as ranges).
* **Full audit A/B, all 66 gates, both runs this session:** every gate's
  verdict identical — 64 PASS + 2 FAIL in both; **0 verdict divergences**. The
  2 FAILs are pre-existing tree state (`tools/hygiene.py --audit` flags the
  untracked `evidence/scores/165-accel-measure.md`; the cadence crosscheck gate
  flags the same filename), identical cause in both runs, unrelated to batching.
* Broken-file isolation, driven through the real driver: a failing file reports
  `exit_code: 1` as ITS OWN record and the healthy file after it still runs and
  passes. Asserted permanently in `tests/test_audit_pytest_batch.py` (bite
  proofs run: reverting the driver's loop to abort-on-failure makes the gate
  FAIL; defaulting the knob ON makes it FAIL; reporting a missing record as
  passed makes it FAIL).

### Why default OFF despite zero divergences

The win is amortising the ~8s `aiogram` import across files by sharing
`sys.modules`. That is non-hermeticity by construction: file N sees file 1's
module state. No divergence was observed on this tree, but this gate set's
sensitivity to fresh-import state is exactly what we cannot bound from one
afternoon of runs, so the knob ships OFF with the measurements in the driver's
docstring — the same call `AUDIT_GATE_WORKERS` made.

### Known limitations (stated, not hidden)

1. **No per-file timeout in batch mode.** A SIGALRM inside pytest surfaces as
   `1 failed` — a hang published as a verdict. The driver therefore offers no
   per-file bound; `_run_gate_set` applies ONE budget to the whole batch (sum of
   the files' declared walls: 2739.77s) and a file with no result line is
   reported UNKNOWN (`exit_code` 124, `unknown: True`,
   `duration_is_lower_bound: True`), never passed. This is a real regression
   against the unbatched path's per-gate retry, and it is priced into the OFF
   default.
2. `pytest.ini`'s `addopts = -m "not integration"` applies in batch mode as in
   single mode (both are pytest.main invocations of one file), so no behavioural
   difference there.
3. Wall figures on this box ranged widely between identical runs (see the
   forward/reverse totals); all claims above are ranges or single named runs,
   never min-of-N presented as typical.

## What I did NOT do

* Did not change `pytest.ini` addopts (would break four logfire-importing test files).
* Did not make the batch the audit default.
* Did not attempt the `AUDIT_GATE_WORKERS` concurrency knob; untouched.
* Did not touch `evidence/ledger.jsonl`, made no commits, closed nothing.
* Did not re-derive the 13:47 baseline; it is quoted as the artifact's own numbers.
* Did not verify the four logfire-importing test files under the batched driver
  (they are not gates; the flag never reaches them).
* The three files the brief named for exit codes:
  - `/usr/bin/python3.14 -m pytest tests/test_gate_registration.py -q` → **exit 5
    ("no tests ran")** in both plugin configurations — this file is a script-form
    gate (`main()` + `__main__`, registered as `[gate_python(),
    tests/test_gate_registration.py]`); pytest collects nothing from it. Script
    form: `/usr/bin/python3.14 tests/test_gate_registration.py` → **exit 0**
    ("gate registry passed", 274 PASS legs, 17 SKIPs).
  - `/usr/bin/python3.14 -m pytest tests/test_audit_pytest_batch.py -q` → **exit 0** (7 passed), and script form → **exit 0**.
  - `/usr/bin/python3.14 -m pytest tests/test_sync_group_admins.py -q` → **exit 0** (16 passed).
  - `/usr/bin/python3.14 tests/test_sync_group_admins.py` → exit 1, BOTH at HEAD
    and with my change (module-level `from app.database import ...` needs
    BOT_TOKEN; the file has no `__main__` and is not an audit gate, so this is
    out of scope — verified identical before my edit via `git stash`).
* ruff: `tools/audit.py` went from 39 findings at HEAD to 38 with my edits (no
  new lint class introduced; UP022/PLW1510 on my new `subprocess.run` fixed).
  New files match the shipped gates' existing lint baseline (EXE001/RUF100 also
  present on `tests/test_audit_yield.py`).
