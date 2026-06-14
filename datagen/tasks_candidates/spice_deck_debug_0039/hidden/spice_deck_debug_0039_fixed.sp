.title Diode Circuit - Duplicate Element
D1 anode cathode Dreal
D2 anode2 cathode2 Dreal
R1 cathode 0 1k
R2 cathode2 0 1k
.model Dreal D(Is=1e-14 N=1)
V1 anode 0 SIN(0 5 60)
V2 anode2 0 SIN(0 5 60)
.tran 10p 33m
.end
