.title RC Filter - Missing Include
.include passive_models.lib
R1 in out 1k
C1 out gnd 1p
V1 in gnd PULSE(0 1.8 1n 100p 100p 2n 4n)
.tran 10p 10n
.end
