# acc_stage handoff glossary (examples only -- NOT a complete schema)

This glossary gives EXAMPLES of the terminology used in the reports. It is deliberately INCOMPLETE: it does not list every valid value, and it does not give a value-to-axis table.

- **scenario**: a setup scenario field. The design's scenarios are named in the spec; a report's `scenario=` value is one of them.
- **corner**: a signoff corner field.
- **PVT descriptor**: a string of the form `<process>_<voltage>_<temperature>`, e.g. `slow_1.0V_125C`. A PVT descriptor CHARACTERIZES a (scenario, corner) pair but is NEVER a valid scenario or corner value itself.
- The consumed clock is the one that yields full intended-clock path coverage on the design.
- scenario and corner are DISJOINT typed axes: a value valid on one is invalid on the other.
