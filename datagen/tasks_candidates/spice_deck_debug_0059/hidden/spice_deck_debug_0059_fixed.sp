.title MOSFET with Include - Missing Include
.model nmos nmos (level=1 vto=0.7 kp=120u)
M1 out gate gnd gnd nmos W=2u L=180n
R1 out 0 1k
Vdd gate 0 1.8
.tran 10p 10n
.end
