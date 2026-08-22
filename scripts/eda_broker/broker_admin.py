#!/usr/bin/env python3
"""Host-side provisioning for the restricted-SSH EDA broker.

This is the only component holding a credential that can write authorized_keys, and it runs outside
the sandbox. The agent never executes any of it.

Per episode: one ed25519 key, one manifest, one managed authorized_keys line, and a teardown that
verifies its own effect rather than assuming it.

For the formal arm the per-episode path is not used. All 48 keys are installed in ONE atomic rewrite
under ONE lock before the arm and removed in one after, so authorized_keys is byte-static while
episodes are running -- see provision_batch. $HOME on b04 is NFS, and nfs(5) disclaims both
cluster-coherent caching and lock survival across a partition, so 96 mutual-exclusion operations
against the operator's three real login keys is a bet its own manual page declines to back. Nothing
is given up by batching: K_i => E_i lives in each line's command=, not in when the line was written.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eda_broker import authorized_keys_block as akb   # noqa: E402
from eda_broker import broker_protocol as bp          # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEPLOY_RECORD = REPO / "opencode_probe/broker/deploy.json"
BATCH_RECORD = REPO / "opencode_probe/broker/batch.json"
DEFAULT_HOST = "tsb@b04"
DEFAULT_ROOT = "/home/tsb/eda-probe-broker"
REMOTE_AK = "~/.ssh/authorized_keys"

FAMILY_OP = {"p15_sta_handoff": "sta_public", "p16_spice_handoff": "spice_public"}
FAMILIES = tuple(FAMILY_OP)

# docs/opencode_probe_analysis_plan.md stage 1.
FORMAL_INSTANCE_IDS = tuple(f"p15_eval_{i:04d}" for i in range(4, 16))
FORMAL_CONDITIONS = ("Base", "BundleS")
FORMAL_REPS = (0, 1)
CONDITION_DIR = {"Base": "base", "BundleS": "bundles"}

# Shipped to <root>/lib/eda_broker/ by deploy.
SHIPPED = ("__init__.py", "broker_protocol.py", "authorized_keys_block.py", "remote_broker.py")

JSON_SENTINEL = "@@EDABROKER-JSON@@"
STALE_PROVISION_SEC = 6 * 3600


class BatchActive(RuntimeError):
    """A batch is live, so per-episode authorized_keys mutation is refused.

    Requirement E is that the file is byte-static for the whole formal arm. Enforcing it here means
    no retry path, helper or operator habit can quietly reintroduce 48 rewrites on NFS.
    """


class RemoteError(RuntimeError):
    """A remote step failed. Deliberately distinct from a refusal: this is infrastructure."""


def _refuse_if_batch_active() -> None:
    if BATCH_RECORD.is_file():
        raise BatchActive(
            f"{BATCH_RECORD} exists: a batch is live and authorized_keys must stay static. "
            f"Run `teardown-batch` first.")


# ---------------------------------------------------------------------------------------------
# pure functions
# ---------------------------------------------------------------------------------------------

def authorized_keys_line(episode_id: str, pubkey: str, root: str, from_addr) -> str:
    """`restrict` first, because it is default-deny: it implies no-pty, no-X11-forwarding,
    no-port-forwarding, no-agent-forwarding and no-user-rc, and it denies whatever a future
    OpenSSH invents. `command=` is what kills scp, sftp and rsync -- each needs to start its own
    server binary on the remote and none of them ever gets to run one."""
    if not bp.valid_episode_id(episode_id):
        raise ValueError(f"illegal episode id: {episode_id!r}")
    pubkey = pubkey.strip()
    if "\n" in pubkey or "\r" in pubkey:
        raise ValueError("public key must be a single line")
    opts = ["restrict"]
    if from_addr:
        opts.append(f'from="{from_addr}"')
    opts.append(f'command="{root}/broker.sh {episode_id}"')
    return ",".join(opts) + " " + pubkey


def episode_id(instance: str, condition: str, rep) -> str:
    """One compound token per episode, so `argv` stays length-2 and the forced command needs no
    additional fields. The client cannot forge it: it is in authorized_keys, not in the protocol."""
    ep = f"{instance}__{condition}__rep{int(rep)}"
    if not bp.valid_episode_id(ep):
        raise ValueError(f"illegal episode id from ({instance!r}, {condition!r}, {rep!r}): {ep!r}")
    return ep


def formal_arm_plan() -> list:
    """The 48 episodes of stage 1, derived rather than listed, so it cannot drift from the analysis
    plan silently. No selection on prior informativeness: all twelve instances, both conditions."""
    return [{"episode": episode_id(inst, cond, rep),
             "instance": f"{inst}_{CONDITION_DIR[cond]}",
             "instance_id": inst, "condition": cond, "rep": rep}
            for inst in FORMAL_INSTANCE_IDS for cond in FORMAL_CONDITIONS for rep in FORMAL_REPS]


def find_instance(instance: str) -> Path:
    for fam in FAMILIES:
        p = REPO / "tasks" / fam / instance
        if p.is_dir():
            return p
    raise ValueError(f"no such instance directory in any family: {instance!r}")


def validate_batch_plan(plan) -> list:
    """Validate the WHOLE plan before any key exists.

    Everything that can fail per episode -- an illegal id, a duplicate, a missing instance -- fails
    here, so a bad plan leaves zero probe keys authorized rather than a partially-authorized arm.
    """
    out, seen = [], set()
    for entry in plan:
        ep = entry.get("episode")
        if not bp.valid_episode_id(ep):
            raise ValueError(f"illegal episode id: {ep!r}")
        if ep in seen:
            raise ValueError(f"duplicate episode id in plan: {ep!r}")
        seen.add(ep)
        path = find_instance(entry["instance"])
        out.append(dict(entry, instance_path=path))
    if not out:
        raise ValueError("empty batch plan")
    return out


def build_manifest(instance, caps_override=None) -> dict:
    """sha256 for every canonical input of the instance's op. Contains no oracle and no task
    content, so its presence on the remote is not itself a disclosure."""
    instance = Path(instance)
    op_name = FAMILY_OP[instance.parent.name]
    op = bp.OPS[op_name]
    sha = {}
    for name in op.canonical:
        f = instance / "files" / name
        if not f.is_file():
            raise SystemExit(f"broker_admin: canonical input missing: {f}")
        sha[name] = hashlib.sha256(f.read_bytes()).hexdigest()
    m = {"ops": [op_name], "sha256": sha, "built": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if caps_override:
        # Preflight-only, and the broker will honour it only where it LOWERS a cap.
        m["caps_override"] = dict(caps_override)
    return m


# ---------------------------------------------------------------------------------------------
# remote plumbing
# ---------------------------------------------------------------------------------------------

def _ssh(host: str, script: str, input_bytes=None, timeout: int = 180):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, "bash", "-lc", script],
                          input=input_bytes, capture_output=True, timeout=timeout)


def _remote_py(host: str, root: str, code: str, py: str = "python3", timeout: int = 180):
    """Run a python snippet on the remote, with <root>/lib importable.

    The snippet is base64'd into the command line rather than quoted into it: base64 is
    shell-inert, so no episode id, path or key ever passes through a quoting layer. It reports by
    printing one sentinel-prefixed JSON line, because b04's login shell writes a banner and an rc
    error of its own and stdout is not guaranteed to be ours alone.
    """
    prelude = (f"import sys, json, os\n"
               f"sys.path.insert(0, {root + '/lib'!r})\n"
               f"def report(obj):\n"
               f"    print({JSON_SENTINEL!r} + json.dumps(obj))\n")
    blob = base64.b64encode((prelude + code).encode()).decode()
    cmd = f"{shlex.quote(py)} -c \"import base64;exec(base64.b64decode('{blob}'))\""
    r = _ssh(host, cmd, timeout=timeout)
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith(JSON_SENTINEL):
            return json.loads(line[len(JSON_SENTINEL):])
    raise RemoteError(f"no framed reply (rc={r.returncode}); "
                      f"stderr={r.stderr.decode('utf-8', 'replace')[-400:]}")


def _deploy_record() -> dict:
    if not DEPLOY_RECORD.is_file():
        raise RemoteError(f"{DEPLOY_RECORD} missing: run `deploy` first")
    return json.loads(DEPLOY_RECORD.read_text())


def _hostname(host: str) -> str:
    return host.split("@", 1)[-1]


def _pinned_host_key(host: str, allow_keyscan: bool = False) -> str:
    """Prefer the entry already in the operator's known_hosts. ssh-keyscan is a last resort because
    it trusts whatever answers on the port."""
    kh = Path.home() / ".ssh/known_hosts"
    if kh.is_file():
        r = subprocess.run(["ssh-keygen", "-F", _hostname(host), "-f", str(kh)],
                           capture_output=True, text=True)
        lines = [l for l in r.stdout.splitlines() if l.strip() and not l.startswith("#")]
        if lines:
            return "\n".join(lines) + "\n"
    if not allow_keyscan:
        raise RemoteError(
            f"no known_hosts entry for {_hostname(host)} and --allow-keyscan not given. "
            "ssh-keyscan trusts whatever answers; pin the key deliberately instead.")
    r = subprocess.run(["ssh-keyscan", "-T", "10", _hostname(host)],
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.strip() and not l.startswith("#")]
    if not lines:
        raise RemoteError(f"ssh-keyscan produced nothing for {_hostname(host)}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------
# deploy
# ---------------------------------------------------------------------------------------------

def deploy(host=DEFAULT_HOST, root=DEFAULT_ROOT, allow_keyscan=False) -> dict:
    """Install the broker on the remote host and verify the installation by reading it back."""
    here = Path(__file__).resolve().parent

    # 1. resolve the interpreter and the two tools from the LOGIN shell, as the forwarder does.
    r = _ssh(host, "command -v python3; command -v pt_shell; command -v hspice; true", timeout=120)
    found = [l for l in r.stdout.decode().splitlines() if l.startswith("/")]
    py = next((l for l in found if l.endswith("python3")), None)
    pt = next((l for l in found if l.endswith("pt_shell")), None)
    hs = next((l for l in found if l.endswith("hspice")), None)
    if not py:
        raise RemoteError(f"no python3 on the remote login PATH: {r.stdout!r} {r.stderr!r}")

    # 2 + 3 + 4. create the tree, install the modules and render broker.sh -- one remote python
    # call, so the deploy record can be honest about exactly what crossed.
    payload = {f"lib/eda_broker/{n}": base64.b64encode((here / n).read_bytes()).decode()
               for n in SHIPPED}
    tmpl = (here / "broker_sh.template").read_text()
    broker_sh = tmpl.replace("@PYTHON3@", py).replace("@ROOT@", root)
    payload["broker.sh"] = base64.b64encode(broker_sh.encode()).decode()

    code = f"""
import base64, hashlib, os
root = {root!r}
payload = {payload!r}
for d in (root, root + "/lib", root + "/lib/eda_broker", root + "/ep"):
    os.makedirs(d, exist_ok=True)
    os.chmod(d, 0o700)
sha = {{}}
for rel, b64 in payload.items():
    blob = base64.b64decode(b64)
    dest = os.path.join(root, rel)
    with open(dest, "wb") as fh:
        fh.write(blob)
    os.chmod(dest, 0o700 if rel.endswith(".sh") else 0o600)
    # Re-read from disk rather than hashing the buffer we just wrote: the claim is about the
    # installed file, not about our memory of it.
    with open(dest, "rb") as fh:
        sha[rel] = hashlib.sha256(fh.read()).hexdigest()
report({{"sha256": sha, "root": root}})
"""
    remote = _remote_py(host, root, code, py=py, timeout=300)

    # 6. verify: every installed file's remote sha256 must equal the local one.
    local_sha = {f"lib/eda_broker/{n}": hashlib.sha256((here / n).read_bytes()).hexdigest()
                 for n in SHIPPED}
    local_sha["broker.sh"] = hashlib.sha256(broker_sh.encode()).hexdigest()
    mismatched = {k: (local_sha[k], remote["sha256"].get(k))
                  for k in local_sha if remote["sha256"].get(k) != local_sha[k]}
    if mismatched:
        raise RemoteError(f"installed files do not match their sources: {mismatched}")

    # 5. pin the host key.
    host_key = _pinned_host_key(host, allow_keyscan=allow_keyscan)
    fp = hashlib.sha256(host_key.encode()).hexdigest()

    rec = {"generated_by": "scripts/eda_broker/broker_admin.py deploy",
           "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "host": host, "root": root,
           "python3": py, "pt_shell": pt, "hspice": hs,
           "remote_sha256": remote["sha256"], "local_sha256": local_sha,
           "host_key_lines": len(host_key.strip().splitlines()),
           "host_key_sha256": fp,
           "known_hosts": host_key,
           "model_calls": 0}
    DEPLOY_RECORD.parent.mkdir(parents=True, exist_ok=True)
    DEPLOY_RECORD.write_text(json.dumps(rec, indent=2) + "\n")
    return {k: v for k, v in rec.items() if k != "known_hosts"}


# ---------------------------------------------------------------------------------------------
# per-episode provisioning (preflight and dry runs only)
# ---------------------------------------------------------------------------------------------

def _keygen(out_dir: Path, ep: str) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    key = out_dir / "key"
    for p in (key, out_dir / "key.pub"):
        if p.exists():
            p.unlink()
    r = subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q",
                        "-C", f"probe-{ep}", "-f", str(key)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not key.is_file():
        raise RemoteError(f"ssh-keygen failed for {ep}: {r.stderr}")
    os.chmod(key, 0o600)
    return (out_dir / "key.pub").read_text().strip()


def _install_episode_dir(host, root, deploy_rec, ep: str, manifest: dict) -> None:
    code = f"""
import json, os, time
root, ep = {root!r}, {ep!r}
d = os.path.join(root, "ep", ep)
os.makedirs(d, exist_ok=True)
os.chmod(d, 0o700)
with open(os.path.join(d, "manifest.json"), "w") as fh:
    json.dump({manifest!r}, fh)
with open(os.path.join(d, "provision.json"), "w") as fh:
    json.dump({{"episode": ep, "started": time.time()}}, fh)
report({{"episode": ep, "dir": d}})
"""
    _remote_py(host, root, code, py=deploy_rec["python3"])


def _remote_akb_call(host, root, deploy_rec, call: str) -> dict:
    """Run one authorized_keys_block call ON the remote, so the mutex, the fsync and the atomic
    rename all happen on the machine that owns the file."""
    code = f"""
import os
from eda_broker import authorized_keys_block as akb
ak = os.path.expanduser("~/.ssh/authorized_keys")
{call}
"""
    return _remote_py(host, root, code, py=deploy_rec["python3"])


def _round_trip_refusal(key: Path, known_hosts: Path, host: str) -> dict:
    """Send a deliberately malformed request and require REFUSED FRAMING.

    This proves two things at once and costs one round trip: the key authenticates, and it lands on
    the forced command rather than on a shell. A shell would have echoed nothing framed at all.
    """
    from eda_broker import broker_client as bc
    r = subprocess.run(bc.ssh_argv(key, known_hosts, host), input=b"not a framed request\n",
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    try:
        resp = bp.unframe(r.stdout)
    except bp.Refusal as e:
        return {"ok": False, "reason": f"no framed reply: {e.reason} {e.detail}",
                "ssh_rc": r.returncode,
                "stderr": r.stderr.decode("utf-8", "replace")[-300:]}
    return {"ok": resp.get("status") == bp.Status.REFUSED and resp.get("reason") == "FRAMING",
            "status": resp.get("status"), "reason": resp.get("reason"), "ssh_rc": r.returncode}


def provision(ep: str, instance, out_dir, host=DEFAULT_HOST, root=DEFAULT_ROOT,
              from_addr=None, caps_override=None) -> dict:
    """Single-episode provisioning, for the preflight and any dry run. Refuses while a batch is
    live: the formal arm must not rewrite authorized_keys per episode."""
    _refuse_if_batch_active()
    if not bp.valid_episode_id(ep):
        raise ValueError(f"illegal episode id: {ep!r}")
    d = _deploy_record()
    out_dir = Path(out_dir)
    pub = _keygen(out_dir, ep)
    manifest = build_manifest(Path(instance), caps_override=caps_override)
    _install_episode_dir(host, root, d, ep, manifest)

    line = authorized_keys_line(ep, pub, root=root, from_addr=from_addr)
    res = _remote_akb_call(host, root, d,
                           f"akb.add_entry(ak, {ep!r}, {line!r})\n"
                           f"report({{'entries': [e['episode'] for e in akb.list_entries(ak)]}})")
    if ep not in res["entries"]:
        raise RemoteError(f"the managed entry for {ep} is not present after add_entry")

    (out_dir / "known_hosts").write_text(d["known_hosts"])
    check = _round_trip_refusal(out_dir / "key", out_dir / "known_hosts", host)
    rec = {"episode": ep, "instance": str(instance), "out_dir": str(out_dir),
           "manifest_ops": manifest["ops"], "entries": res["entries"],
           "round_trip": check, "ok": bool(check["ok"]),
           "when": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (out_dir / "provision.json").write_text(json.dumps(rec, indent=2) + "\n")
    return rec


def teardown(ep: str, host=DEFAULT_HOST, root=DEFAULT_ROOT) -> dict:
    """Remove the managed entry and the episode directory, then VERIFY both are gone. Cleanup is
    verified rather than assumed: an unverified teardown is how a probe key outlives its episode."""
    _refuse_if_batch_active()
    if not bp.valid_episode_id(ep):
        raise ValueError(f"illegal episode id: {ep!r}")
    d = _deploy_record()
    res = _remote_akb_call(host, root, d, f"""
import shutil, os
akb.remove_entry(ak, {ep!r})
d = os.path.join({root!r}, "ep", {ep!r})
shutil.rmtree(d, ignore_errors=True)
report({{"entries": [e["episode"] for e in akb.list_entries(ak)],
         "dir_exists": os.path.isdir(d)}})
""")
    key_removed = ep not in res["entries"]
    dir_removed = not res["dir_exists"]
    return {"episode": ep, "key_removed": key_removed, "dir_removed": dir_removed,
            "ok": key_removed and dir_removed}


# ---------------------------------------------------------------------------------------------
# batch provisioning (the formal arm)
# ---------------------------------------------------------------------------------------------

def provision_batch(plan, out_root, host=DEFAULT_HOST, root=DEFAULT_ROOT,
                    from_addr=None, caps_override=None) -> dict:
    """Requirement E: install a whole arm's keys with ONE authorized_keys rewrite.

    Ordering is the point. Everything that can fail per episode -- validation, keygen, manifest
    construction, remote episode-directory creation -- happens BEFORE the single key install, so a
    failure leaves zero probe keys authorized rather than a partially-authorized arm, and the file
    is touched exactly once on the success path.
    """
    _refuse_if_batch_active()
    entries = validate_batch_plan(plan)
    d = _deploy_record()
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    before = _remote_akb_call(host, root, d,
                              "report({'user_region_sha256': __import__('hashlib')"
                              ".sha256(akb.user_region(ak).encode()).hexdigest(),"
                              " 'entries': [e['episode'] for e in akb.list_entries(ak)]})")
    if before["entries"]:
        raise RemoteError(f"the managed block is not empty before a batch: {before['entries']}")

    # 2. per-episode work, none of it touching authorized_keys.
    lines, fps = [], {}
    for e in entries:
        ep = e["episode"]
        pub = _keygen(out_root / ep, ep)
        manifest = build_manifest(e["instance_path"], caps_override=caps_override)
        _install_episode_dir(host, root, d, ep, manifest)
        (out_root / ep / "known_hosts").write_text(d["known_hosts"])
        lines.append((ep, authorized_keys_line(ep, pub, root=root, from_addr=from_addr)))
        fps[ep] = hashlib.sha256(pub.encode()).hexdigest()

    # 3. ONE remote call: one mutex, one atomic rewrite, N lines.
    installed = _remote_akb_call(host, root, d, f"""
import hashlib
n = akb.add_entries(ak, {lines!r})
report({{"n": n,
         "entries": [e["episode"] for e in akb.list_entries(ak)],
         "lines": [e["line"] for e in akb.list_entries(ak)],
         "user_region_sha256": hashlib.sha256(akb.user_region(ak).encode()).hexdigest()}})
""")

    # 4. verify WITHOUT rewriting: count, per-line forcing, and the untouched user region.
    want = [ep for ep, _ in lines]
    ok_count = sorted(installed["entries"]) == sorted(want)
    ok_region = installed["user_region_sha256"] == before["user_region_sha256"]
    ok_forcing = True
    for line in installed["lines"]:
        forced = re.findall(r'command="[^"]*/broker\.sh ([^"]*)"', line)
        if len(forced) != 1 or forced[0] not in want or f"probe-{forced[0]}" not in line:
            ok_forcing = False
            break

    # 5. one round trip on one key, not all N.
    first = want[0]
    check = _round_trip_refusal(out_root / first / "key", out_root / first / "known_hosts", host)

    ok = bool(ok_count and ok_region and ok_forcing and check["ok"])
    rec = {"generated_by": "scripts/eda_broker/broker_admin.py provision-batch",
           "batch_id": secrets.token_hex(8),
           "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "host": host, "root": root, "out_root": str(out_root),
           "n": len(want), "episodes": want, "key_sha256": fps,
           "user_region_sha256": before["user_region_sha256"],
           "verified": {"entry_set_matches": ok_count,
                        "user_region_unchanged": ok_region,
                        "every_line_forces_only_its_own_episode": ok_forcing,
                        "round_trip": check},
           "ok": ok, "model_calls": 0}
    if not ok:
        # Do not leave a live batch record for a batch that did not verify; remove the keys we
        # just installed so the failure state is "nothing authorized", not "48 keys and no record".
        _remote_akb_call(host, root, d,
                         f"akb.remove_entries(ak, {want!r})\nreport({{'rolled_back': True}})")
        raise RemoteError(f"batch provisioning did not verify, rolled back: {rec['verified']}")
    BATCH_RECORD.parent.mkdir(parents=True, exist_ok=True)
    BATCH_RECORD.write_text(json.dumps(rec, indent=2) + "\n")
    return rec


def teardown_batch(host=DEFAULT_HOST, root=DEFAULT_ROOT) -> dict:
    """Remove every key in the batch record with ONE rewrite, then verify.

    A failed teardown KEEPS the record, which keeps the per-episode lock-out in force and makes the
    residue impossible to ignore.
    """
    if not BATCH_RECORD.is_file():
        return {"n": 0, "ok": True, "note": "no live batch record"}
    rec = json.loads(BATCH_RECORD.read_text())
    eps = list(rec["episodes"])
    d = _deploy_record()
    res = _remote_akb_call(host, root, d, f"""
import hashlib, os, shutil
removed = akb.remove_entries(ak, {eps!r})
survivors = []
for ep in {eps!r}:
    p = os.path.join({root!r}, "ep", ep)
    shutil.rmtree(p, ignore_errors=True)
    if os.path.isdir(p):
        survivors.append(ep)
report({{"removed": removed,
         "entries": [e["episode"] for e in akb.list_entries(ak)],
         "dir_survivors": survivors,
         "user_region_sha256": hashlib.sha256(akb.user_region(ak).encode()).hexdigest()}})
""")
    keys_removed = not (set(eps) & set(res["entries"]))
    dirs_removed = not res["dir_survivors"]
    region_ok = res["user_region_sha256"] == rec["user_region_sha256"]
    out = {"n": len(eps), "keys_removed": keys_removed, "dirs_removed": dirs_removed,
           "user_region_unchanged": region_ok,
           "survivors": {"keys": sorted(set(eps) & set(res["entries"])),
                         "dirs": res["dir_survivors"]},
           "user_region_sha256": res["user_region_sha256"],
           "ok": bool(keys_removed and dirs_removed and region_ok)}
    if out["ok"]:
        BATCH_RECORD.unlink()
    return out


# ---------------------------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------------------------

def audit(host=DEFAULT_HOST, root=DEFAULT_ROOT, reap=False) -> dict:
    """List managed entries, <root>/ep/* and any quarantined lock directories.

    A quarantined lock is reported and never auto-removed: it is the record that somebody's lock was
    taken from them, and that is worth a human looking at it. Crash residue in the managed block IS
    reaped on request, because a probe key outliving its episode is a live capability with no owner.
    """
    d = _deploy_record()
    res = _remote_akb_call(host, root, d, f"""
import os, time, json, shutil
root = {root!r}
epdir = os.path.join(root, "ep")
dirs = sorted(os.listdir(epdir)) if os.path.isdir(epdir) else []
live, stale = [], []
for ep in dirs:
    marker = os.path.join(epdir, ep, "provision.json")
    started = 0
    try:
        with open(marker) as fh:
            started = json.load(fh).get("started", 0)
    except Exception:
        started = 0
    (live if (time.time() - started) < {STALE_PROVISION_SEC} else stale).append(ep)
entries = [e["episode"] for e in akb.list_entries(ak)]
quarantine = [str(p) for p in akb.list_quarantine(akb._lock_dir(ak))]
reaped = []
if {bool(reap)!r}:
    dead = [e for e in entries if e not in live]
    if dead:
        akb.remove_entries(ak, dead)
        reaped = dead
    for ep in stale:
        shutil.rmtree(os.path.join(epdir, ep), ignore_errors=True)
    entries = [e["episode"] for e in akb.list_entries(ak)]
    dirs = sorted(os.listdir(epdir)) if os.path.isdir(epdir) else []
report({{"entries": entries, "episode_dirs": dirs, "live": live, "stale": stale,
         "quarantine": quarantine, "reaped": reaped}})
""")
    res["batch_active"] = BATCH_RECORD.is_file()
    return res


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------

def _load_plan(spec: str) -> list:
    if spec == "formal":
        return formal_arm_plan()
    return json.loads(Path(spec).read_text())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Host-side broker administration. Zero model calls.")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--root", default=DEFAULT_ROOT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("deploy")
    p.add_argument("--allow-keyscan", action="store_true",
                   help="fall back to ssh-keyscan, which trusts whatever answers")

    p = sub.add_parser("provision")
    p.add_argument("--episode", required=True)
    p.add_argument("--instance", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--from-addr", default=None)

    p = sub.add_parser("provision-batch")
    p.add_argument("--plan", required=True, help="'formal' or a path to a plan JSON")
    p.add_argument("--out", required=True)
    p.add_argument("--from-addr", default=None)

    p = sub.add_parser("teardown")
    p.add_argument("--episode", required=True)

    sub.add_parser("teardown-batch")

    p = sub.add_parser("audit")
    p.add_argument("--reap", action="store_true")

    a = ap.parse_args(argv)
    if a.cmd == "deploy":
        out = deploy(a.host, a.root, allow_keyscan=a.allow_keyscan)
    elif a.cmd == "provision":
        out = provision(a.episode, Path(a.instance), Path(a.out), a.host, a.root, a.from_addr)
    elif a.cmd == "provision-batch":
        out = provision_batch(_load_plan(a.plan), Path(a.out), a.host, a.root, a.from_addr)
    elif a.cmd == "teardown":
        out = teardown(a.episode, a.host, a.root)
    elif a.cmd == "teardown-batch":
        out = teardown_batch(a.host, a.root)
    else:
        out = audit(a.host, a.root, reap=a.reap)
    printable = {k: v for k, v in out.items() if k != "known_hosts"}
    print(json.dumps(printable, indent=2))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
