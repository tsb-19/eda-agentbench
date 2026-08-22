#!/usr/bin/env python3
"""Manage exactly one delimited region of ~/.ssh/authorized_keys on the remote host.

Four properties, each of which a naive read-modify-write of the whole file would lose:

  * The operator's own keys are never rewritten. b04's authorized_keys holds real login keys; a
    partial write there locks the operator out of the host that runs every EDA tool.
  * Concurrent episodes coexist. The state is not "one probe key at a time" -- it is a set, and
    teardown of episode A may not remove episode B.
  * A crash cannot truncate the file. Mutations write a sibling temp, fsync it, then os.replace.
    A failed mutation leaves the previous file byte-identical and removes its own temp.
  * A whole batch is one mutation. The formal arm installs 48 lines in a single rewrite under a
    single lock, so authorized_keys is byte-static for the duration of the arm.

The mutex is a directory, not flock: $HOME on b04 is NFS, where flock(2) is emulated through the
lock manager and nfs(5) disclaims both cluster-coherent caching and lock survival across a
partition. mkdir(2) is atomic in its create step, which is what a mutex needs -- but it is not a
correct distributed lock, so the stale rule below never breaks a lock on age alone and never
deletes a lock whose owner it cannot prove dead.

This module is shipped to the remote host unchanged and is also unit-tested locally, because it
operates on a path rather than on "the" authorized_keys.
"""

from __future__ import annotations

import errno
import json
import os
import secrets
import socket
import time
from pathlib import Path

from . import broker_protocol as bp

BEGIN = "# BEGIN EDA-OPENCODE-PROBE"
END = "# END EDA-OPENCODE-PROBE"
TAG = "# probe-entry "          # followed by a JSON object: {"episode":..., "added":...}
QUARANTINE_PREFIX = ".quarantine."


class LockBusy(RuntimeError):
    pass


def _pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True            # exists, owned by someone else
    except (OverflowError, ValueError, TypeError, OSError):
        return False


class Mutex:
    """Directory mutex with a conservative stale rule.

    Breaking a lock requires BOTH that it is older than `stale_sec` AND that its owner is provably
    gone. "Provably" means: the owner recorded this host and its pid no longer exists. A lock owned
    by another host cannot be proved dead from here, so it is not deleted -- it is renamed aside
    into a quarantine directory and the lock is re-contested. The rename is atomic, so exactly one
    breaker wins, and an owner that was alive after all will find a foreign nonce at release time
    and free nothing.

    A broken lock is quarantined in BOTH branches rather than unlinked in the verified-death one.
    Deleting would be defensible there, but a preserved directory is a record that somebody's lock
    was taken from them, and `audit` reports it. Nothing about this design wants that to be silent.
    """

    def __init__(self, lock_dir, stale_sec: int = 900, wait_sec: float = 30.0,
                 poll_sec: float = 0.25):
        self.dir = Path(lock_dir)
        self.stale_sec = stale_sec
        self.wait_sec = wait_sec
        self.poll_sec = poll_sec
        self.nonce = None
        self.broken_by_other = False

    # -- acquisition ------------------------------------------------------------------------
    def __enter__(self):
        deadline = time.time() + self.wait_sec
        while True:
            parent = self.dir.parent
            if not parent.is_dir():
                os.makedirs(str(parent), exist_ok=True)
            try:
                os.mkdir(str(self.dir), 0o700)      # the atomic step, and the only one
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                if self._try_break():
                    continue
                if time.time() >= deadline:
                    raise LockBusy(f"{self.dir} held by another process")
                time.sleep(self.poll_sec)
                continue
            self.nonce = secrets.token_hex(16)
            self._write_owner()
            return self

    def _write_owner(self) -> None:
        now = time.time()
        (self.dir / "owner").write_text(json.dumps(
            {"owner_host": socket.gethostname(), "owner_pid": os.getpid(),
             "owner_nonce": self.nonce, "created_at": now, "heartbeat": now}))

    def touch(self) -> None:
        """Refresh the heartbeat. Staleness is measured from the heartbeat, so a legitimately long
        operation is never mistaken for a dead one."""
        rec = self._owner()
        if rec.get("owner_nonce") != self.nonce:
            self.broken_by_other = True
            return
        rec["heartbeat"] = time.time()
        (self.dir / "owner").write_text(json.dumps(rec))

    def _owner(self) -> dict:
        try:
            return json.loads((self.dir / "owner").read_text())
        except Exception:
            return {}

    def _try_break(self) -> bool:
        """Return True if the lock was cleared and acquisition should be retried."""
        rec = self._owner()
        last = rec.get("heartbeat") or rec.get("created_at")
        if last is None:
            try:                                    # no readable record: fall back to the mtime
                last = (self.dir / "owner").stat().st_mtime
            except OSError:
                try:
                    last = self.dir.stat().st_mtime
                except OSError:
                    return False                    # gone already; the retry will find out
        if (time.time() - float(last)) <= self.stale_sec:
            return False        # rule 1: age alone is never enough to break a lock, and youth is
                                # always enough to be left alone -- even for a dead owner.
        host, pid = rec.get("owner_host"), rec.get("owner_pid")
        if host == socket.gethostname() and pid is not None and _pid_alive(pid):
            return False                            # slow, not dead
        return self._quarantine()                   # verified death, or unverifiable: move aside

    def _quarantine(self) -> bool:
        dest = self.dir.parent / (self.dir.name + QUARANTINE_PREFIX
                                  + f"{int(time.time())}." + secrets.token_hex(4))
        try:
            os.rename(str(self.dir), str(dest))
        except OSError:
            pass                # someone else won the race; either way the lock is no longer here
        return True

    # -- release ----------------------------------------------------------------------------
    def __exit__(self, *exc):
        self.release()
        return False

    def release(self) -> None:
        if self.nonce is None:
            return                      # never acquired: nothing of ours to free
        if self._owner().get("owner_nonce") != self.nonce:
            # Our lock was broken while we held it. The directory belongs to someone else now and
            # removing it would free THEIR lock.
            self.broken_by_other = True
            return
        try:
            (self.dir / "owner").unlink()
        except OSError:
            pass
        try:
            self.dir.rmdir()
        except OSError:
            pass


def list_quarantine(lock_dir) -> list:
    """Quarantined locks left behind by a break. Reported by `audit`: each one is a record that
    somebody's lock was taken from them, which is worth seeing rather than silently cleaning."""
    lock_dir = Path(lock_dir)
    return sorted(p for p in lock_dir.parent.glob(lock_dir.name + QUARANTINE_PREFIX + "*")
                  if p.is_dir())


def _lock_dir(path) -> Path:
    return Path(path).parent / ".eda-probe-akb.lock.d"


def _read(path) -> bytes:
    """Read the file as BYTES, never as text.

    Measured on b04: `~/.ssh/authorized_keys` uses CRLF. `Path.read_text()` applies universal-newline
    translation, so a read-then-write cycle through text mode silently rewrites every line ending in
    the file -- including the operator's own lines, which is precisely the "nothing outside the
    managed block is ever rewritten" guarantee. Line endings are content here, so all I/O in this
    module is byte-exact and the only bytes this module ever originates are its own block's.
    """
    p = Path(path)
    return p.read_bytes() if p.is_file() else b""


def _lines(data: bytes) -> list:
    """Split on b"\\n" keeping the terminator, so CR (and a missing final newline) survive."""
    out, start = [], 0
    while True:
        i = data.find(b"\n", start)
        if i < 0:
            if start < len(data):
                out.append(data[start:])
            return out
        out.append(data[start:i + 1])
        start = i + 1


def _split(data: bytes):
    """Return (before, managed, after) as byte strings. No block yields (all, b"", b"")."""
    lines = _lines(data)
    b = e = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s == BEGIN.encode() and b is None:
            b = i
        elif s == END.encode():
            e = i
    if b is None or e is None or e < b:
        return data, b"", b""
    return b"".join(lines[:b]), b"".join(lines[b + 1:e]), b"".join(lines[e + 1:])


def _atomic_write(path, data: bytes) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(str(tmp), str(path))
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if tmp.exists():
            tmp.unlink()


def _render(before: bytes, managed: bytes, after: bytes) -> bytes:
    body = before
    if body and not body.endswith(b"\n"):
        body += b"\n"
    if managed:
        body += BEGIN.encode() + b"\n" + managed + END.encode() + b"\n"
    return body + after


def list_entries(path) -> list:
    _, managed, _ = _split(_read(path))
    out, pending = [], None
    for raw in _lines(managed):
        line = raw.decode("utf-8", "surrogateescape")
        if line.startswith(TAG):
            try:
                pending = json.loads(line[len(TAG):])
            except Exception:
                pending = None
        elif line.strip() and pending:
            out.append({"episode": pending.get("episode"), "added": pending.get("added"),
                        "line": line.rstrip("\r\n")})
            pending = None
    return out


def read_block(path) -> list:
    return [ln.decode("utf-8", "surrogateescape") for ln in _lines(_split(_read(path))[1])]


def user_region(path) -> bytes:
    """Everything OUTSIDE the managed block, as raw BYTES.

    This is the quantity the operator cares about and the one the preflight hashes three times:
    before the batch, while all 48 keys are installed, and after teardown. It returns bytes rather
    than text on purpose. Returning text would normalise CRLF on both sides of the comparison, so the
    check meant to prove "nothing outside the block changed" would be blind to a whole-file line-ending
    rewrite -- a verifier that cannot see the mutation it exists to catch. That defect was real: it was
    found by the dry run against a copy of b04's actual file, which is CRLF.
    """
    before, _, after = _split(_read(path))
    return before + after


def _rewrite(path, entries: list) -> None:
    before, _, after = _split(_read(path))
    managed = b""
    for e in entries:
        managed += (TAG + json.dumps({"episode": e["episode"], "added": e["added"]}) + "\n").encode()
        managed += e["line"].rstrip("\r\n").encode() + b"\n"
    _atomic_write(Path(path), _render(before, managed, after))


def _check(episode_id: str, line: str) -> None:
    if not bp.valid_episode_id(episode_id):
        raise ValueError(f"illegal episode id: {episode_id!r}")
    if "\n" in line or "\r" in line:
        raise ValueError("an authorized_keys entry may not span lines")


def add_entries(path, entries) -> int:
    """Install several probe keys in ONE rewrite under ONE lock (requirement E).

    Every id and every line is validated before the mutex is taken, so a bad batch cannot leave a
    partially-installed block behind. Duplicate episode ids are refused rather than deduplicated:
    two keys for one episode would survive a teardown keyed on the episode, and the survivor is a
    live capability with no owner.
    """
    entries = [(str(ep), str(line)) for ep, line in entries]
    for ep, line in entries:
        _check(ep, line)
    ids = [ep for ep, _ in entries]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate episode ids in one batch: {dupes}")
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    with Mutex(_lock_dir(path)):
        keep = [e for e in list_entries(path) if e["episode"] not in set(ids)]
        keep += [{"episode": ep, "added": now, "line": line} for ep, line in entries]
        _rewrite(path, keep)
    return len(entries)


def remove_entries(path, episode_ids) -> list:
    """Remove several probe keys in ONE rewrite under ONE lock. Returns those actually present."""
    wanted = set()
    for ep in episode_ids:
        if not bp.valid_episode_id(ep):
            raise ValueError(f"illegal episode id: {ep!r}")
        wanted.add(ep)
    with Mutex(_lock_dir(path)):
        entries = list_entries(path)
        present = [e["episode"] for e in entries if e["episode"] in wanted]
        if present:
            _rewrite(path, [e for e in entries if e["episode"] not in wanted])
        return present


def add_entry(path, episode_id: str, line: str) -> None:
    """One entry, one rewrite. Kept for the preflight and any single-episode dry run; the formal
    arm uses add_entries so that authorized_keys is not rewritten 48 times."""
    _check(episode_id, line)
    with Mutex(_lock_dir(path)):
        entries = [e for e in list_entries(path) if e["episode"] != episode_id]
        entries.append({"episode": episode_id, "added": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "line": line})
        _rewrite(path, entries)


def remove_entry(path, episode_id: str) -> bool:
    if not bp.valid_episode_id(episode_id):
        raise ValueError(f"illegal episode id: {episode_id!r}")
    with Mutex(_lock_dir(path)):
        entries = list_entries(path)
        keep = [e for e in entries if e["episode"] != episode_id]
        if len(keep) == len(entries):
            return False
        _rewrite(path, keep)
        return True


def reap(path, live) -> list:
    """Remove managed entries for episodes that are no longer live. Crash residue is a custody
    problem, not only a race: a probe key outliving its episode is a capability nobody is holding."""
    with Mutex(_lock_dir(path)):
        entries = list_entries(path)
        dead = [e["episode"] for e in entries if e["episode"] not in live]
        if dead:
            _rewrite(path, [e for e in entries if e["episode"] in live])
        return dead
