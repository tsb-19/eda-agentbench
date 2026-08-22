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

`--cost-cap-cny` adds a live spend cap, enforced on the event stream as each request's token record
arrives and fail-closed: on breach the process group is killed and the episode is measurement-invalid
rather than a model result that happens to stop early. See CostGovernor for why the cap has to be
live, and for how the record proves it was.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
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
    argv[0] -- the filename is load-bearing, not cosmetic. They are therefore PYTHON scripts with a
    shebang, not shell wrappers. A `#!/bin/sh` wrapper doing `exec python3 .../broker_client.py "$@"`
    loses the name: Python sets sys.argv[0] to the script it was handed, so the client saw
    `broker_client.py` and refused every call with UNKNOWN_SHIM. That is exactly what preflight
    control 14 observed, and it would have broken every episode of the arm. With a shebang the kernel
    hands Python the launcher's own path, so argv[0] is `.../pt_shell` and the op resolves.

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
        p.write_text(broker_launcher_source())
        p.chmod(0o755)
    return bin_dir


def broker_launcher_source(python: str = "/usr/bin/env python3") -> str:
    """The launcher, whose FILENAME selects the op. See stage_broker_bin for why it is not a shell
    wrapper. It adds its own `lib/` to sys.path and hands its own argv straight through."""
    return (f"#!{python}\n"
            "# Invoked as pt_shell or hspice by run_public.sh via EDA_PT_CMD / EDA_HSPICE_CMD.\n"
            "# The op is selected from argv[0], i.e. from THIS FILE'S NAME, so the name is part of\n"
            "# the interface. Nothing here parses or rewrites the arguments.\n"
            "import os\n"
            "import sys\n"
            "sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))\n"
            "from eda_broker import broker_client\n"
            "raise SystemExit(broker_client.main(sys.argv))\n")


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


# ---------------------------------------------------------------------------------------------
# Cost governor and request ledger.
# ---------------------------------------------------------------------------------------------

EXIT_COST_CAP = 121
EXIT_WALL_CLOCK = 122

MODELS_ARM2 = REPO_ROOT / "phase8a/models_arm2.json"


@dataclass(frozen=True)
class Rates:
    """CNY per 1M tokens. Read from the arm-2 model config rather than restated here, so the probe's
    ledger and the frozen arm's ledger cannot drift apart silently. This uses a frozen file as a
    PRICE REFERENCE; it pools, sums and differences no frozen outcome."""
    input_per_m: float
    output_per_m: float
    source: str

    @classmethod
    def from_arm2(cls, path: Path = MODELS_ARM2, model: str = "deepseek-v4-pro") -> "Rates":
        for m in json.loads(Path(path).read_text()).get("models", []):
            if m.get("name") == model:
                return cls(float(m["price_in_per_m"]), float(m["price_out_per_m"]),
                           f"{Path(path).name}:{model}")
        raise SystemExit(f"opencode_probe_agent: no rates for {model!r} in {path}")


def billed(tokens: dict) -> tuple[int, int, int]:
    """Split one token record into (input_billed, output, reasoning).

    OpenCode's `step_finish` reports total = input + output + reasoning + cache.read, so the four are
    disjoint. Cache traffic is billed AS INPUT, which is the difference between an orientation figure
    and a usable one: dry-run episode 2 read 485 888 cached tokens against 36 311 fresh input ones,
    so ignoring cache turns CNY 6.41 into CNY 0.58. Cache writes go on the same side; they were zero
    in both dry-run episodes, so this still reproduces the published figures exactly.
    """
    cache = tokens.get("cache") or {}
    inp = int(tokens.get("input") or 0) + int(cache.get("read") or 0) + int(cache.get("write") or 0)
    return inp, int(tokens.get("output") or 0), int(tokens.get("reasoning") or 0)


def cost_range(input_billed: int, output: int, reasoning: int, rates: Rates) -> tuple[float, float]:
    """(lower, upper) CNY. The two differ only in whether reasoning tokens are billed as output; the
    gateway reports `cost: 0` and does not say. A cap is enforced on the UPPER figure -- the safe
    direction for runaway protection, and the wrong direction for predicting spend."""
    fixed = input_billed * rates.input_per_m / 1e6
    return (round(fixed + output * rates.output_per_m / 1e6, 4),
            round(fixed + (output + reasoning) * rates.output_per_m / 1e6, 4))


@dataclass
class CostGovernor:
    """A hard spend cap enforced where the ledger is produced.

    `opencode run --format json` emits one JSON object per line and each `step_finish` carries that
    request's token counts, so the event stream IS the ledger and it arrives one request at a time.
    Accumulating there and killing the process group on breach is a live cap; totalling afterwards is
    an audit. This project has a rule about that difference, so the governor RECORDS whether it ran
    live -- the arrival offsets of the events it saw -- rather than asserting it. If OpenCode ever
    buffers its stdout, `live` comes out false and the wall clock was the only real protection; that
    has to be reported, not assumed away.

    The cap is not decorative. With `compaction.auto: false` history grows monotonically, so cached
    input grows with the square of the turn count (80 896 tokens at 10 turns, 485 888 at 26), and
    extrapolating that curve to the configured 60-turn ceiling clears CNY 20.
    """
    cap_cny: float
    rates: Rates
    t0: float
    steps: list = field(default_factory=list)
    tripped_at_step: int | None = None

    def observe(self, line: str, now: float) -> bool:
        """Feed one event-stream line. Returns True once the cap is breached."""
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
        if not isinstance(obj, dict) or obj.get("type") != "step_finish":
            return False
        part = obj.get("part") or {}
        inp, out, rea = billed(part.get("tokens") or {})
        self.steps.append({"step": len(self.steps) + 1,
                           "input_billed": inp, "output": out, "reasoning": rea,
                           "provider_cost": part.get("cost"),
                           "received_offset_s": round(now - self.t0, 3)})
        if self.cost()[1] > self.cap_cny and self.tripped_at_step is None:
            self.tripped_at_step = len(self.steps)
            return True
        return False

    def totals(self) -> dict:
        return {"requests": len(self.steps),
                "input_billed": sum(s["input_billed"] for s in self.steps),
                "output": sum(s["output"] for s in self.steps),
                "reasoning": sum(s["reasoning"] for s in self.steps)}

    def cost(self) -> tuple[float, float]:
        t = self.totals()
        return cost_range(t["input_billed"], t["output"], t["reasoning"], self.rates)

    def liveness(self) -> dict:
        """Evidence that the cap was enforced during the run rather than after it."""
        offs = [s["received_offset_s"] for s in self.steps]
        spread = round(max(offs) - min(offs), 3) if len(offs) > 1 else 0.0
        return {"events_observed": len(offs),
                "first_event_offset_s": min(offs) if offs else None,
                "last_event_offset_s": max(offs) if offs else None,
                "arrival_spread_s": spread,
                "live": bool(len(offs) > 1 and spread >= 1.0),
                "note": ("live means the token records arrived spread out over the run, so the cap "
                         "could have interrupted it. false means the governor degenerated into a "
                         "post-hoc audit and the wall clock was the only live bound.")}

    def record(self) -> dict:
        lo, hi = self.cost()
        return {"cap_cny": self.cap_cny,
                "rates_cny_per_M": {"input": self.rates.input_per_m,
                                    "output": self.rates.output_per_m,
                                    "source": self.rates.source},
                "cost_cny_lower": lo, "cost_cny_upper": hi,
                "enforced_on": "upper",
                "cap_exceeded": self.tripped_at_step is not None,
                "tripped_at_step": self.tripped_at_step,
                "totals": self.totals(), "per_step": self.steps,
                "liveness": self.liveness()}


def _kill_group(pid: int, grace: float = 10.0) -> None:
    """SIGTERM the whole process group, wait, then SIGKILL.

    Deliberately a local copy rather than an import of remote_broker._kill_group: that module deletes
    SSH_ORIGINAL_COMMAND and installs SIGTERM/SIGINT/SIGHUP handlers at import time, which is right
    for a forced command and wrong for anything that merely wants to kill a child.

    The group, not the process: bwrap starts opencode, opencode starts bash, bash starts
    run_public.sh, and run_public.sh starts the broker client, which holds an ssh connection to a
    remote PrimeTime. Killing only the top of that chain leaves a licence checked out.
    """
    try:
        pgid = os.getpgid(pid)
    except OSError:
        return
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 2.0)):
        try:
            os.killpg(pgid, sig)
        except OSError:
            return
        end = time.time() + wait
        while time.time() < end:
            try:
                os.killpg(pgid, 0)
            except OSError:
                return
            time.sleep(0.1)


def run_governed(argv: list, env: dict, deadline_sec: float,
                 governor: "CostGovernor | None") -> dict:
    """Run the sandbox, streaming its event stream through the governor.

    Two independent live bounds, because they fail in different ways. The governor needs OpenCode to
    flush its stdout; the wall clock needs nothing from OpenCode at all and runs in its own thread, so
    a model that stops responding mid-request is still bounded. Whichever fires, the process GROUP is
    killed and the episode is measurement-invalid -- not a model result with a short transcript.
    """
    proc = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL, start_new_session=True)
    t0 = time.time()
    if governor is not None:
        governor.t0 = t0
    state = {"reason": None}
    done = threading.Event()

    def watchdog():
        if not done.wait(deadline_sec):
            state["reason"] = state["reason"] or "wall_clock"
            _kill_group(proc.pid)

    err_chunks: list = []

    def drain_stderr():
        try:
            err_chunks.append(proc.stderr.read())
        except Exception:
            pass

    threads = [threading.Thread(target=watchdog, daemon=True),
               threading.Thread(target=drain_stderr, daemon=True)]
    for t in threads:
        t.start()

    out_parts: list = []
    for raw in proc.stdout:                        # readline on a pipe: yields as events arrive
        out_parts.append(raw)
        if governor is not None and governor.observe(raw.decode("utf-8", "replace"), time.time()):
            state["reason"] = "cost_cap_exceeded"
            _kill_group(proc.pid)
            break
    done.set()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        _kill_group(proc.pid, grace=2.0)
        proc.wait(timeout=30)
    for t in threads:
        t.join(timeout=15)
    try:
        out_parts.append(proc.stdout.read())       # anything still buffered after a break
    except Exception:
        pass

    return {"returncode": proc.returncode,
            "stdout": b"".join(p for p in out_parts if p).decode("utf-8", "replace"),
            "stderr": b"".join(c for c in err_chunks if c).decode("utf-8", "replace"),
            "wall_clock_sec": round(time.time() - t0, 1),
            "terminated_by": state["reason"]}


MODEL_ID_KEYS = ("modelID", "modelId", "model", "small_model")


def _walk_model_ids(obj, out: dict) -> None:
    """Every model identifier anywhere in a JSON tree, not only the ones on assistant messages.

    The question is whether a hidden title / summary / compaction agent ever routed to a second
    model. A scan restricted to `role == "assistant"` could not answer it, because what a hidden
    agent writes need not be an assistant message in the session it was summarising.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in MODEL_ID_KEYS and isinstance(v, str) and v:
                out[v] = out.get(v, 0) + 1
            else:
                _walk_model_ids(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_model_ids(v, out)


def session_ledger(state_dir: Path) -> dict:
    """The request ledger, read out of OpenCode's own session storage.

    Independent of the event stream on purpose: check 9 asks whether two instruments agree on the
    request count, and two readings of one file are one instrument. `json_files_scanned` is reported
    so an empty ledger is distinguishable from a ledger of nothing -- a scan that silently found no
    storage at all would otherwise report "only the pinned model" for a run that used five.
    """
    models: dict = {}
    assistant: dict = {}
    files = 0
    messages = 0
    tokens = {"input_billed": 0, "output": 0, "reasoning": 0}
    for p in sorted(Path(state_dir).rglob("*.json")):
        if not p.is_file():
            continue
        files += 1
        try:
            obj = json.loads(p.read_text(errors="ignore"))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        _walk_model_ids(obj, models)
        if isinstance(obj, dict) and obj.get("role") == "assistant":
            messages += 1
            mid = str(obj.get("modelID") or obj.get("model") or "?")
            assistant[mid] = assistant.get(mid, 0) + 1
            inp, out, rea = billed(obj.get("tokens") or {})
            tokens["input_billed"] += inp
            tokens["output"] += out
            tokens["reasoning"] += rea
    return {"json_files_scanned": files, "assistant_messages": messages,
            "assistant_models": assistant, "model_ids_anywhere": models,
            "assistant_tokens": tokens}


# The three provisioned balances, in the order they are to be spent. Listed rather than computed
# because the names are off by one against the slot numbers: slot 2 is TR_API_KEY_1. A formula would
# have silently selected the wrong balance, and a wrong balance looks exactly like an exhausted one.
KEY_SLOTS = ("TR_API_KEY", "TR_API_KEY_1", "TR_API_KEY_2")


def _provider_key() -> str:
    """Same credential and same convention as the frozen arm: a .env key exported as API_KEY
    (scripts/phase8a_run.py:312). The probe introduces no new credential path.

    EDA_PROBE_KEY_SLOT selects which of the three provisioned balances to spend, 1 by default.
    Rotation is explicit rather than automatic: a driver that moved to the next key by itself on
    failure could not distinguish an exhausted balance from a gateway fault, and this project counts
    the second as measurement-invalid rather than as a reason to spend more money.
    """
    slot = os.environ.get("EDA_PROBE_KEY_SLOT", "1").strip()
    if slot not in ("1", "2", "3"):
        raise SystemExit(f"opencode_probe_agent: EDA_PROBE_KEY_SLOT must be 1, 2 or 3; got {slot!r}")
    name = KEY_SLOTS[int(slot) - 1]
    key = os.environ.get("API_KEY") or os.environ.get(name) or ""
    if not key:
        env_file = REPO_ROOT / ".env"
        if env_file.is_file():
            for line in env_file.read_text().splitlines():
                if line.startswith(name + "="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit(f"opencode_probe_agent: {name} not provisioned (expected in .env); "
                         f"EDA_PROBE_KEY_SLOT={slot}")
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
    ap.add_argument("--cost-cap-cny", type=float, default=0.0,
                    help="hard spend cap for this episode, enforced live on the event stream and "
                         "fail-closed: on breach the process group is killed and the episode is "
                         "measurement-invalid. 0 disables the governor.")
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
    governor = (CostGovernor(cap_cny=a.cost_cap_cny, rates=Rates.from_arm2(), t0=time.time())
                if a.cost_cap_cny > 0 else None)
    run = run_governed(argv, env, max(30, timeout - 30), governor)
    ledger = session_ledger(state_dir)
    if a.log:
        a.log.parent.mkdir(parents=True, exist_ok=True)
        a.log.write_text(json.dumps({
            "returncode": run["returncode"],
            "prompt_sections": manifest,
            "stdout": run["stdout"],
            "stderr": run["stderr"][-20000:],
            "wall_clock_sec": run["wall_clock_sec"],
            "terminated_by": run["terminated_by"],
            "cost_governor": governor.record() if governor else None,
            "session_ledger": ledger,
            "broker_enabled": broker is not None,
        }, indent=2))
    sys.stdout.write(run["stdout"])
    sys.stderr.write(run["stderr"])
    if run["terminated_by"] == "cost_cap_exceeded":
        sys.stderr.write("opencode_probe_agent: MEASUREMENT_INVALID cost_cap_exceeded\n")
        return EXIT_COST_CAP
    if run["terminated_by"] == "wall_clock":
        sys.stderr.write("opencode_probe_agent: MEASUREMENT_INVALID wall_clock\n")
        return EXIT_WALL_CLOCK
    return run["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
