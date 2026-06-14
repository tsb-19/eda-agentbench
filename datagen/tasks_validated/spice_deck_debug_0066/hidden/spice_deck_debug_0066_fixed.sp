.title Diode Rectifier - Missing Include
.model Dreal D(Is=1e-14 N=1)
D1 anode cathode Dreal
R1 cathode 0 1k
V1 anode 0 SIN(0 5 60)
.tran 10p 33m
.end
