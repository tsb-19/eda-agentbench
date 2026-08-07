# Disclosure bundle (BundleS: C1+C2+C4+C7, non-answer-bearing)

## C1 canonical labels + disjoint-axis declaration
Typed roles: intent_class, target_partition, check_mode. They are DISJOINT typed axes (a value on one axis does not satisfy another).

## C2 value-domain definitions
- intent_class in ['functional_close', 'cdc_isolate', 'reset_exempt', 'scan_override']
- target_partition in ['cdc', 'reset', 'scan', 'core']
- check_mode in ['setup', 'hold', 'both']

## C4 glossary + references
- intent_class: see intent.md
- target_partition: see cdc_report|reset_report|scan_section
- check_mode: the coverage matrix requires_exception cell
Authority precedence: INT(primary), CDC/RST/SCN(primary), COV(derived), PRIOR(none/decoy)

## C7 procedural contract
Bind each role from its attesting primary/derived authority; tool signs green regardless, so correctness is provenance-attested.
