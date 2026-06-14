.title Filter with Subckt - Missing Subckt
.subckt terminator in out
Rt in out 100
.ends terminator
X1 in mid terminator
R1 mid out 1k
C1 out gnd 1p
V1 in gnd PULSE(0 1.8 1n 100p 100p 2n 4n)
.tran 10p 10n
.end
