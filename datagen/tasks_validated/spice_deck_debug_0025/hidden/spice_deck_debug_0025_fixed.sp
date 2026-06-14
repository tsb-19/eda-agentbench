.title Filter with Subckt - Missing Subckt
.subckt terminator in out
Rt in out 220
.ends terminator
X1 in mid terminator
R1 mid out 4.7k
C1 out gnd 100f
V1 in gnd PULSE(0 3.3 1n 100p 100p 2n 4n)
.tran 10p 10n
.end
