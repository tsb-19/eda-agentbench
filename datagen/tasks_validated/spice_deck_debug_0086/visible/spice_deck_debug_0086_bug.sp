.title MOSFET Load - Bad Level
M1 out gate gnd gnd nmos W=3u L=130n
.model nmos nmos (level=99 vto=0.7 kp=120u)
Vdd gate 0 1.5
R1 out 0 10k
.tran 10p 10n
.end
