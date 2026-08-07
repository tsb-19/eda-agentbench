# Task p15_eval_0004: STA timing-exception signoff handoff

You own static-timing signoff. Reconcile the timing-exception intent from the authority chain and bind it in `exception_config.json` as (intent_class, target_partition, check_mode). The reports use an overloaded field `timing_tag`; resolve the typed roles (intent / partition / view) from the authority intersection.

The design is marginally timed and healthy: `report_timing` is GREEN regardless of which exception you bind — so a clean signoff is necessary but NOT sufficient. Correctness is provenance-attested: the binding must match the primary authorities (intent.md / cdc_report / reset_report / scan_section), not the stale prior signoff.log.

Edit `exception_config.json`, run `bash run_public.sh` for feedback, iterate, then finalize.
