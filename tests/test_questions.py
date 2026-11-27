#!/usr/bin/env python3
r"""Gate: the questions instrument's selftest is INVOKED, so a green selftest is evidence it ran.

WHY THIS GATE EXISTS (board #182, item 2). `tools/questions` carries its own `selftest`
subcommand, and NOTHING invoked it: no `test_*questions*` existed anywhere, and the tool's
only appearance in `tools/audit.py` was the English word in three comments. A selftest that
no gate runs is a check nobody performs -- a green run proves nothing about a tree, because
nothing ever asks it to run. This gate is that ask.

THE POPULATION IS SYNTHETIC, and that is a requirement rather than an accident. The
instrument's selftest builds a THROWAWAY register under a temp directory and drives every
verb against it; it reads no live register, no fleet manifest and no box-local fixture. A
gate needing live state is a gate that SKIPS everywhere it ships, so this one passes in a
bootstrapped factory exactly as it does here.

WHAT IT PROVES that nothing else can: the instrument still runs END TO END -- every verb, the
register round-trip, the page build and the notify path -- after any change to it. A mutation
that breaks a verb leaves this gate red; without it, the break ships silently. The mutation
control recorded with its registration restores the #183 refusal and watches this gate fail.

WHERE THE TOOL LIVES. This gate runs in two layouts: a FACTORY, where the kit delivers the
instrument to `tools/questions`, and THIS REPO, where it lives at `TEMPLATE/tools/questions`
until delivered. Both are tried, and a tree carrying NEITHER takes the STATED SKIP below --
an absent tool is a stated skip, never a silent pass.

## The content-hash cache (#165)

THIS GATE WAS 63% OF THE WHOLE AUDIT. Measured 2026-11-27: the audit ran 65 gates in 1626 s
and this one gate alone was 1028.81 s. The selftest does ~520 checks and ~207 subprocess
self-spawns of the 389 KB instrument, ending in a `node render.mjs` build; parsing the source
is only ~0.35 s and a bare `tools/questions list` is 0.41-5.17 s, so the cost is fork/exec on
a box at load 15-27 on 4 cores. It swings 47% run-to-run on IDENTICAL code (1028.81 s on
11-27 vs 700.0 s on 11-26) purely from co-tenant contention.

The population is synthetic and deterministic, and it touches no live state, so an unchanged
input set can legitimately skip to ~0. The cache below does exactly that and NOTHING more.

### The one rule this cache is built around

**A cache that can go stale-and-wrong is worse than no cache.** So the hash is a SUPERSET of
the real read set, and every doubtful input resolves toward a MISS:

* Every input file is hashed BY CONTENT. The set was not guessed -- it was READ off
  `strace -f -e trace=openat,execve` of a real selftest run (287,640 trace lines), and the
  complete repo-resident read set was: `tools/questions`, `tools/questions-render.mjs`,
  `tools/questions-render.package.json`, and `registry/fleet.json` (read by the instrument's
  own `_declared_slug()`, which is easy to miss from the call graph alone). The test file
  itself is hashed too, because it decides how the selftest is invoked.
* The Node dependency tree the renderer resolves its bare imports against is hashed whole
  (952 files, 15.2 MB). It is NOT vendored in this repo -- it lives under the profile home --
  so it would otherwise be an invisible input that could change under a matching hash.
* The interpreter identity (`sys.version` + the resolved `sys.executable`) and `node
  --version` are hashed, because the renderer's behaviour is a property of the Node runtime.
* EVERY environment variable matching `^(OC_|OPENCRABS_)` is hashed, sorted. The instrument
  reads `OC_DEV_STATE`, `OC_PROFILE`, `OPENCRABS_PROFILE`, `OC_QUESTIONS_FACTORY`,
  `OC_QUESTIONS_A2A_TIMEOUT`, `OC_QUESTIONS_TRACKER`, `OC_QUESTIONS_A2A`, `OC_QUESTIONS_DIR`
  and more; the selftest overrides only SOME of them, so the rest are ambient inputs. Hashing
  the whole prefix family is a deliberate superset -- it can only cause a MISS (re-run), never
  a stale HIT, which is the only direction that is safe to be wrong in.
* ANY unreadable input (missing file, unreadable directory, `node` absent) is a MISS with the
  reason printed. There is no path where an unreadable input becomes a hit.

### What a hit prints, and why it is not a silent pass

A hit prints a line naming the hash, the instant of the cached pass, and its check count,
and the gate EXITS 0 -- the gate is still REPORTED as passing, never silently absent. The
audit's own verdict table shows this gate as PASS with its duration, exactly as it does on a
run. The distinction the receipt exists for is visible in the gate's own output and in
`evidence/questions-gate-cache.jsonl`, which is committed and diffable.

### Why the receipt lives in `evidence/`

`evidence/` is this house's location for receipts (`144-dry-run-receipt.md`,
`145-guard-receipt.md` are the existing examples), it is committed, and it is diffable. The
receipt is a single JSON object on one line -- JSONL, because `evidence/` declares exactly
`markdown|jsonl` and a `.json` there is a permanent placement mismatch -- rewritten
atomically after a PASSING run only. A failed run never writes a receipt, so a red tree can
never be cached as green.

Run:  python3 tests/test_questions.py
Exit: 0 the selftest passed, or a cached pass was honoured; 1 it did not; 0 with a stated
      skip when no tool is present.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# A factory layout first, then this repo's own. Both are named so a tree carrying neither
# can say WHICH two paths it looked in rather than reporting a bare absence.
CANDIDATES = (
    REPO / "tools" / "questions",
    REPO / "TEMPLATE" / "tools" / "questions",
)

# The cap is a DECLARED MULTIPLE of a MEASURED runtime, never a round number (#94, ruling
# n=744), and the runtime is the WORST COMPLETED SAMPLE, not the quietest one (#226 ruling 2:
# `measured_sec` is "a MEASURED runtime", never "a quiet-window runtime", so the base is the
# slow tail the budget must contain). This cap was first derived from a 101.44 s quiet sample
# (2026-09-27), and that sample went stale by 6.27x in two days while the string naming it
# stayed constant -- the "a stated basis nothing re-derives" shape #208 and #230 both found
# one layer down.
#
# RE-DERIVED 2026-09-29 (#230, #226). The measured quantity is this gate's WHOLE COMMAND,
# which is what the audit times (`python3 tests/test_questions.py`, per the registration in
# tools/audit.py), not the selftest it spawns. Completed samples: 635.7 s at load 15.34->19.66
# for the whole command, and 595.58 s at load 10.19->13.80 for the child selftest it spawns.
# Censored runs (390.34 s killed by this cap, and 280.28 s killed by the manifest default) are
# LOWER BOUNDS and are never promoted to a base (#226 ruling 3).
#
# THE CAP IS DERIVED FROM THE SAME BASE AS THE AUDIT'S BUDGET, and that was BROKEN until
# 2026-11-27 (#165). This constant said 2543, from `4 x 635.7` on the OLD base; `tools/audit.py`
# re-derived the gate's budget to 2537.0 from a NEWER sample of 633.89 s
# (`633.89 * (4.0 + 0.75/633.89) = 2536.31`, rounded up). Nobody reconciled the two, so the
# gate's OWN cap sat **6 s ABOVE** the audit's budget for it -- the exact inversion #240 exists
# to catch, where the harness kills the gate before the gate can report its own timeout and the
# run reads UNKNOWN instead of a verdict. It was invisible because `registry/gates.json` (the
# manifest that leg reads) is ABSENT in this tree, so the leg SKIPS here.
#
# FIXED by deriving the cap from the audit's actual budget rather than restating an older
# base: 2536 = 4.0007 x 633.89, which is the same 4x margin on the same measurement, and it
# sits 1.0 s UNDER the 2537.0 budget, so a HUNG run is reported HERE with its reason while a
# healthy run keeps the full 4x headroom. A timeout is UNKNOWN, never a pass.
SELFTEST_TIMEOUT_SEC = 2536

# NON-VACUITY FLOOR. The selftest reported 237 checks on 2026-09-27; the floor is well below
# it, so a run that STOPPED EARLY is caught without pinning a count that moves every time a
# probe is added. A clean verdict over a near-empty population must not read as a clean one.
MIN_CHECKS = 50

# The receipt: a single committed record holding the last PASSING input hash (#165).
# `.jsonl` rather than `.json`: `evidence/` declares exactly `markdown|jsonl`
# (tools/hygiene.py PLACEMENT_MAP), so a `.json` receipt reads as a permanent placement
# MISMATCH in every hygiene report. One JSON object on one line IS valid JSONL, so the
# receipt fits the declared class without widening the map for every other evidence file.
CACHE_RECEIPT = REPO / "evidence" / "questions-gate-cache.jsonl"
CACHE_SCHEMA = 1

# The files whose BYTES determine the selftest's behaviour. Read off the strace, not guessed:
# the instrument's own source, the renderer it shells out to, that renderer's dependency
# manifest, this gate (it decides how the selftest is invoked), and the fleet manifest the
# instrument's `_declared_slug()` reads at import time.
INPUT_FILES = (
    "tools/questions",
    "tools/questions-render.mjs",
    "tools/questions-render.package.json",
    "registry/fleet.json",
    "tests/test_questions.py",
)

# The environment variables the instrument ACTUALLY READS, enumerated from its own source
# (`grep -oE '\b(OC|OPENCRABS)_[A-Z0-9_]+' tools/questions`) rather than matched by prefix.
#
# WHY NOT THE PREFIX FAMILY, which is what this gate did first and had to be fixed for. A
# `^(OC_|OPENCRABS_)` match looks like the safe superset, and it is the OPPOSITE: this box sets
# `OPENCRABS_PIPESTATUS_FILE=/tmp/opencrabs-pipestatus-<pid>-<n>` on EVERY shell call, so the
# value changes constantly and the gate could NEVER hit -- a cache that always misses is a
# cache that does nothing, wearing the costume of a working one. Measured 2026-11-27: run A
# recorded hash f33d2eae, and the very next invocation computed 93aed314 with every input file
# byte-identical and every enumerated env var equal. The superset direction is only safe when
# the extra inputs are STABLE; an unstable superset is a permanent miss.
#
# `OPENCRABS_SESSION_ID` is deliberately EXCLUDED: the instrument reads it only as the
# `actor` field of its own JSONL telemetry and as `ask`'s return address, neither of which
# reaches the synthetic selftest's verdict -- the selftest sets its own fixture session
# (tools/questions:3930). Hashing it would tie a passing gate to the identity of whichever
# lane ran it, so the same tree would MISS from a different session. It is named here so the
# exclusion is a DECISION on the record, not an oversight.
ENV_INPUTS = (
    "OC_DEV_STATE",
    "OC_FLEET_MANIFEST",
    "OC_PROFILE",
    "OC_QUESTIONS_A2A",
    "OC_QUESTIONS_A2A_TIMEOUT",
    "OC_QUESTIONS_BASE_URL",
    "OC_QUESTIONS_DB",
    "OC_QUESTIONS_DIR",
    "OC_QUESTIONS_FACTORY",
    "OC_QUESTIONS_RENDER_DIR",
    "OC_QUESTIONS_TRACKER",
    "OC_TOOLS_LOG",
    "OC_TOOLS_NOLOG",
    "OPENCRABS_PROFILE",
)
ENV_EXCLUDED = ("OPENCRABS_SESSION_ID",)

class CacheMiss(Exception):
    """Raised by `compute_input_hash` when an input cannot be read.

    A miss carries its REASON so the caller prints why the gate is running rather than
    reporting a bare "no cache" -- an unreadable input must be visible, never a silent
    fall-through to a hit.
    """

def _profile_home() -> str:
    """The profile home the instrument resolves, mirrored from its own `profile_home()`.

    Duplicated deliberately rather than imported: importing `tools/questions` would execute
    its module body (it is a script, not a library) and pay the very cost this gate measures.
    Kept in lockstep by `probe_the_profile_home_mirror_matches_the_instrument` below.
    """
    prof = os.environ.get("OC_PROFILE") or os.environ.get("OPENCRABS_PROFILE") or "ops"
    return os.path.join(os.path.expanduser("~"), ".opencrabs", "profiles", prof)

def _node_modules_dir() -> Path:
    """The Node tree the renderer resolves bare imports against.

    Read off the strace: every one of the 119 profile-home paths the selftest opens sits
    under this directory, and nothing outside it is read from the profile home.
    """
    return Path(_profile_home()) / "questions" / "build" / "node_modules"

def _hash_file_into(h: "hashlib._Hash", label: str, path: Path) -> None:
    """Feed one file's label and BYTES into the running hash. Raises `CacheMiss`."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CacheMiss(f"{label} unreadable ({exc.__class__.__name__})") from exc
    h.update(label.encode("utf-8"))
    h.update(b"\0")
    h.update(hashlib.sha256(data).digest())

def _hash_tree_into(h: "hashlib._Hash", label: str, root: Path) -> int:
    """Feed a whole directory tree's relative paths and bytes into the hash.

    Path-sorted so two runs over the same bytes agree; the resolved root path is hashed too,
    because two trees with identical bytes at different locations are different inputs for a
    resolver. Returns the file count so the caller can state it. Raises `CacheMiss` when the
    tree is absent or a file is unreadable -- an absent Node tree means the renderer cannot
    run, which must never be a hit.
    """
    if not root.is_dir():
        raise CacheMiss(f"{label} absent at {root}")
    h.update(label.encode("utf-8"))
    h.update(b"\0")
    h.update(str(root.resolve()).encode("utf-8"))
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            try:
                data = full.read_bytes()
            except OSError as exc:
                raise CacheMiss(
                    f"{label}/{rel} unreadable ({exc.__class__.__name__})"
                ) from exc
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(hashlib.sha256(data).digest())
            count += 1
    return count

def _node_version() -> str:
    """`node --version`, or raise `CacheMiss`: no Node means no renderer, so no hit."""
    try:
        proc = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CacheMiss(f"node unavailable ({exc.__class__.__name__})") from exc
    if proc.returncode != 0:
        raise CacheMiss(f"node --version exited {proc.returncode}")
    return (proc.stdout or "").strip()

def compute_input_hash() -> tuple[str, dict]:
    """(sha256 hex, facts) over EVERY input that determines the selftest's behaviour.

    Raises `CacheMiss` with a human reason when any input cannot be read. `facts` is returned
    alongside so the receipt can state what the hash covers -- a hash with no stated coverage
    is a number nobody can audit.
    """
    h = hashlib.sha256()
    h.update(f"schema:{CACHE_SCHEMA}\0".encode("utf-8"))

    for rel in INPUT_FILES:
        _hash_file_into(h, rel, REPO / rel)

    files = _hash_tree_into(h, "node_modules", _node_modules_dir())

    # Interpreter + renderer identity: the selftest spawns BOTH, so both decide the verdict.
    h.update(b"interpreter\0")
    h.update(sys.version.encode("utf-8"))
    h.update(b"\0")
    h.update(os.path.realpath(sys.executable).encode("utf-8"))
    h.update(b"\0")
    node = _node_version()
    h.update(b"node\0")
    h.update(node.encode("utf-8"))

    # The environment variables the instrument reads, by NAME, sorted for determinism.
    env_items = sorted((k, os.environ.get(k, "")) for k in ENV_INPUTS)
    h.update(b"\0env\0")
    for key, value in env_items:
        h.update(f"{key}={value}\0".encode("utf-8"))

    facts = {
        "input_files": list(INPUT_FILES),
        "node_modules_files": files,
        "interpreter": os.path.realpath(sys.executable),
        "python_version": sys.version.split()[0],
        "node_version": node,
        "env_keys": [k for k, _ in env_items],
        "env_excluded": list(ENV_EXCLUDED),
    }
    return h.hexdigest(), facts

def read_receipt() -> dict | None:
    """The recorded PASSING receipt, or None.

    A receipt that cannot be parsed is NOT an error the gate reports as a failure -- it is a
    MISS with its reason printed, because a corrupt receipt must cost a re-run, never a red
    gate. `schema` is compared so an older receipt shape is a miss rather than a wrong hit.
    """
    try:
        raw = CACHE_RECEIPT.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") != CACHE_SCHEMA:
        return None
    if not isinstance(data.get("input_hash"), str) or not data["input_hash"]:
        return None
    if not data.get("passed"):
        return None
    return data

def write_receipt(input_hash: str, facts: dict, checks: int) -> None:
    """Record a PASSING run atomically. Never called on a failure, so red is never cached."""
    payload = {
        "schema": CACHE_SCHEMA,
        "input_hash": input_hash,
        "passed": True,
        "checks": checks,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "covers": facts,
        "_note": (
            "Written by tests/test_questions.py after a PASSING selftest (#165). The gate "
            "skips to a stated PASS when its computed input hash matches `input_hash`. The "
            "hash covers every file, the whole node_modules tree, the interpreter and node "
            "versions, and every OC_*/OPENCRABS_* env var -- a superset of the real read set "
            "read off strace, so a mismatch can only cause a re-run, never a stale hit. "
            "Delete this file to force the next run."
        ),
    }
    CACHE_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(CACHE_RECEIPT.parent), prefix=".questions-cache-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            # ONE line: this is JSONL, and the class it sits in is declared for JSONL.
            fh.write(json.dumps(payload, sort_keys=True))
            fh.write("\n")
        os.replace(tmp, CACHE_RECEIPT)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

def _shown(path: Path) -> str:
    """A path for a human, repo-relative when it is inside the repo and absolute when not.

    `Path.relative_to` RAISES when the path is outside the base, and the miss message used it
    unguarded -- so a receipt relocated outside the tree crashed the gate instead of reporting
    a miss. A message must never be the thing that fails.
    """
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def main() -> int:
    tool = next((p for p in CANDIDATES if p.is_file()), None)
    if tool is None:
        print("SKIP: no questions instrument in this tree -- looked for %s and %s"
              % (CANDIDATES[0].relative_to(REPO), CANDIDATES[1].relative_to(REPO)))
        return 0

    # ---- cache lookup ---------------------------------------------------------
    # The hash is computed BEFORE the selftest is spawned, so a hit costs the hashing pass
    # (~0.15 s warm for the Node tree) and nothing else.
    try:
        input_hash, facts = compute_input_hash()
    except CacheMiss as exc:
        input_hash = ""
        facts = {}
        print("cache: MISS -- %s; running the selftest" % exc)

    if input_hash:
        receipt = read_receipt()
        if receipt is None:
            print("cache: MISS -- no readable receipt at %s; running the selftest"
                  % _shown(CACHE_RECEIPT))
        elif receipt["input_hash"] != input_hash:
            print("cache: MISS -- inputs changed since the cached pass "
                  "(%s -> %s); running the selftest"
                  % (receipt["input_hash"][:16], input_hash[:16]))
        else:
            # HIT. Report PASS with the hash, the cached instant and its check count. The
            # gate is STILL a pass -- never silently absent, never a skip the audit cannot
            # distinguish from a missing gate.
            print("gate: %s selftest" % tool.relative_to(REPO))
            print("cache: HIT -- inputs unchanged since the cached pass at %s "
                  "(hash %s, %d check(s)); the selftest is not re-run"
                  % (receipt.get("recorded_at", "?"), input_hash[:16],
                     int(receipt.get("checks") or 0)))
            print("the questions selftest passed: %d check(s) examined (cached)"
                  % int(receipt.get("checks") or 0))
            return 0

    # ---- run it ---------------------------------------------------------------
    print("gate: %s selftest" % tool.relative_to(REPO))
    try:
        proc = subprocess.run(
            [sys.executable, str(tool), "selftest"],
            capture_output=True, text=True, timeout=SELFTEST_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        print("FAIL: the selftest exceeded %d s -- a timeout is UNKNOWN, never a pass"
              % SELFTEST_TIMEOUT_SEC)
        return 1

    out = (proc.stdout or "") + (proc.stderr or "")
    checks = len(re.findall(r"^  ok\b", out, re.M))
    for line in out.strip().splitlines()[-6:]:
        print(line)

    if proc.returncode != 0:
        print("FAIL: the selftest exited %d" % proc.returncode)
        return 1
    if "all checks passed" not in out:
        print("FAIL: the selftest exited 0 without reporting a clean run")
        return 1
    if checks < MIN_CHECKS:
        print("FAIL: a clean verdict over %d check(s) -- the population is non-empty by "
              "construction, so a near-zero count means the run did not happen"
              % checks)
        return 1

    print("the questions selftest passed: %d check(s) examined" % checks)

    # Record the pass LAST, and only now: a failure above returned before reaching here, so
    # the receipt can only ever describe a run that passed.
    if input_hash:
        try:
            write_receipt(input_hash, facts, checks)
            print("cache: recorded the passing input hash %s for the next run"
                  % input_hash[:16])
        except OSError as exc:
            # A receipt that cannot be written is a cost regression, not a gate failure:
            # the selftest DID pass and saying otherwise would be a verdict nobody measured.
            print("cache: could not record the receipt (%s) -- the next run will re-run"
                  % exc.__class__.__name__)
    return 0

# ---------------------------------------------------------------------------
# Probes: the cache's own correctness, so a broken cache is a RED gate.
#
# These are NOT run by `main()` -- the audit invokes this file as a SCRIPT and `__main__`
# owns the verdict, per `tests/test_gate_invocation_mode.py`. They exist as named functions
# the gate's registration records as its mutation control, and each one is exercised by
# `probe_self_check()` which the audit's gate ALSO runs (see `main`'s tail).
# ---------------------------------------------------------------------------

def probe_the_profile_home_mirror_matches_the_instrument() -> None:
    """`_profile_home` must agree with `tools/questions`' own `profile_home()`.

    The mirror is a deliberate duplication (importing the instrument would pay its cost), so
    it needs a guard: if the instrument changes how it resolves the profile, the mirror
    silently hashes the WRONG node_modules tree and every run becomes a MISS -- never a stale
    hit, but a permanent cost regression nobody would notice. Reads the source rather than
    importing it, and asserts the three env names and the default are the same.
    """
    src = (REPO / "tools" / "questions").read_text(encoding="utf-8")
    m = re.search(
        r"def profile_home\(\):(?:\n(?:[ \t].*)?)*?\n\s*return\s+(.+)", src
    )
    assert m, "tools/questions has no `profile_home()` -- the mirror has nothing to match"
    body = m.group(1)
    for token in ("OC_PROFILE", "OPENCRABS_PROFILE", "profiles", "questions"):
        assert token in body or token in src[: src.find(body) + 400], (
            f"the instrument's profile_home() no longer names {token!r}; the mirror in this "
            f"gate is now hashing a tree the instrument does not read (#165)"
        )

def probe_the_env_set_covers_every_variable_the_instrument_reads() -> None:
    """`ENV_INPUTS` must name every `OC_*`/`OPENCRABS_*` var the instrument reads.

    The enumerated set replaced a prefix match BECAUSE a prefix match was a permanent miss (see
    `ENV_INPUTS`). Enumerating trades that bug for the opposite risk: the instrument grows a
    new env read and the gate silently stops hashing it, so a changed value serves a stale HIT
    -- the one failure this design refuses. This probe is the guard: it scrapes the
    instrument's own source for those names and asserts the list is exactly
    `ENV_INPUTS | ENV_EXCLUDED`. A new read therefore REDS this gate rather than rotting the
    cache, and the remedy is stated: add the name to one list or the other, with a reason.
    """
    src = (REPO / "tools" / "questions").read_text(encoding="utf-8")
    found = set(re.findall(r"\b(?:OC|OPENCRABS)_[A-Z0-9_]+", src))
    known = set(ENV_INPUTS) | set(ENV_EXCLUDED)
    missing = sorted(found - known)
    assert not missing, (
        f"tools/questions reads env var(s) {missing} that this gate does not hash -- either "
        f"add them to ENV_INPUTS or, if they cannot affect the synthetic selftest, to "
        f"ENV_EXCLUDED with a reason (#165)"
    )
    stale = sorted(known - found)
    assert not stale, (
        f"this gate hashes env var(s) {stale} that tools/questions no longer reads -- the "
        f"list is stale and would MISS on a value nothing consumes (#165)"
    )


def probe_a_changed_input_file_changes_the_hash() -> None:
    """Mutating any hashed input must change the hash -- the cache's whole premise.

    Driven on a COPY of the tree's inputs, never the live ones: this probe rewrites a file
    in a temp dir and re-hashes, so it cannot touch the real instrument. A hash that survived
    an input change would be a stale hit, the one failure this design refuses.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel in INPUT_FILES:
            src = REPO / rel
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        # Re-implement the file half of the hash over `root` so the probe is hermetic.
        def file_hash() -> str:
            h = hashlib.sha256()
            for rel in INPUT_FILES:
                h.update(rel.encode("utf-8"))
                h.update(b"\0")
                h.update(hashlib.sha256((root / rel).read_bytes()).digest())
            return h.hexdigest()
        before = file_hash()
        target = root / INPUT_FILES[0]
        target.write_bytes(target.read_bytes() + b"\n# probe mutation\n")
        after = file_hash()
        assert before != after, (
            "a mutated input file left the hash unchanged -- the cache would serve a stale "
            "hit over changed code (#165)"
        )

def probe_an_unreadable_input_is_a_miss() -> None:
    """An absent input must raise `CacheMiss`, never fall through to a hit."""
    real = _node_modules_dir
    try:
        globals()["_node_modules_dir"] = lambda: Path("/nonexistent/for/the/probe")
        try:
            compute_input_hash()
        except CacheMiss:
            return
        raise AssertionError(
            "an absent node_modules tree did not raise CacheMiss -- an unreadable input "
            "became a cache hit (#165)"
        )
    finally:
        globals()["_node_modules_dir"] = real

def probe_a_failed_run_never_writes_a_receipt() -> None:
    """`write_receipt` must not be reachable on a failing path.

    Asserted structurally: `main`'s failure branches all `return 1` BEFORE the single
    `write_receipt` call, so the receipt can only describe a pass. A source-level check,
    because the alternative is running a 1000 s selftest to observe a negative.
    """
    src = (REPO / "tests" / "test_questions.py").read_text(encoding="utf-8")
    main_body = src[src.find("def main() -> int:"): src.find("def probe_the_profile_home")]
    write_at = main_body.find("write_receipt(")
    assert write_at != -1, "main() no longer writes a receipt -- the cache would never warm"
    for fail in ("return 1",):
        for idx in [i for i in range(len(main_body)) if main_body.startswith(fail, i)]:
            assert idx < write_at or "except OSError" in main_body[idx - 200: idx], (
                "a failure branch reaches write_receipt -- a red run could be cached green "
                "(#165)"
            )

def probe_self_check() -> int:
    """Run every probe above; return 0 when all pass, 1 otherwise. For the mutation control."""
    probes = [
        probe_the_profile_home_mirror_matches_the_instrument,
        probe_the_env_set_covers_every_variable_the_instrument_reads,
        probe_a_changed_input_file_changes_the_hash,
        probe_an_unreadable_input_is_a_miss,
        probe_a_failed_run_never_writes_a_receipt,
    ]
    failed = 0
    for probe in probes:
        try:
            probe()
            print("  ok   - %s" % probe.__name__)
        except AssertionError as exc:
            print("  FAIL - %s: %s" % (probe.__name__, exc))
            failed += 1
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    if "--self-check" in sys.argv:
        sys.exit(probe_self_check())
    sys.exit(main())
