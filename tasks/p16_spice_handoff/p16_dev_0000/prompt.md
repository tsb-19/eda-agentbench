# Task p16_dev_0000: SPICE measurement-handoff

Bind the characterization measurement request to (corner, load_condition, metric) in `meas_config.json` by joining the request to its authority sources. Canonical typed roles `corner` / `load_condition` / `metric`; see disclosure_bundles.md.

The deck measures a PLAUSIBLE number for any tuple — simulation success and a plausible numeric output are NOT sufficient. Correctness is authority-joined (char_spec / mission_profile / application_note), not numeric; the stale measurement.log is a decoy.

Edit `meas_config.json`, run `bash run_public.sh` for the measured value, iterate, then finalize.
