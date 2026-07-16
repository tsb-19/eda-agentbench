# Phase-4W axis-domain + lexical audit (gate #3)

Legal public scenario values: `['slow', 'typ', 'fast']`
Legal public corner values: `['func', 'test', 'lowpower']`
Held-out golden (0011 & 0012): scenario=`typ`, corner=`test`
Held-out mutant swap: `['test', 'slow']` (test in scenario slot [corner value -> type error], slow in corner slot [scenario value -> type error])

## wrong-axis candidate `test/slow`
- test is a corner member (`True`); in the scenario slot it is a type error (`True`).
- slow is a scenario member (`True`); in the corner slot it is a type error (`True`).
- Syntactically a valid string; PT-executable (signoff green on v2/clk_main; body corner-independent); rejected by typed-binding/evidence.

## 0011 disclosure audit
- filename discloses typ/test: `False`
- ships glossary: `False` | ships public_check_summary: `False` | C6 assertion: `False`
- no NEW disclosure channel vs 0009: `True`

## public token occurrence counts (visible files)
| token | 0011 | 0012 |
|---|---|---|
| `typ` | 7 | 8 |
| `test` | 9 | 10 |
| `slow` | 7 | 7 |
| `func` | 4 | 4 |
