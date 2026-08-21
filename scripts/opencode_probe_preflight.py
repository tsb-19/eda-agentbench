#!/usr/bin/env python3
"""Zero-call preflight for the OpenCode external-scaffold probe.

Four of the nine structural checks in docs/opencode_scaffold_probe_scope.md do not need a model at
all -- they are properties of the config, the filesystem and the sandbox. Establishing those first
means the paid dry run only has to settle the ones that genuinely require a model to act, and it
means the safety-critical ones (oracle unreachability above all) are settled before any money is
spent rather than after.

  1  file exposure            workspace listing == <instance>/files/, no oracle path resolvable
  2  injection sources silent resolved config: instructions/plugin/mcp/skills empty, username neutral
  2b resolved permissions     read back the AGENT, because last-matching-rule-wins makes the written
                              config a poor witness for the effective one
  5  oracle isolation         a plain shell inside the sandbox cannot reach the task tree, and
                              EDA_TASK_PATH / EDA_TASK_ID are gone from its environment
  6a truncation seal          the directory OpenCode writes overflow into is read-only in-sandbox
  --  prompt transfer         every section marked TRANSFERRED is byte-identical to the frozen
                              driver's own text, proved against the pinned source, not eyeballed

Makes no model call. Reads no outcome. Writes nothing outside a temp workspace it then removes.

  python3 scripts/opencode_probe_preflight.py            # run, print a table
  python3 scripts/opencode_probe_preflight.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

CONFIG = REPO / "opencode_probe/config/opencode.json"
DRIVER = REPO / "scripts/llm_agent_driver.py"
DEV_TASK = REPO / "tasks/p15_sta_handoff/p15_dev_0000"
AGENT_ENTRY = REPO / "scripts/opencode_probe_agent.py"

SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|[A-Za-z0-9_\-]{32,})")


def _redact(text: str) -> str:
    return SECRET_RE.sub("<REDACTED>", text)


def _opencode() -> Path:
    p = shutil.which("opencode")
    if p:
        return Path(p)
    cand = Path.home() / ".opencode/bin/opencode"
    return cand


def _hardened_env(state: Path) -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("oc_agent", AGENT_ENTRY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    env = dict(os.environ)
    env.pop("EDA_TASK_PATH", None)
    env.pop("EDA_TASK_ID", None)
    env.update(mod.HARDENING_ENV)
    env["OPENCODE_CONFIG"] = str(CONFIG)
    env["XDG_DATA_HOME"] = str(state / "data")
    env["XDG_CACHE_HOME"] = str(state / "cache")
    env["XDG_CONFIG_HOME"] = str(state / "config")
    env["XDG_STATE_HOME"] = str(state / "state")
    return env


# ------------------------------------------------------------------------------------------------


def _frozen_prompt_literals() -> str:
    """Reconstruct the frozen driver's prompt text from its own AST.

    Comparing against the driver's *source* is wrong: the source contains the two-character escape
    `\\n` where the sent string contains a newline, so a whitespace-collapsed source comparison
    reports a spurious mismatch. Evaluating the AST compares against what the driver actually
    sends, and is also robust to the source being reformatted.

    Returns the concatenation of every string constant in `_CONF_FINISH` and in the `system = (...)`
    expression inside `main()`. f-string parts (the task text and the workspace file lists) are
    interpolated per episode and are checked separately by construction.
    """
    tree = ast.parse(DRIVER.read_text())
    chunks: list[str] = []

    def constants(node: ast.AST) -> None:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                chunks.append(sub.value)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "_CONF_FINISH" in names or "system" in names:
                constants(node.value)
    return "\n".join(chunks)


def check_prompt_transfer() -> dict:
    """Every TRANSFERRED section must appear byte-for-byte in what the frozen driver sends."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("oc_agent2", AGENT_ENTRY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    frozen = _frozen_prompt_literals()

    frozen_literals = {
        "role_preamble": mod.FROZEN_ROLE,
        "environment_tools_on_path": mod.FROZEN_TOOLS_ON_PATH,
        "no_oracle_clause": mod.FROZEN_NO_ORACLE,
        "confidence_block_source": mod.FROZEN_CONFIDENCE,
    }
    bad = []
    for name, text in frozen_literals.items():
        # exact match on the sent text, modulo the line breaks introduced by literal splitting
        if " ".join(text.split()) not in " ".join(frozen.split()):
            bad.append(name)

    os.environ.setdefault("EDA_TASK_PATH", str(DEV_TASK))
    msg, manifest = mod.compose(DEV_TASK, steps=60, elicit_confidence=True)
    transferred = [m["section"] for m in manifest if m["status"] == "TRANSFERRED"]
    restated = [m["section"] for m in manifest if m["status"] == "RESTATED"]

    # the frozen action grammar must NOT leak into an OpenCode episode
    leaked = [tok for tok in ("RUN:", "WRITE:", "FINISH") if tok in msg]

    return {
        "check": "prompt transfer fidelity",
        "pass": not bad and not leaked,
        "detail": {
            "frozen_literals_not_found_in_driver": bad,
            "transferred_sections": transferred,
            "restated_sections": restated,
            "frozen_action_grammar_leaked": leaked,
            "message_chars": len(msg),
        },
    }


def check_file_exposure(ws: Path) -> dict:
    """Check 1. The agent sees exactly <instance>/files/, flattened, and no oracle path."""
    from eda_agentbench.agentic.workspace import create_agent_workspace
    meta = json.loads((DEV_TASK / "metadata.json").read_text())
    real = create_agent_workspace(DEV_TASK, meta)
    try:
        got = sorted(p.name for p in real.rglob("*") if p.is_file())
        want = sorted(p.name for p in (DEV_TASK / "files").rglob("*") if p.is_file())
        forbidden = [d for d in ("hidden", "solution", "oracle")
                     if (real / d).exists()]
        return {
            "check": "file exposure (1)",
            "pass": got == want and not forbidden,
            "detail": {"files_in_workspace": len(got), "files_in_instance": len(want),
                       "only_in_workspace": sorted(set(got) - set(want)),
                       "only_in_instance": sorted(set(want) - set(got)),
                       "forbidden_dirs_present": forbidden},
        }
    finally:
        shutil.rmtree(real, ignore_errors=True)


def check_resolved_config(state: Path) -> dict:
    """Check 2. Read the RESOLVED config back; do not trust what we wrote."""
    oc = _opencode()
    proc = subprocess.run([str(oc), "debug", "config"], env=_hardened_env(state),
                          capture_output=True, text=True, cwd=str(state))
    if proc.returncode != 0:
        return {"check": "injection sources silent (2)", "pass": False,
                "detail": {"error": _redact(proc.stderr[-800:])}}
    try:
        cfg = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"check": "injection sources silent (2)", "pass": False,
                "detail": {"error": f"non-json debug config: {e}"}}

    want = {
        "instructions_empty": not cfg.get("instructions"),
        "plugin_empty": not cfg.get("plugin"),
        "mcp_empty": not cfg.get("mcp"),
        "skills_empty": not (cfg.get("skills") or {}).get("paths")
                        and not (cfg.get("skills") or {}).get("urls"),
        "username_neutral": cfg.get("username") not in (None, "") and "tongsb" not in str(cfg.get("username")),
        "share_disabled": cfg.get("share") == "disabled",
        "snapshot_off": cfg.get("snapshot") is False,
        "formatter_off": cfg.get("formatter") is False,
        "lsp_off": cfg.get("lsp") is False,
        "autoupdate_off": cfg.get("autoupdate") is False,
        "tool_output_4000": (cfg.get("tool_output") or {}).get("max_bytes") == 4000,
        "compaction_auto_off": (cfg.get("compaction") or {}).get("auto") is False,
        "compaction_prune_off": (cfg.get("compaction") or {}).get("prune") is False,
        "small_model_pinned": cfg.get("small_model") == cfg.get("model"),
        "subagent_depth_zero": cfg.get("subagent_depth") == 0,
        "no_literal_secret": not SECRET_RE.search(json.dumps(cfg.get("provider", {}))),
    }
    return {"check": "injection sources silent (2)", "pass": all(want.values()),
            "detail": {k: v for k, v in want.items()},
            "resolved_username": cfg.get("username")}


def check_resolved_agent(state: Path) -> dict:
    """Check 2b. Effective permissions, after last-matching-rule-wins has been applied."""
    oc = _opencode()
    proc = subprocess.run([str(oc), "debug", "agent", "probe"], env=_hardened_env(state),
                          capture_output=True, text=True, cwd=str(state))
    if proc.returncode != 0:
        return {"check": "resolved agent permissions (2b)", "pass": False,
                "detail": {"error": _redact(proc.stderr[-800:])}}
    try:
        ag = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"check": "resolved agent permissions (2b)", "pass": False,
                "detail": {"error": f"non-json: {e}", "head": _redact(proc.stdout[:300])}}

    rules = ag.get("permission") or []
    def effective(name: str, pattern: str = "*") -> str | None:
        act = None
        for r in rules if isinstance(rules, list) else []:
            if r.get("permission") in (name, "*"):
                act = r.get("action")
        return act

    must_deny = ("task", "webfetch", "websearch", "skill", "lsp", "glob", "grep",
                 "list", "todowrite", "question", "external_directory")
    verdicts = {n: effective(n) for n in must_deny}
    tool_output_allows = [r for r in (rules if isinstance(rules, list) else [])
                          if r.get("permission") == "external_directory"
                          and r.get("action") == "allow"]
    # `tools` is a name -> bool map: report what is ENABLED, which is the action surface the model
    # actually sees. Reading the keys instead of the values reports every tool as present.
    tmap = ag.get("tools") if isinstance(ag.get("tools"), dict) else {}
    enabled = sorted(k for k, v in tmap.items() if v)
    disabled = sorted(k for k, v in tmap.items() if not v)
    # external_directory is the one deny that provably cannot be enforced by config; it is carried
    # as a known finding rather than as a pass criterion, and is enforced at the filesystem instead.
    unenforceable = {"external_directory"}
    return {
        "check": "resolved agent permissions (2b)",
        "pass": all(v == "deny" for n, v in verdicts.items() if n not in unenforceable),
        "detail": {"effective": verdicts,
                   "tools_enabled": enabled,
                   "tools_disabled": disabled,
                   "external_directory_allow_rules_remaining": len(tool_output_allows),
                   "external_directory_note":
                       "config cannot revoke these; verified against string-deny, object-deny, "
                       "explicit-pattern-deny and global '*: deny'. Filesystem control required.",
                   "patterns": [r.get("pattern") for r in tool_output_allows]},
    }


def check_grader_invariance() -> dict:
    """The probe's central structural claim: the grader is not merely unchanged, it is not reached.

    An OpenCode arm is a different `agent_cmd` and nothing else, so the evaluator workspace, the
    hidden overlay, run_public.sh / run_hidden.sh, the typed provenance/authority oracle and the
    three anti-cheat checks are all downstream of the substitution. That is only worth anything if
    the bytes are actually still the frozen bytes, so verify the pins rather than assert the design.
    """
    from frozen_membership_verify import collect_pins, SCAN_ROOT
    pins = collect_pins(SCAN_ROOT)
    # The gate is "no NEW drift", not "no drift". Two generators were edited after the phase-5B/5C
    # freeze and that drift is carried forward deliberately (docs/frozen_membership_baseline.json);
    # a check tuned until it prints nothing would hide the next real mutation, which is the failure
    # mode the baseline exists to prevent.
    baseline = json.loads((REPO / "docs/frozen_membership_baseline.json").read_text())
    known = {e["path"]: e["actual"] for e in baseline.get("mismatch", []) if isinstance(e, dict)}
    watched = [
        "eda_agentbench/agentic/runner.py",
        "eda_agentbench/agentic/workspace.py",
        "eda_agentbench/evaluator/sta_handoff.py",
        "eda_agentbench/evaluator/spice_handoff.py",
        "generators/p15_sta_handoff_gen.py",
        "scripts/llm_agent_driver.py",
        "scripts/canonical_integrity.py",
        "scripts/episode_arbiter.py",
    ]
    bad, unpinned, carried = [], [], []
    for rel in watched:
        # collect_pins maps path -> {(sha256, manifest_that_recorded_it), ...}; a path may carry
        # more than one sha only if it is legitimately versioned, so accept any recorded sha.
        want = {sha for sha, _ in pins.get(rel, set())}
        if not want:
            unpinned.append(rel)
            continue
        p = REPO / rel
        got = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        if got in want:
            continue
        # known drift is only acceptable if it is the SAME drift the baseline recorded
        if known.get(rel) == got:
            carried.append(rel)
        else:
            bad.append(rel)
    return {
        "check": "grader / oracle / anti-cheat byte-invariance",
        "pass": not bad,
        "detail": {"verified_identical": len(watched) - len(unpinned) - len(carried) - len(bad),
                   "new_drift": bad,
                   "carried_baseline_drift": carried,
                   "not_sha256_pinned": unpinned,
                   "note": "runner.py is referenced but not sha256-pinned; the probe does not edit "
                           "it. Carried drift matches docs/frozen_membership_baseline.json exactly."},
    }


def check_sandbox(ws: Path, state: Path) -> dict:
    """Checks 5 and 6a, with a plain shell instead of a model.

    A model is not needed to establish that a path is unreachable: bash inside the sandbox is the
    same bash the agent would get, and it is strictly more capable than the agent because it is not
    mediated by any permission layer. So a bash that cannot reach the oracle bounds `read`, `write`
    and `edit` too, which is the only reason one shell probe can stand for four tools.

    This is an escape battery, not a listing. Each stanza is a named bypass the plan requires to be
    closed -- absolute path, parent traversal, environment disclosure, symlink, mount-table
    disclosure, and filesystem-wide search -- and the check fails if any of them succeeds.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("oc_agent3", AGENT_ENTRY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Planted before entry: a symlink is the one bypass that is created inside the writable
    # workspace and so survives the sandbox boundary as an object, even though its target does not.
    for name, target in (("escape_hidden", DEV_TASK / "hidden"),
                         ("escape_solution", DEV_TASK / "solution"),
                         ("escape_repo", REPO)):
        link = ws / name
        if not link.is_symlink():
            link.symlink_to(target)

    probe_sh = r"""
set -u
echo "ENV_TASK_PATH=${EDA_TASK_PATH:-ABSENT}"
echo "ENV_TASK_ID=${EDA_TASK_ID:-ABSENT}"
# any variable whose VALUE spells out the repository or the instance is an equivalent disclosure
while IFS= read -r line; do
  k="${line%%=*}"; v="${line#*=}"
  [ "$k" = "PATH" ] && continue
  case "$v" in
    *"$REPO_GUESS"*|*"$DEV_GUESS"*) echo "ENV_VALUE_LEAK=$k" ;;
  esac
done < <(env)
for p in "$REPO_GUESS" "$REPO_GUESS/tasks" "$DEV_GUESS" "$DEV_GUESS/hidden" "$DEV_GUESS/solution"; do
  if [ -e "$p" ]; then echo "REACHABLE=$p"; else echo "absent=$p"; fi
done
# symlink escape: the link exists, the target must not resolve
for l in escape_hidden escape_solution escape_repo; do
  if [ -e "$WS/$l/" ]; then echo "SYMLINK_ESCAPE=$l"; else echo "symlink_dangles=$l"; fi
done
# parent traversal out of the workspace
if [ -e "$WS/../../../data1" ]; then echo "TRAVERSAL_ESCAPE=data1"; else echo "traversal_blocked"; fi
# mount table must not disclose the task tree either
if grep -qE 'eda-agentbench|p15_' /proc/self/mountinfo; then echo "MOUNTINFO_LEAK"; else echo "mountinfo_clean"; fi
# filesystem-wide search for the oracle, by content not by guessed path
if find / -xdev -name 'handoff_truth.json' -o -xdev -name 'run_hidden.sh' 2>/dev/null | grep -q .; then
  echo "ORACLE_FOUND_BY_SEARCH"; else echo "oracle_not_findable"; fi
if [ -d "$WS" ]; then echo "WORKSPACE_OK=$WS"; else echo "WORKSPACE_MISSING"; fi
if touch "$WS/.probe_write_test" 2>/dev/null; then echo "WORKSPACE_WRITABLE"; rm -f "$WS/.probe_write_test"; else echo "WORKSPACE_READONLY"; fi
for d in "$XDG_DATA_HOME/opencode/tool-output" /tmp/opencode; do
  if touch "$d/.seal_test" 2>/dev/null; then echo "SEAL_BROKEN=$d"; rm -f "$d/.seal_test"; else echo "sealed=$d"; fi
done
# the probe calls a remote model API, so egress and name resolution must both work; without this
# every request fails as an infrastructure fault and is misread as model behaviour
if timeout 15 getent ahostsv4 tokenrhythm.studio >/dev/null 2>&1; then echo "DNS_OK"; else echo "DNS_FAIL"; fi
"""
    inner = ["/bin/bash", "-c", probe_sh]
    argv = mod.bwrap_argv(ws, state, _opencode(), inner,
                          ro_binds=os.environ.get("EDA_PROBE_BIND_RO", "").split(":"),
                          seal_tool_output=True,
                          config=CONFIG, resolv=mod.write_resolv(state))
    env = mod.scrubbed_env(CONFIG, state)
    env["REPO_GUESS"] = str(REPO)
    env["DEV_GUESS"] = str(DEV_TASK)
    env["WS"] = str(ws)
    # deliberately try to smuggle the pointers back in; the scrub must have removed them already
    proc = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=300)
    out = proc.stdout

    def tagged(prefix: str) -> list[str]:
        return [l.split("=", 1)[1] for l in out.splitlines() if l.startswith(prefix)]

    reachable = tagged("REACHABLE=")
    seal_broken = tagged("SEAL_BROKEN=")
    # REPO_GUESS / DEV_GUESS / WS are injected by this harness itself to make the probe adversarial;
    # they are not part of the environment a real episode gets.
    env_leaks = [k for k in tagged("ENV_VALUE_LEAK=")
                 if k not in ("REPO_GUESS", "DEV_GUESS", "WS", "_")]
    symlink_escapes = tagged("SYMLINK_ESCAPE=")
    scrubbed = ("ENV_TASK_PATH=ABSENT" in out and "ENV_TASK_ID=ABSENT" in out)
    hard_failures = {
        "env_pointers_scrubbed": scrubbed,
        "no_env_value_leak": not env_leaks,
        "no_reachable_task_path": not reachable,
        "no_symlink_escape": not symlink_escapes,
        "no_traversal_escape": "TRAVERSAL_ESCAPE=data1" not in out,
        "mountinfo_clean": "mountinfo_clean" in out,
        "oracle_not_findable": "oracle_not_findable" in out,
        "truncation_dir_sealed": not seal_broken,
        "workspace_writable": "WORKSPACE_WRITABLE" in out,
        "dns_resolves": "DNS_OK" in out,
    }
    return {
        "check": "oracle isolation + truncation seal (5, 6a)",
        "pass": all(hard_failures.values()),
        "detail": {**hard_failures,
                   "env_value_leaks": env_leaks,
                   "reachable_task_paths": reachable,
                   "symlink_escapes": symlink_escapes,
                   "seal_broken_dirs": seal_broken,
                   "bwrap_rc": proc.returncode,
                   "stderr_tail": _redact(proc.stderr[-400:])},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not CONFIG.is_file():
        print(f"missing pinned config: {CONFIG}", file=sys.stderr)
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="oc_preflight_"))
    ws = tmp / "ws"
    ws.mkdir()
    state = tmp / "state"
    for sub in ("data/opencode/tool-output", "cache", "config", "state"):
        (state / sub).mkdir(parents=True, exist_ok=True)

    results = []
    try:
        results.append(check_prompt_transfer())
        results.append(check_file_exposure(ws))
        results.append(check_resolved_config(state))
        results.append(check_resolved_agent(state))
        results.append(check_grader_invariance())
        results.append(check_sandbox(ws, state))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ok = all(r["pass"] for r in results)
    if a.json:
        print(json.dumps({"pass": ok, "model_calls": 0, "checks": results}, indent=2))
    else:
        print(f"OpenCode probe preflight — zero model calls\n{'=' * 62}")
        for r in results:
            print(f"[{'PASS' if r['pass'] else 'FAIL'}] {r['check']}")
            for k, v in r["detail"].items():
                print(f"        {k}: {v}")
        print("=" * 62)
        print("PREFLIGHT PASSED" if ok else "PREFLIGHT FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
