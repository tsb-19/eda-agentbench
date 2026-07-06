# acc_stage handoff glossary (examples only -- NOT a complete schema)

This glossary gives EXAMPLES of the terminology used in the reports. It is deliberately INCOMPLETE: it does not list every valid value, and it does not give a value-to-axis table.

- **op_point**: an operating-point field. The design's operating points are named in the spec; a report's `op_point=` value is one of them.
- **mode**: a signoff-mode field.
- **PVT descriptor**: a string of the form `<process>_<voltage>_<temperature>`, e.g. `slow_1.0V_125C`. A PVT descriptor CHARACTERIZES an (operating point, signoff mode) pair but is NEVER a valid op_point or mode value itself.
- The consumed clock is the one that yields full intended-clock path coverage on the design.
- op_point and mode are DISJOINT typed axes: a value valid on one is invalid on the other.
