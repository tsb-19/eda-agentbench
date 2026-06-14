.title Diode Rectifier - Missing Model
D1 anode cathode Drect
R1 cathode 0 10k
V1 anode 0 SIN(0 3.3 1k)
.model Drectifier D(Is=1e-14 N=1)
.tran 10p 2m
.end
