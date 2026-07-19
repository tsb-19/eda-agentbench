#!/usr/bin/env python3
"""Phase-4X transport-validity check — implements the FROZEN valid-episode rule verbatim
(reports/evidence/p14_phase4x_dev/frozen_config.json, committed 4977c48):

  "An episode with transport_valid=false (any transport-failure marker / infra abort / runner
   timeout attributable to transport) does NOT count."

INVALID iff: any transport-failure marker present, OR the episode error is a transport marker
(infra abort), OR the workspace is not gradeable, OR a runner timeout co-occurs with transport
evidence (markers/infra abort). A hard task-wall timeout with ZERO transport events and a gradeable
workspace is a task-level termination (capability/pace), NOT a transport failure -> VALID
(termination mode reported separately).

History: the initial runs/p4x_validity.py helper implemented `timed_out -> INVALID` unconditionally
— STRICTER than the frozen rule — causing block1:Base over-collection (see deviation_log.json).
This committed checker replaces it for all remaining slots.

Usage: phase4x_validity.py <results_root> <task_id>   (prints VALID/INVALID, exits 0/1)
"""
import json, sys
from pathlib import Path

MARKERS = ("socket_timeout", "hard_request_deadline", "incomplete_stream", "malformed_stream",
           "worker_crash", "malformed_worker_result", "retryable_http", "connection_reset")

root, task = Path(sys.argv[1]), sys.argv[2]
base = root / "DeepSeek-V4-Pro/p14_workflow_handoff"
try:
    res = json.loads((base / f"{task}.json").read_text())
    lg = json.loads((base / f"{task}.agentlog.json").read_text())
except Exception as e:
    print(f"INVALID missing_results {type(e).__name__}"); sys.exit(1)
log_text = json.dumps(lg)
counts = {m: log_text.count(m) for m in MARKERS}
events = sum(counts.values())
err = lg.get("error") or res.get("error")
infra_aborted = bool(err) and any(m in str(err) for m in MARKERS)
timed_out = bool(res.get("agent", {}).get("timed_out", False))
gradeable = res.get("total_score") is not None
timeout_transport_attributable = timed_out and (events > 0 or infra_aborted)
invalid = (events > 0) or infra_aborted or (not gradeable) or timeout_transport_attributable
if not invalid:
    note = " (task_wall_hard_kill: timed_out with 0 transport events -> task-level termination)" if timed_out else ""
    print(f"VALID{note}"); sys.exit(0)
print(f"INVALID events={events} infra_aborted={infra_aborted} timed_out={timed_out} gradeable={gradeable} "
      f"nonzero={{ {', '.join(f'{k}:{v}' for k, v in counts.items() if v)} }}")
sys.exit(1)
