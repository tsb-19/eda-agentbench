# Task p16_eval_0003: SPICE measurement-handoff

Bind the characterization measurement request to (corner, load_condition, metric) in `meas_config.json` by joining the request to its authority sources. A machine-readable typed contract `typed_contract.json` declares roles, domains, authority sources.

The deck measures a PLAUSIBLE number for any tuple — simulation success and a plausible numeric output are NOT sufficient. Correctness is authority-joined (char_spec / mission_profile / application_note), not numeric; the stale measurement.log is a decoy.

Edit `meas_config.json`, run `bash run_public.sh` for the measured value, iterate, then finalize.
