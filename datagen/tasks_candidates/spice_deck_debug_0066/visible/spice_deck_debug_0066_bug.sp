.title Diode Rectifier - Missing Include
.include diode_models.lib
D1 anode cathode Dreal
R1 cathode 0 1k
V1 anode 0 SIN(0 5 60)
.tran 10p 33m
.end
