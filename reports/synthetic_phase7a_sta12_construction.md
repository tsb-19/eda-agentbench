# Phase-7A Study A — 12-instance STA construction/gate report

**All pass hard gate + audits:** True

**Distinct signatures:** {'truth': True, 'authority': True, 'decoy': True, 'wrong_green': True}

| instance | golden | wrong | axis | hard_gate | output_channel | info_equiv | wrong_green_unattested |
|---|---|---|---|---|---|---|---|
| p15_eval_0004 | ['functional_close', 'core', 'setup'] | ['functional_close', 'cdc', 'setup'] | partition | True | True | True | True |
| p15_eval_0005 | ['functional_close', 'cdc', 'setup'] | ['reset_exempt', 'cdc', 'both'] | intent+view | True | True | True | True |
| p15_eval_0006 | ['functional_close', 'reset', 'setup'] | ['scan_override', 'reset', 'both'] | intent+view | True | True | True | True |
| p15_eval_0007 | ['cdc_isolate', 'core', 'setup'] | ['cdc_isolate', 'cdc', 'setup'] | partition | True | True | True | True |
| p15_eval_0008 | ['cdc_isolate', 'cdc', 'setup'] | ['scan_override', 'cdc', 'both'] | intent+view | True | True | True | True |
| p15_eval_0009 | ['cdc_isolate', 'scan', 'setup'] | ['reset_exempt', 'scan', 'both'] | intent+view | True | True | True | True |
| p15_eval_0010 | ['reset_exempt', 'cdc', 'both'] | ['reset_exempt', 'reset', 'both'] | partition | True | True | True | True |
| p15_eval_0011 | ['reset_exempt', 'reset', 'both'] | ['functional_close', 'reset', 'setup'] | intent+view | True | True | True | True |
| p15_eval_0012 | ['reset_exempt', 'scan', 'both'] | ['cdc_isolate', 'scan', 'setup'] | intent+view | True | True | True | True |
| p15_eval_0013 | ['scan_override', 'core', 'both'] | ['scan_override', 'scan', 'both'] | partition | True | True | True | True |
| p15_eval_0014 | ['scan_override', 'reset', 'both'] | ['cdc_isolate', 'reset', 'setup'] | intent+view | True | True | True | True |
| p15_eval_0015 | ['scan_override', 'scan', 'both'] | ['functional_close', 'scan', 'setup'] | intent+view | True | True | True | True |
