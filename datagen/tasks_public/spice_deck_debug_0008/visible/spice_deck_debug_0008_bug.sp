.title Diode Rectifier - Bug 8
* BUG: Diode D1 references model "Drect" but .model defines "Drectifier"
D1 anode cathode Drect
R1 cathode 0 1k
V1 anode 0 SIN(0 5 60)
.model Drectifier D(Is=1e-14 N=1)
.tran 10p 33m
.end
