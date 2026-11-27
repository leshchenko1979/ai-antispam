# Audit acceleration — working state (issue #165)

## Board
Issue **#165** filed on leshchenko1979/ai-antispam. Title prefix `[work]`.
URL from create stdout: https://github.com/leshchenko1979/ai-antispam/issues/165

## Baseline (2026-11-27)
- Audit: 1626 s, 65 gates.
- `tests/test_questions.py` 1028.81 s (63%).
- `test_ledger.py` 84.06 s. Then pytest-form gates 12.79–50.28 s each.

## Lever 2 — DONE, and root-caused deeper than the brief
Brief said: move `from app.database import (...)` out of conftest module level.
Measured reality: that was only HALF the cost.

**Two separate costs found in `tests/conftest.py`:**
1. Module-level `from app.database import (Administrator, create_schema,
   drop_and_create_database, postgres_connection)` + `from app.database.models import
   ModerationMode` + `from aiogram.exceptions import TelegramBadRequest`.
   `import app.database` = 9.47–11.95 s; `aiogram.types` alone 5.6–6.7 s.
2. **The bigger one, not in the brief:** `pytest_sessionfinish` called
   `mute_logging_for_tests()` UNCONDITIONALLY, which does
   `from app.logging_setup import mute_logging_for_tests` -> `app.logging_setup` imports
   `app.common.bot` -> `aiogram` at the END of EVERY pytest session, including all ~60
   gate sessions that never touch an app module. Bisect measured: 1-test collection-only
   run = **42.18 s** with that hook's import, **2.74 s** without. ~10 s/session wasted.

### Edits made to tests/conftest.py
- Module-level app.database import block -> removed, replaced with a long comment
  explaining the cost + why lazy. Names moved into the fixtures that use them:
  - `create_test_database`: `from app.database import create_schema, drop_and_create_database`
    inside the PostgreSQL branch only (after the SQLite early return).
  - `patched_db_conn`: `from app.database import postgres_connection` in the body.
  - `sample_user`: `from app.database import Administrator` +
    `from app.database.models import ModerationMode` in the body.
  - `patched_get_pool` already had its own function-local import — untouched.
- `from aiogram.exceptions import TelegramBadRequest` + `class MockTelegramBadRequest`
  -> replaced by a PEP 562 module `__getattr__` that builds the class on first request
  and caches it in `globals()`. Only user is `tests/handlers/test_spam_handlers.py`
  (NOT a gate — 0 hits in tools/audit.py).
- `pytest_sessionfinish` -> captures `had_integration = _session_has_integration` BEFORE
  resetting it; env resets stay unconditional; the `app.logging_setup` import + mute now
  only runs when `had_integration` (i.e. the one path that actually enabled Logfire, in
  `pytest_collection_finish`).

### Lever 2 measurements
- `pytest --co tests/test_hygiene_namespace.py`: **40.75 s -> 2.27/2.36/2.52/2.63/2.27 s**
  (5 runs, load 24.97). That is the collect-only wall, i.e. pure overhead.
- `import conftest` (with tests/ + src/ on sys.path): 24.26–45.94 s before -> **0.94–1.06 s**.
- One-test collection-only run through conftest: ~13 s -> ~2.5 s.
- All 8 consumer test files PASS:
  test_bot_health_probe 48 passed / test_classifier_fallback_budget 11 passed /
  test_recover_failed_credits 3 passed / test_recovery 9 passed /
  test_repair_roster_activation 12 passed / test_sync_group_admins 16 passed /
  test_upsert_adapter_faithful 2 passed / test_verdict_scenarios 3 passed 1 skipped.
- `tests/handlers/test_spam_handlers.py`: **49 passed, 1 deselected** — proves the PEP 562
  `MockTelegramBadRequest` lazy path works.

## Lever 1 — input coverage PROVEN by strace (do not re-derive)
Ran the real selftest under `strace -f -e trace=openat,execve`:
`/tmp/qs.strace` (287640 lines), stdout `/tmp/qs.out`, `RC=0`, **520 `  ok` lines**.

Repo files opened by the selftest (the COMPLETE set, deduped):
- `/root/ai-antispam/tools/questions`
- `/root/ai-antispam/tools/questions-render.mjs`
- `/root/ai-antispam/tools/questions-render.package.json`
- `/root/ai-antispam/registry/fleet.json`   <-- read by `_declared_slug()`; NOT in the brief
- `/root/ai-antispam` (dir), `/root/ai-antispam/src` (dir), `/root/ai-antispam/tools` (dir)

OC_HOME: **119 distinct paths, ALL under
`/root/.opencrabs/profiles/ops/questions/build/node_modules/`** — zero outside node_modules.
(Whole tree = 952 files / 15,221,398 bytes; content hash measured 0.13–0.14 s warm.)

`.git/config`, `.git/HEAD` etc are opened by the selftest's OWN `git init` inside
`tempfile.mkdtemp()` — self-created, deterministic, not an input.

`/root/sender/src`, `/root/miidas-template/...` are interpreter `.pth`/site startup, not the tool.

Env vars the tool reads but the selftest does NOT override (so ambient values are inputs):
`OC_DEV_STATE`, `OC_PROFILE`, `OPENCRABS_PROFILE`, `OC_QUESTIONS_FACTORY`,
`OC_QUESTIONS_A2A_TIMEOUT`. Also `OC_QUESTIONS_TRACKER` / `OC_QUESTIONS_A2A` are inherited
via `env = dict(os.environ)` before being overridden in some legs only.

### Cache design (superset hashing — can only over-invalidate, never stale-hit)
Hash = sha256 over:
- bytes of: tools/questions, tools/questions-render.mjs,
  tools/questions-render.package.json, tests/test_questions.py, registry/fleet.json
  (each with its repo-relative name)
- content hash of the node_modules tree at `profile_home()/questions/build/node_modules`
  (path-sorted walk, relpath + bytes; the resolved path string is included too)
- `sys.version` + `os.path.realpath(sys.executable)` (interpreter identity)
- `node --version` output (renderer identity)
- EVERY env var matching `^(OC_|OPENCRABS_)`, sorted — a deliberate superset
Any unreadable input -> NO CACHE, run the gate.

Receipt: `evidence/questions-gate-cache.json` (committable, diffable, not gitignored).
Written ONLY after a successful run, atomically. Corrupt/unparseable receipt -> miss.
Gate still REPORTED as PASS with a line naming the hash + the cached pass instant.

## Lever 3 — LANDED, default stays 1

`tools/audit.py`: the `for cmd in gates_to_run:` loop is now `_run_gate_set(gates_to_run,
repo_root)`, with `_gate_worker_count()` reading `AUDIT_GATE_WORKERS`. **Default 1** — the
historical sequential path, kept byte-for-byte. `executor.map` preserves registration order,
so the verdict table, score arithmetic and report read identically at any worker count.

Invalid values (non-integer, 0, negative) print a warning and fall back to 1 — never a crash,
never a silent clamp.

Ordering contract verified against synthetic gates that finish in REVERSE order (0.30/0.20/
0.10/0.00 s sleeps): results came back `['g1','g2','g3','g4']` in registration order, shape
keys identical, elapsed 0.31 s vs 0.60 s sequential — concurrency real, ordering preserved.

## Registry consequences (both resolved)

* `tests/test_questions.py` — the rewrite breaks the kit pin (`5f137eeb…` -> `bc724e42…`).
  Declared in `registry/kit-exemptions.json` with the measured need, the strace provenance of
  the input set, and why the pin is not re-hashed (version record, not a per-file table).
  `tests/test_kit_pin.py` green: `judged 96 carried path(s); 23 declared exempt`.
* `tools/audit.py` — already exempt (precedent for a `standalone`-class fork), so Lever 3
  needed no new declaration.

## Receipt format: `.jsonl`, not `.json`

`evidence/` declares exactly `markdown|jsonl` (`tools/hygiene.py` PLACEMENT_MAP), so a `.json`
receipt is a permanent placement MISMATCH in every hygiene report. One JSON object on one line
IS valid JSONL, so the receipt is `evidence/questions-gate-cache.jsonl` and fits the declared
class without widening the map for every other evidence file.

## The bug that mattered: a prefix-matched env superset is a PERMANENT MISS

The first cache hashed every env var matching `^(OC_|OPENCRABS_)`, on the reasoning that a
superset can only cause a miss. **That reasoning is wrong when the extra inputs are
UNSTABLE.** This box sets `OPENCRABS_PIPESTATUS_FILE=/tmp/opencrabs-pipestatus-<pid>-<n>` on
every shell call, so its value changes constantly.

Measured: run A recorded hash `f33d2eae` after a full green pass. The very next invocation
computed `93aed314` with **every input file byte-identical and every enumerated env var
equal** — the only difference was that one ambient variable. The gate re-ran the full ~1000 s
selftest instead of hitting, and would have done so forever.

A superset is safe in exactly one direction: extra STABLE inputs cost a miss only when they
change, which they never do. Extra UNSTABLE inputs cost a miss on every run — a cache that
always misses is a cache that does nothing, wearing the costume of a working one. **This is
the failure the brief warned about, and it was in the design, not the implementation.**

FIX: `ENV_INPUTS` is now the ENUMERATED list of variables `tools/questions` actually reads,
scraped from its own source (`grep -oE '\b(OC|OPENCRABS)_[A-Z0-9_]+'`), 14 names.
`OPENCRABS_SESSION_ID` is deliberately excluded and named in `ENV_EXCLUDED`: the instrument
reads it only as its telemetry `actor` and as `ask`'s return address, neither of which reaches
the synthetic selftest (which sets its own fixture session at `tools/questions:3930`).
Hashing it would tie a passing gate to the identity of whichever lane ran it.

GUARD: `probe_the_env_set_covers_every_variable_the_instrument_reads` scrapes the instrument
for those names and asserts the list is exactly `ENV_INPUTS | ENV_EXCLUDED` — so a NEW env
read REDS the gate instead of silently rotting the cache, and a stale entry is reported too.
Verified to bite: removing `OC_QUESTIONS_DB` from the list makes the probe fail by name.

STABILITY PROVEN: three separate process invocations computed `78f91ed20e80e950f1aa6ee5`
identically.

## A second bug the probes caught: an unguarded `relative_to` in a message

`main`'s miss message called `CACHE_RECEIPT.relative_to(REPO)` unguarded, so a receipt path
outside the repo raised `ValueError` and crashed the gate instead of reporting a miss. Found
by driving the miss branches with a relocated receipt, not by reading the code. Now `_shown()`
falls back to the absolute path. A message must never be the thing that fails.

## A third defect, found next door: the #240 cap inversion

`SELFTEST_TIMEOUT_SEC` was **2543** — derived from an older base of 635.7 s — while
`tools/audit.py` re-derived the gate's budget to **2537.0** from a newer 633.89 s sample.
The gate's own cap therefore sat **6 s ABOVE** the harness budget for it: the exact #240
inversion, where the audit kills the gate before the gate can report its own timeout and the
run reads UNKNOWN instead of a verdict. Invisible because `registry/gates.json` — the manifest
that leg reads — is ABSENT in this tree, so the leg SKIPS here.

Fixed to **2536** = 4.0007 x 633.89, same 4x margin on the same measurement, 1.0 s under the
budget. The arithmetic and both bases are in the constant's comment.

## Cache correctness, proven by probe rather than by assertion

| Branch | Input | Result |
|---|---|---|
| HIT | matching receipt | exit 0, **zero** selftest spawns (subprocess guarded) |
| MISS | stale hash | spawns, runs |
| MISS | corrupt JSON | spawns, runs |
| MISS | old schema | spawns, runs |
| MISS | `passed: false` | spawns, runs |
| MISS | absent receipt | spawns, runs |
| MISS | JSON list not object | spawns, runs |
| MISS | unreadable input | `CacheMiss`, spawns, reason printed |

Every doubtful input resolves toward a MISS. There is no path from an unreadable or changed
input to a hit.

## MEASURED: full audit, twice

| | Gates | Summed gate durations | `test_questions.py` |
|---|---|---|---|
| Baseline (`evidence/scores/2026-11-27-self-audit.md`) | 65 | **1592.94 s** | **1028.81 s** |
| Audit 1 (cold: cache MISS, selftest ran) | 64 | **837.57 s** | 7.53 s |
| Audit 2 (warm: cache HIT) | 65 | **555.83 s** | 7.81 s |

**The gate itself: 1028.81 s -> 7.53 s cold, 0.44-0.62 s warm.** Three consecutive warm runs
all reported HIT and exit 0; the receipt's `recorded_at` was unchanged after audit 2, which is
positive evidence the gate did not re-run rather than an absence of output.

**Overall: 1592.94 s -> 555.83 s, a 65.11 % reduction.** The audit-2 number is the honest
comparison against the 1592.94 s baseline because it carries the same 65 gates; audit 1 ran 64
because the questions gate's own receipt was being established.

Two caveats stated rather than buried. First, the summed gate durations are the audit's own
per-gate `(Xs)` figures added up, not a wall clock — the audit runs gates sequentially, so the
two are close but the sum is what the report prints. Second, audit 1's failure
(`test_single_writer.py`) and audit 2's failure (`test_hygiene_branch_occupancy.py`) are both
real findings, and both are now fixed: the first wanted the receipt declared as a state
surface, the second asserts the tree is on `main` and this work is on a named branch — it
reports **9 passed on `main`** and fails only because the branch is
`165-audit-acceleration`.

## A fourth defect, found by the audit itself

`tests/test_audit_interpreter_binding.py` was registered with NO `GATE_WALLS_SEC` entry, so it
fell to `DEFAULT_GATE_WALL_SEC = 30.0` and measured **45.10 s** on 2026-11-27 — the audit
killed a healthy gate and the run read UNKNOWN. Declared at **182.0** = 4.0 x 45.10 + 0.75
rounded up (4.0355x on the measurement), arithmetic in the comment.

This is the same class as the #240 inversion fixed above, and neither was visible to a reader:
the first needed a real audit run to surface, the second needed a reader who knew the two
constants had to be reconciled.

## Ledger rows: NOT written, and why

`tools/ledger.py append` refuses with `session b1903093-... matches no lane declared in 1
fragment(s)`. That is correct behaviour: the live path accepts only a DERIVED actor, and
`registry.all_bindings()` carries zero rows for this session — it is a headless session, not a
Telegram lane bound to a factory topic, so there is no lane for it to resolve to. The
`--actor` flag cannot override it (a declared actor that does not match the derived role is
refused by the same law), and the only escape is `bootstrap`, which requires an EMPTY ledger
and a `genesis` event. Forging a lane binding to satisfy the writer would be exactly the
kind of false record the law exists to prevent, so the rows are left unwritten and stated
here. **The board issue #165 remains OPEN** and should be closed by a session that resolves
to a lane.

## Still to do
1. Full audit run, twice (second must show the cache hit).
2. Ledger rows: intake/claim/close. Close needs `--rework none` + `board=closed head=<sha>`.
3. Do NOT push, do NOT commit to main. Leave in working tree / named branch.
