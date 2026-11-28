# Operational Process Self-Audit — 2026-11-28

> **Verdict:** `PASSED` · Process 3 (Internal Self-Audit)

> **Interpreter:** sys.version `3.14.6` · sys.executable `/usr/bin/python3.14` · realpath `/usr/bin/python3.14` · GATE_PYTHON `/usr/bin/python3.14`

> **Ledger read at:** `2026-11-28T05:52:33Z` (583 events) — this artifact describes the ledger AS OF THAT INSTANT, before this run's own row was appended. It is a START-OF-RUN SNAPSHOT, not the ledger's state when you read it: the run row this audit writes lands after the read, and concurrent lanes append throughout the gate window (#142, ruling n=919).

---

## 1. Process Health & Delivery Telemetry

| Metric | Value | Reference / Derivation |
|---|---|---|
| **Total Ledger Events** | `583` | Continuous ledger sequence |
| **Closed Tasks** | `93` | Distinct closed subjects; `99` close rows (6 re-close of a re-opened subject) |
| **First-Pass Yield** | `68.3%` | 41 accepted runs ÷ 60 runs stating an outcome (coverage: 60 of 208 run rows) |
| **Rework Entries** | `11` | Defect count recorded in rework.md |
| **Rework Declarations** | `48/99` (48.5%) | Close rows declaring a `rework=#N` or `rework=none` disposition — canonical trailer read by position: rework=#N 2; rework=none 46; undeclared 51 (printed, never gated — n=386 clause 5) |
| **Rework Share** | `10.6%` | 11 rework entries ÷ (93 closed subjects + 11 rework entries) |
| **Rework per Close** | `11.8%` | 11 rework entries ÷ 93 closed subjects |
| **Change Fail Rate** | `7.5%` | 7 closes that produced a rework entry ÷ 93 closed work units — **linkage coverage `11/11`** entries carry a determinate Subject (100.0%); read the rate only against this coverage |
| **Avg Task Lead Time** | `301220.2s` | Mean intake→close duration over 96 sampled subjects |
| **Total Inference Cost** | `$10012.7898` | Tracked cost across ledger task telemetry — summed from each row's canonical TRAILER only, by position and across every event (issue #90) |
| **Telemetry Outside the Trailer** | `11` row(s) | excluded from the totals above BY DESIGN: these rows carry a telemetry-shaped token outside the canonical trailer — n=141 (claim), n=239 (run), n=365 (run), n=415 (run), n=418 (run), n=419 (run), n=421 (run), n=424 (run), n=425 (run), n=451 (run), n=460 (run). Read each as prose, not as spend |
| **Avg Cost / Closed Task** | `$107.6644` | $10012.7898 total cost ÷ 93 distinct closed subjects |
| **Cost / Successful Task** | `n/a` | $10012.7898 total cost ÷ 0 accepted closed subjects (coverage: 0 of 99 close rows state an outcome) |
| **Total Tokens (In/Out)** | `1012932243 / 29613539425` | Cumulative prompt and completion tokens |
| **Cadence Status** | `HELD` | Last run: 23.5h ago · record read: evidence/ledger.jsonl run/score rows whose subject matches is_self_audit_subject (internal-self-audit, or daily self-audit YYYY-MM-DD) · matched 71 · rejected 1 (self-audit-class@2026-11-20) · latest artifact: 2026-11-27 |

---

## 2. Mechanical Gate Verification

| Gate / Command | Outcome | Duration | Notes |
|---|---|---|---|
| `/usr/bin/python3.14 tools/ledger.py verify` | `PASS` | `0.72s` | renumber-paired claim: n=148 #74 — closed by a row filed under #107, the number this item carries since the declared board renumber; the pai |
| `/usr/bin/python3.14 tests/test_ontology.py` | `PASS` | `1.42s` | vocabulary clean: 13 canonical term(s), 2 banned term(s), 125 file(s) scanned |
| `/usr/bin/python3.14 tests/test_rework.py` | `PASS` | `0.09s` | rework gate passed |
| `/usr/bin/python3.14 tests/test_rework_relative_revision.py` | `PASS` | `0.12s` | rework relative-revision gate passed |
| `/usr/bin/python3.14 tests/test_rework_declared_landed.py` | `PASS` | `0.25s` | rework declared-to-landed gate passed — 2 declaration(s) in scope, all resolved to a landed entry |
| `/usr/bin/python3.14 tests/test_single_writer.py` | `PASS` | `0.1s` | single-writer state clean: 8 declared surface(s) audited, locking verified |
| `/usr/bin/python3.14 tests/test_ledger_schema.py` | `PASS` | `0.4s` | ledger schema clean, 4 excused: 583 row(s) audited, all domain invariants & schemas verified |
| `/usr/bin/python3.14 tools/hygiene.py --clean --namespace ai-antispam` | `PASS` | `12.21s` | hygiene cleanup complete: 0 scratch item(s) reaped |
| `/usr/bin/python3.14 tools/hygiene.py --audit --namespace ai-antispam` | `PASS` | `0.69s` | hygiene audit clean: 0 stale scratch items in /tmp/ai-antispam-*, 0 stranded dirty paths (grace 60m), 0 advisory item(s), working tree clean |
| `/usr/bin/python3.14 tools/roadmap.py --audit` | `PASS` | `0.21s` | Product & cadence roadmap clean: 3 canonical products healthy and cadenced |
| `/usr/bin/python3.14 tests/test_audit_yield.py` | `PASS` | `6.54s` | yield-artifact guard clean: one rounding site, row == scorecard at 14/17 |
| `/usr/bin/python3.14 tests/test_audit_pytest_batch.py` | `PASS` | `3.85s` | pytest-batch driver guard clean: 7 check(s) -- per-file verdicts survive a failure, the knob is off by default, a missing record is UNKNOWN |
| `/usr/bin/python3.14 tests/test_audit_gate_note.py` | `PASS` | `0.53s` | gate-note guard clean: a FAIL note carries its population, PASS keeps its summary |
| `/usr/bin/python3.14 tests/test_close_board_recorded.py` | `PASS` | `0.3s` | close-board gate: excused — 9 row(s) (2 admitted, 7 pre-invariant); this is a visible debt, not a clean run |
| `/usr/bin/python3.14 tests/test_kit_pin.py` | `PASS` | `3.7s` | kit pin passed |
| `/usr/bin/python3.14 -m pytest tests/test_cron_thinness.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.68s` | 16 passed in 0.24s |
| `/usr/bin/python3.14 tests/test_patrol_host_state.py` | `PASS` | `5.67s` | patrol-runner gate passed: 109 check(s) |
| `/usr/bin/python3.14 tests/test_ledger.py` | `PASS` | `69.38s` | ledger gate passed |
| `/usr/bin/python3.14 tests/test_audit_stamp_duration.py` | `PASS` | `9.78s` | audit-stamp duration guard clean: the stamp site carries no literal, and the row tracks the gate work it describes |
| `/usr/bin/python3.14 tests/test_audit_cadence_record.py` | `PASS` | `0.6s` | and the printed record describes the subject PREDICATE (#159) |
| `/usr/bin/python3.14 tests/test_audit_cadence_subject.py` | `PASS` | `0.22s` | variant spelling (#159) recognised, `self-audit-class` rejected, hole still bites |
| `/usr/bin/python3.14 tests/test_audit_cadence_artifact_crosscheck.py` | `PASS` | `0.22s` | PASS: every artifact date carries a self-audit run row, or a dated exemption |
| `/usr/bin/python3.14 tests/test_ledger_commit_cites_no_rows.py` | `PASS` | `23.11s` | ledger clause: excused — 3 exempted violation(s) in cd2a3f874a39aacd0073b88372c15e23a4cbc3cd..HEAD; this is a visible debt, not a clean run |
| `/usr/bin/python3.14 tests/test_audit_cadence_own_run.py` | `PASS` | `0.18s` | PASS: own-run excluded, prior hole still named, parameter present and passed |
| `/usr/bin/python3.14 -m pytest tests/test_audit_interpreter_binding.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `3.91s` | 6 passed in 2.51s |
| `/usr/bin/python3.14 -m pytest tests/test_audit_requires_python_preflight.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.4s` | 6 passed in 0.38s |
| `/usr/bin/python3.14 -m pytest tests/test_audit_env_classification.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `4.27s` | 8 passed in 3.19s |
| `/usr/bin/python3.14 tests/test_audit_tree_condition.py` | `PASS` | `1.71s` | audit tree condition: passed |
| `/usr/bin/python3.14 tests/test_board_intake_recorded.py` | `PASS` | `0.39s` | board-intake gate passed: 15 check(s) |
| `/usr/bin/python3.14 tests/test_brain_metrics.py` | `PASS` | `0.78s` | brain-metrics gate passed (6 probe(s), 0 failure(s)) |
| `/usr/bin/python3.14 tests/test_close_row_revision.py` | `PASS` | `1.2s` | close-row revision gate: clean — 82 post-boundary close row(s) declared a revision IN THE CANONICAL RUN and every one RESOLVES; 1 retired by |
| `/usr/bin/python3.14 tests/test_commit_close_keyword.py` | `PASS` | `0.49s` | close-keyword gate: clean — 9 closing spellings refused, 9 lawful subjects accepted, body surface covered, bite proof intact |
| `/usr/bin/python3.14 tests/test_commit_pair_hook.py` | `PASS` | `0.63s` | commit pair hook ok: tools/hooks/pre-commit shipped, executable, wired via core.hooksPath |
| `/usr/bin/python3.14 tests/test_commit_session_trailer.py` | `PASS` | `1.08s` | commit session trailer passed |
| `/usr/bin/python3.14 tests/test_criteria_count.py` | `PASS` | `1.3s` | criteria count: clean — 0 claim(s) over 46 file(s) all read 19 criteria / 6 families (source: the shipped pin v0.5 — no local rubric in this |
| `/usr/bin/python3.14 tests/test_docs_sync.py` | `PASS` | `0.12s` | no TEMPLATE/docs tree — nothing to pair |
| `/usr/bin/python3.14 tests/test_duplicate_prose.py` | `PASS` | `0.1s` | duplicate-prose gate ok: 0 law surface(s), 0 prose block(s), no duplicates |
| `/usr/bin/python3.14 tests/test_gate_fixtures_closure.py` | `PASS` | `7.44s` | gate-fixture closure gate passed |
| `/usr/bin/python3.14 tests/test_gate_invocation_mode.py` | `PASS` | `0.33s` | SKIP no registry/gates.json in this tree — the invocation-mode declaration has not been adopted here, so there is nothing to assert against. |
| `/usr/bin/python3.14 tests/test_gate_registration.py` | `PASS` | `10.32s` | gate registry passed |
| `/usr/bin/python3.14 tests/test_ledger_identity.py` | `PASS` | `0.62s` | ledger identity: SKIPPED — this tree carries a lane resolver and a manifest, but its Worker lane does not resolve to a live session, so no s |
| `/usr/bin/python3.14 tests/test_ledger_index.py` | `PASS` | `3.21s` | ledger index gate clean |
| `/usr/bin/python3.14 tests/test_ledger_no_shrink.py` | `PASS` | `8.67s` | ledger no-shrink: clean — no commit removes a row identity |
| `/usr/bin/python3.14 tests/test_publish.py` | `PASS` | `3.85s` | PASS an in-sync round renders as in-sync |
| `/usr/bin/python3.14 tests/test_questions.py` | `PASS` | `5.25s` | the questions selftest passed: 520 check(s) examined (cached) |
| `/usr/bin/python3.14 tests/test_registry.py` | `PASS` | `0.27s` | SKIPPED — no docs/factory-registry.md, registry/index.json in this tree, so there is no registry to judge. Both are FACTORY DATA generated f |
| `/usr/bin/python3.14 tests/test_roadmap_transition.py` | `PASS` | `1.2s` | roadmap transition: clean — fresh/empty/malformed/incomplete all RED, filled declaration GREEN, skeleton-copy not GREEN; this tree: declared |
| `/usr/bin/python3.14 tests/test_skill_version_contract.py` | `PASS` | `0.16s` | skill-version contract: SKIP — no tracked law file matches skills/*/SKILL.md, TEMPLATE/SKILL.md.tmpl — nothing to judge |
| `/usr/bin/python3.14 tests/test_subject_anchor.py` | `PASS` | `0.16s` | subject-anchor gate passed (11 probe(s), 0 failure(s)); the live fleet reading above is REPORTED, never judged. |
| `/usr/bin/python3.14 tests/test_template_integrity.py` | `PASS` | `0.1s` | no TEMPLATE/ tree — the factory is the instantiation, nothing to classify |
| `/usr/bin/python3.14 -m pytest tests/test_binding_mechanism_exists.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `4.73s` | 3 passed in 3.48s |
| `/usr/bin/python3.14 -m pytest tests/test_close_telemetry_provenance.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.47s` | 18 passed in 0.22s |
| `/usr/bin/python3.14 -m pytest tests/test_hygiene_inflight.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `4.4s` | 7 passed in 3.39s |
| `/usr/bin/python3.14 -m pytest tests/test_hygiene_namespace.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `4.24s` | 14 passed in 3.29s |
| `/usr/bin/python3.14 -m pytest tests/test_hygiene_build_residue.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.52s` | 9 passed in 0.67s |
| `/usr/bin/python3.14 -m pytest tests/test_hygiene_declaration_sweep.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.91s` | 13 passed in 0.94s |
| `/usr/bin/python3.14 -m pytest tests/test_hygiene_stale_dirs.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.94s` | 14 passed in 0.80s |
| `/usr/bin/python3.14 -m pytest tests/test_hygiene_branch_occupancy.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.16s` | 9 passed in 0.14s |
| `/usr/bin/python3.14 -m pytest tests/test_insights_gate_recorded.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.5s` | 24 passed, 1 skipped in 0.18s |
| `/usr/bin/python3.14 -m pytest tests/test_ledger_close_preflight.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `3.61s` | 7 passed in 2.55s |
| `/usr/bin/python3.14 -m pytest tests/test_ledger_event_authorized.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.26s` | 4 passed in 0.22s |
| `/usr/bin/python3.14 -m pytest tests/test_registry_attest.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.19s` | 9 passed in 0.14s |
| `/usr/bin/python3.14 -m pytest tests/test_registry_render.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.21s` | 29 passed in 0.18s |
| `/usr/bin/python3.14 -m pytest tests/test_score_gate_recorded.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.09s` | 24 passed, 1 skipped in 0.15s |
| `/usr/bin/python3.14 -m pytest tests/test_self_audit_push_gate.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `1.51s` | 5 passed in 0.64s |
| `/usr/bin/python3.14 -m pytest tests/test_audit_rates.py -q -p no:logfire -p no:pytest_logfire` | `PASS` | `5.44s` | 19 passed in 4.61s |

---

## 3. Calibration Spot-Check (Sampled Task)

- **Sampled Subject:** `#165`
- **Intake Recorded:** `YES`
- **Claim Lock Recorded:** `YES`
- **Close Verified:** `YES`
- **Sequence Integrity:** `VERIFIED`
