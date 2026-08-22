#!/usr/bin/env python3
"""OpenCode `agent_cmd` entry point for the external-scaffold probe.

`eda_agentbench.agentic.runner.run_single_agentic` takes `agent_cmd` as a shell string and does
everything after it itself -- evaluator workspace, hidden overlay, run_public.sh / run_hidden.sh,
the typed oracle, and the three anti-cheat checks. So an OpenCode arm is a different `agent_cmd`
and nothing else. This is that command.

Two stages, and the split is the whole point:

  A. TRUSTED. Still holds EDA_TASK_PATH, so it can read metadata.json and prompt.md and compose the
     episode message. Emits a provenance manifest naming, per section, whether the text was
     TRANSFERRED byte-for-byte from the frozen driver or RESTATED because it describes the action
     surface. The un-alignable part of the prompt frame is thereby enumerated, not asserted.
  B. UNTRUSTED. Scrubs EDA_TASK_PATH / EDA_TASK_ID exactly as llm_agent_driver.py:693 does, then
     execs OpenCode inside bwrap with the task tree not mounted at all. A denylist is a weaker
     control than an absent mount, and here the stronger one is cheap.

Nothing here hardcodes an EDA path. Read-only binds for the tool installation come from
EDA_PROBE_BIND_RO (colon-separated), so tool setup stays out of this file.

Zero-call modes, used by opencode_probe_preflight.py:
  --emit-prompt-only     compose and print the message; make no model call
  --emit-manifest-only   print the section provenance manifest as JSON
  --emit-argv-only       print the exact sandboxed argv that would be executed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------------------------
# The frozen composition, reproduced verbatim from scripts/llm_agent_driver.py so that the
# transferred sections can be proved byte-identical rather than eyeballed. If the driver ever
# changed, opencode_probe_preflight.py would report a mismatch -- the driver is sha256-pinned, so
# that would itself be a finding.
# ---------------------------------------------------------------------------------------------

FROZEN_ROLE = ("You are an expert IC design engineer fixing a bug in a sandboxed workspace, "
               "using a commercial EDA flow. Work iteratively, like a real engineer.\n\n")

FROZEN_TOOLS_ON_PATH = ("- The commercial EDA tools are already installed and on PATH. Just run the "
                        "provided script (e.g. `bash run_public.sh`) directly; do NOT search for tool "
                        "binaries or export PATH — that only wastes actions.\n")

FROZEN_NO_ORACLE = ("The final hidden acceptance test is "
                    "NOT shown to you and there is no answer key — reason about correctness yourself, "
                    "the way an engineer does before signoff. Do not attempt to read hidden tests, "
                    "solutions, or anything outside the workspace.")

FROZEN_CONFIDENCE = ("      When you FINISH, on the SAME message add one final line outside any code block:\n"
                     "      CONFIDENCE: <HIGH | MEDIUM | LOW | ABSTAIN>\n"
                     "      stating how sure you are the fix is correct (ABSTAIN = 'needs human review'). Report "
                     "honestly — a wrong fix declared HIGH is the worst outcome.\n")

# Restated because it describes the action surface, which OpenCode replaces. Every departure from
# the frozen wording lives here and nowhere else.
RESTATED_HOW_TO_ACT = (
    "# HOW TO ACT\n"
    "Use your available tools to work in the workspace: run shell commands to read files and to "
    "run the provided test script for real tool feedback (e.g. `bash run_public.sh`), and write "
    "files to apply your fix. Stop when you are confident the fix is correct.\n")

RESTATED_EDITABLE_ONLY = (
    "- Only the editable file(s) listed above may be changed. For scratch math, run python "
    "(e.g. `python3 -c \"...\"`) rather than writing another file.\n")

RESTATED_BUDGET_ADVICE = (
    "- Spend your limited turns on design iterations (run the script, read the measured numbers, "
    "change the editable file, re-run), not on exploring the setup.\n\n")

RESTATED_CONFIDENCE = (
    "When you are done, add one final line outside any code block:\n"
    "CONFIDENCE: <HIGH | MEDIUM | LOW | ABSTAIN>\n"
    "stating how sure you are the fix is correct (ABSTAIN = 'needs human review'). Report "
    "honestly — a wrong fix declared HIGH is the worst outcome.\n")


def _restated_budget(steps: int) -> str:
    return (f"You have at most {steps} turns. ")


def compose(task_path: Path, steps: int, elicit_confidence: bool) -> tuple[str, list[dict]]:
    """Return (message, section provenance manifest).

    Sections marked TRANSFERRED are byte-identical to the frozen driver's. Sections marked
    RESTATED describe the action surface or the budget unit, which OpenCode necessarily changes.
    """
    meta = json.loads((task_path / "metadata.json").read_text())
    prompt_md = (task_path / "prompt.md").read_text() if (task_path / "prompt.md").is_file() else ""
    editable = list(meta["files"].get("editable", []))
    visible = list(meta["files"].get("visible", []))

    frozen_task = f"# TASK\n{prompt_md}\n\n"
    frozen_ws = (f"# WORKSPACE\nVisible files: {', '.join(visible)}\n"
                 f"Editable files (only these may be changed): {', '.join(editable)}\n\n")

    parts: list[tuple[str, str, str]] = [
        ("role_preamble", "TRANSFERRED", FROZEN_ROLE),
        ("task_text", "TRANSFERRED", frozen_task),
        ("workspace_file_lists", "TRANSFERRED", frozen_ws),
        ("how_to_act", "RESTATED", RESTATED_HOW_TO_ACT),
        ("environment_tools_on_path", "TRANSFERRED", "# ENVIRONMENT\n" + FROZEN_TOOLS_ON_PATH),
        ("environment_editable_only", "RESTATED", RESTATED_EDITABLE_ONLY),
        ("environment_budget_advice", "RESTATED", RESTATED_BUDGET_ADVICE),
        ("budget_sentence", "RESTATED", _restated_budget(steps)),
        ("no_oracle_clause", "TRANSFERRED", FROZEN_NO_ORACLE),
    ]
    if elicit_confidence:
        parts.append(("confidence_elicitation", "RESTATED", "\n\n" + RESTATED_CONFIDENCE))

    # Dry-run negative controls only. This text has no counterpart in any frozen episode and must
    # never be present in a scored episode, so it is a separately named section with its own status
    # and it is refused unless the caller is explicitly in dry-run mode.
    extra = os.environ.get("EDA_PROBE_NEGATIVE_CONTROL", "")
    if extra:
        parts.append(("negative_control_block", "DRY_RUN_ONLY", "\n\n" + extra))

    message = "".join(text for _, _, text in parts)
    manifest = [{"section": name, "status": status,
                 "chars": len(text),
                 "sha256": hashlib.sha256(text.encode()).hexdigest()[:16]}
                for name, status, text in parts]
    return message, manifest


# ---------------------------------------------------------------------------------------------
# Stage B: the sandbox.
# ---------------------------------------------------------------------------------------------

SCRUB = ("EDA_TASK_PATH", "EDA_TASK_ID")

# The frozen driver scrubs two *names*. That is sufficient there because a frozen episode was
# launched from a plain login shell. This probe is launched from inside another agent harness, so
# two further classes of variable must go, and neither is a name the driver ever had to consider:
#
#   1. Anything whose VALUE spells out the repository root or the instance directory. Scrubbing
#      EDA_TASK_PATH while leaving OPENCODE_CONFIG=<repo>/opencode_probe/config/opencode.json
#      hands the agent the real task root by a different name. Measured, not hypothesised -- it was
#      the one leak the sandbox audit found. The config is therefore bound at a neutral in-sandbox
#      path and OPENCODE_CONFIG points there.
#   2. The surrounding harness's own variables and third-party credentials. These have no
#      counterpart in any frozen episode, so leaving them in would put agent-visible content into
#      the probe that the frozen arm never had -- a task-information difference, and separately a
#      credential and de-anonymisation exposure.
#
# The provider key itself stays: OpenCode's child `bash` inherits OpenCode's environment and there
# is no control for that, and the frozen driver's RUN subprocesses saw the key too (it builds
# run_env as os.environ minus the two pointers). That is parity, and it is recorded as parity.
SCRUB_PREFIXES = ("CLAUDE", "ANTHROPIC_", "OLLAMA_", "TMUX", "SSH_", "DBUS_", "AWS_", "OPENAI_")
SCRUB_EXACT = ("AI_AGENT", "DISPLAY", "XAUTHORITY", "API_TIMEOUT_MS", "GIT_EDITOR",
               "TERM_PROGRAM", "TERM_PROGRAM_VERSION",
               # The two pointers to the frozen forwarder. Inside this sandbox the forwarder is not
               # reachable and must not appear to be: B04_HOST names the host where grading deposits
               # the oracles, and EDA_TOOL_ROOT would aim pt_shell at the forwarder shim instead of
               # at the broker client. Scrubbed whether or not the broker is enabled, because a
               # stale pointer surviving by inheritance is a leak in both configurations.
               "EDA_TOOL_ROOT", "B04_HOST")

# Sandbox-internal paths. Neutral by construction: they name neither the repository nor the task.
IN_SANDBOX_CONFIG = "/tmp/opencode-probe-config.json"
RESOLV_STUB = "/run/systemd/resolve/stub-resolv.conf"

# Broker mounts, at neutral in-sandbox paths: they name neither the repository, nor the task, nor
# the remote account. /tmp is a bwrap tmpfs, so these are mount points inside it -- unlike /opt,
# which is already a read-only bind and cannot host new children.
IN_SANDBOX_BROKER = "/tmp/eda-probe"
BROKER_KEY = f"{IN_SANDBOX_BROKER}/key"
BROKER_KNOWN_HOSTS = f"{IN_SANDBOX_BROKER}/known_hosts"
BROKER_BIN = f"{IN_SANDBOX_BROKER}/bin"

# Staged into the sandbox beside the launchers. remote_broker.py and broker_admin.py are absent on
# purpose: the forced command belongs on the remote host, and the component that can write
# authorized_keys must never be inside the sandbox at all.
BROKER_CLIENT_MODULES = ("__init__.py", "broker_protocol.py", "broker_client.py")


@dataclass(frozen=True)
class BrokerMounts:
    """Everything the episode's tool channel needs, and nothing else. The agent holds the private
    key by design: it is a capability for two named operations on one episode, not an account. What
    it must NOT hold is ~/.ssh or the forwarder, which is the whole point of this design."""
    key: Path
    known_hosts: Path
    bin_dir: Path

# Escape hatches that must be set, each closing an injection source that has no counterpart in a
# frozen episode. Values are strings because they go into the child environment.
HARDENING_ENV = {
    "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
    "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
    "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
    "OPENCODE_PURE": "1",
}


def _secret_markers() -> list[str]:
    """Path strings that must not survive into the sandboxed environment, by name or by value."""
    markers = []
    tp = os.environ.get("EDA_TASK_PATH")
    if tp:
        markers += [tp, str(Path(tp).resolve())]
    tid = os.environ.get("EDA_TASK_ID")
    if tid:
        markers.append(tid)
    markers.append(str(REPO_ROOT))
    return [m for m in markers if m]


def scrubbed_env(config: Path, state_dir: Path, *, in_sandbox_config: str = IN_SANDBOX_CONFIG,
                 api_key: str | None = None, broker_enabled: bool = False) -> dict:
    markers = _secret_markers()

    def leaks(value: str) -> bool:
        return any(m in value for m in markers)

    env: dict[str, str] = {}
    for k, v in os.environ.items():
        if k in SCRUB or k in SCRUB_EXACT or k.startswith(SCRUB_PREFIXES):
            continue
        if k == "PATH":
            # PATH cannot simply be dropped; filter the offending components instead, so the EDA
            # tool shims survive while no repository path is disclosed.
            env[k] = ":".join(c for c in v.split(":") if c and not leaks(c))
            continue
        if leaks(v):
            continue
        env[k] = v
    env.update(HARDENING_ENV)
    env["OPENCODE_CONFIG"] = in_sandbox_config
    if api_key:
        env["API_KEY"] = api_key
    # Keep OpenCode's state inside the episode's own directory, so nothing leaks across episodes
    # and the truncation directory is a known path we can control.
    env["XDG_DATA_HOME"] = str(state_dir / "data")
    env["XDG_CACHE_HOME"] = str(state_dir / "cache")
    env["XDG_CONFIG_HOME"] = str(state_dir / "config")
    env["XDG_STATE_HOME"] = str(state_dir / "state")
    if broker_enabled:
        # run_public.sh already dispatches through these two variables, so the broker needs no
        # change to any hash-pinned canonical file. EDA_TOOL_ROOT and B04_HOST are in SCRUB_EXACT
        # and so are already gone: the forwarder is not reachable from inside the sandbox and must
        # not appear to be.
        env["EDA_PT_CMD"] = f"{BROKER_BIN}/pt_shell"
        env["EDA_HSPICE_CMD"] = f"{BROKER_BIN}/hspice"
        env["EDA_BROKER_KEY"] = BROKER_KEY
        env["EDA_BROKER_KNOWN_HOSTS"] = BROKER_KNOWN_HOSTS
    return env


def bwrap_argv(workspace: Path, state_dir: Path, opencode: Path, inner: list[str],
               ro_binds: list[str], seal_tool_output: bool,
               config: Path | None = None, resolv: Path | None = None,
               broker: "BrokerMounts | None" = None) -> list[str]:
    """Sandbox in which the task tree is simply not mounted."""
    argv = [
        "bwrap",
        "--unshare-pid", "--unshare-ipc", "--unshare-uts",
        "--die-with-parent",
        "--proc", "/proc", "--dev", "/dev",
        "--tmpfs", "/tmp",
    ]
    for d in ("/usr", "/bin", "/sbin", "/lib", "/lib64", "/etc", "/opt"):
        if Path(d).exists():
            argv += ["--ro-bind-try", d, d]
    for b in ro_binds:
        b = b.strip()
        if b and Path(b).exists():
            argv += ["--ro-bind-try", b, b]
    # writable: the agent workspace and OpenCode's own state, nothing else
    argv += ["--bind", str(workspace), str(workspace)]
    argv += ["--bind", str(state_dir), str(state_dir)]
    # the opencode binary itself
    argv += ["--ro-bind-try", str(opencode.parent), str(opencode.parent)]
    if seal_tool_output:
        # Strongest available control on truncation-overflow recovery: make the directory OpenCode
        # writes full tool output into read-only, so an overflow cannot be persisted and therefore
        # cannot be read back. Whether OpenCode degrades gracefully or fails here is a dry-run
        # question; see docs/opencode_scaffold_probe_scope.md check 6.
        sealed = state_dir / "sealed"
        sealed.mkdir(parents=True, exist_ok=True)
        for p in (state_dir / "data/opencode/tool-output", Path("/tmp/opencode")):
            argv += ["--ro-bind", str(sealed), str(p)]
    if config is not None:
        # Bound at a neutral path so the agent's own environment never spells out the repository
        # root -- and bound FROM a neutral path too, because /proc/self/mountinfo discloses the
        # source of every bind. Binding the repository copy directly closed the environment leak
        # and reopened the same disclosure one file lower down; the escape battery caught it.
        staged = state_dir / "opencode.json"
        staged.write_bytes(Path(config).read_bytes())
        argv += ["--ro-bind", str(staged), IN_SANDBOX_CONFIG]
    if resolv is not None:
        # The network namespace is deliberately NOT unshared -- the probe calls a remote model API.
        # But /run is not mounted, and on this host /etc/resolv.conf is a symlink into /run, so
        # without this the sandbox has working egress and no name resolution: every model request
        # would fail as an infrastructure fault. Binding one file is narrower than exposing /run.
        argv += ["--ro-bind", str(resolv), RESOLV_STUB]
    if broker is not None:
        # The episode's tool capability: one private key, one pinned host key, two launchers. All
        # read-only -- the agent must not be able to replace its own key with one whose forced
        # command names a different episode. ~/.ssh is still not mounted and neither is the
        # forwarder, which is the difference between a capability and an account.
        argv += ["--ro-bind", str(broker.key), BROKER_KEY]
        argv += ["--ro-bind", str(broker.known_hosts), BROKER_KNOWN_HOSTS]
        argv += ["--ro-bind", str(broker.bin_dir), BROKER_BIN]
    argv += ["--chdir", str(workspace), "--"]
    return argv + inner


def stage_broker_bin(state_dir: Path) -> Path:
    """Materialise the in-sandbox tool channel: two launchers and the client library.

    The launchers must be NAMED pt_shell and hspice, because broker_client selects its op from
    argv[0] -- the filename is load-bearing, not cosmetic. The client itself is reached through
    lib/, so its own filename does not have to be either of those.

    Only the client half is staged. remote_broker.py belongs on the remote host, and broker_admin.py
    -- the one component holding a credential that can write authorized_keys -- must never be inside
    the sandbox at all.
    """
    src = REPO_ROOT / "scripts/eda_broker"
    bin_dir = Path(state_dir) / "broker/bin"
    lib = bin_dir / "lib/eda_broker"
    lib.mkdir(parents=True, exist_ok=True)
    for name in BROKER_CLIENT_MODULES:
        (lib / name).write_bytes((src / name).read_bytes())
    for shim in broker_shim_names():
        p = bin_dir / shim
        p.write_text("#!/bin/sh\n"
                     f"exec python3 {BROKER_BIN}/lib/eda_broker/broker_client.py \"$@\"\n")
        p.chmod(0o755)
    return bin_dir


def broker_shim_names() -> tuple:
    """The shim names come from the op table, so adding an op cannot silently forget its launcher."""
    scripts = str(REPO_ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from eda_broker import broker_protocol as bp
    return tuple(sorted(bp.OP_BY_SHIM))


def write_resolv(state_dir: Path) -> Path:
    """Materialise the host's upstream nameservers as an explicit, recorded sandbox file."""
    servers: list[str] = []
    try:
        out = subprocess.run(["resolvectl", "status"], capture_output=True, text=True, timeout=15)
        for line in out.stdout.splitlines():
            if "DNS Servers:" in line:
                servers += line.split(":", 1)[1].split()
    except Exception:
        pass
    if not servers:
        servers = ["8.8.8.8", "8.8.4.4"]
    ipv4 = [s for s in dict.fromkeys(servers) if ":" not in s][:3]
    p = state_dir / "resolv.conf"
    p.write_text("".join(f"nameserver {s}\n" for s in ipv4) or "nameserver 8.8.8.8\n")
    return p


def _provider_key() -> str:
    """Same credential and same convention as the frozen arm: .env TR_API_KEY exported as API_KEY
    (scripts/phase8a_run.py:312). The probe introduces no new credential path."""
    key = os.environ.get("API_KEY") or os.environ.get("TR_API_KEY") or ""
    if not key:
        env_file = REPO_ROOT / ".env"
        if env_file.is_file():
            for line in env_file.read_text().splitlines():
                if line.startswith("TR_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit("opencode_probe_agent: TR_API_KEY not provisioned (expected in .env)")
    return key


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--agent", default="probe")
    ap.add_argument("--model", default="probe/deepseek-v4-pro")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--log", type=Path, help="write the OpenCode JSON event stream here")
    ap.add_argument("--elicit-confidence", action="store_true")
    ap.add_argument("--no-seal-tool-output", action="store_true",
                    help="disable the read-only overlay on the truncation directory; the resulting "
                         "run has a recoverable observation cap and must be recorded as such")
    ap.add_argument("--emit-prompt-only", action="store_true")
    ap.add_argument("--emit-manifest-only", action="store_true")
    ap.add_argument("--emit-argv-only", action="store_true")
    ap.add_argument("--broker-dir", type=Path, default=None,
                    help="a provision output directory holding `key` and `known_hosts`. When given, "
                         "the episode gets a real PrimeTime/HSPICE channel as a two-operation "
                         "capability; ~/.ssh and the forwarder stay unmounted either way.")
    a = ap.parse_args()

    task_path = Path(os.environ["EDA_TASK_PATH"])       # stage A only; never crosses into stage B
    message, manifest = compose(task_path, a.steps, a.elicit_confidence)

    if a.emit_manifest_only:
        print(json.dumps(manifest, indent=2))
        return 0
    if a.emit_prompt_only:
        sys.stdout.write(message)
        return 0

    workspace = Path(os.environ["EDA_WORKSPACE"]).resolve()
    timeout = int(os.environ.get("EDA_TIMEOUT", "1800"))
    opencode = Path(shutil.which("opencode") or (Path.home() / ".opencode/bin/opencode"))
    if not opencode.exists():
        print("opencode binary not found", file=sys.stderr)
        return 127

    state_dir = workspace.parent / f"{workspace.name}.opencode"
    for sub in ("data", "cache", "config", "state"):
        (state_dir / sub).mkdir(parents=True, exist_ok=True)

    inner = [str(opencode), "run",
             "--agent", a.agent,
             "--model", a.model,
             "--format", "json",
             "--title", "probe",
             message]
    broker = None
    if a.broker_dir is not None:
        key = a.broker_dir / "key"
        kh = a.broker_dir / "known_hosts"
        for p in (key, kh):
            if not p.is_file():
                raise SystemExit(f"opencode_probe_agent: --broker-dir is missing {p.name}")
        broker = BrokerMounts(key=key, known_hosts=kh, bin_dir=stage_broker_bin(state_dir))

    argv = bwrap_argv(workspace, state_dir, opencode, inner,
                      ro_binds=os.environ.get("EDA_PROBE_BIND_RO", "").split(":"),
                      seal_tool_output=not a.no_seal_tool_output,
                      config=a.config, resolv=write_resolv(state_dir), broker=broker)

    if a.emit_argv_only:
        # redact the message, which is many KB and is emitted separately
        shown = [x if x is not message else "<EPISODE_MESSAGE>" for x in argv]
        print(json.dumps(shown, indent=2))
        return 0

    env = scrubbed_env(a.config, state_dir, api_key=_provider_key(),
                       broker_enabled=broker is not None)
    assert not any(k in env for k in SCRUB), "oracle pointers survived the scrub"
    leaked = {k for k, v in env.items() if k != "PATH" and any(m in v for m in _secret_markers())}
    assert not leaked, f"repository/task path survived the scrub in: {sorted(leaked)}"

    # Wall clock, mirroring the runner's own subprocess timeout with margin, as the driver does.
    proc = subprocess.run(argv, env=env, capture_output=True, text=True,
                          timeout=max(30, timeout - 30))
    if a.log:
        a.log.parent.mkdir(parents=True, exist_ok=True)
        a.log.write_text(json.dumps({
            "returncode": proc.returncode,
            "prompt_sections": manifest,
            "stdout": proc.stdout,
            "stderr": proc.stderr[-20000:],
        }, indent=2))
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
