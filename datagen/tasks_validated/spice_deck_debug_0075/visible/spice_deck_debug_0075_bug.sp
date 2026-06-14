.title CMOS Inverter - Bad Level 101
M1 out gate gnd gnd nmos W=1u L=250n
.model nmos nmos (level=99 vto=0.7 kp=120u)
Vdd gate 0 2.5
R1 out 0 1k
.tran 10p 10n
.end
