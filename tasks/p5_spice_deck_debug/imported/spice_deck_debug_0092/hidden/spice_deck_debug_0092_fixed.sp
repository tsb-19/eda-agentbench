.title MOSFET Circuit - Invalid Directive
M1 out gate gnd gnd nmos W=2u L=180n
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd gate 0 1.8
R1 out 0 1k
.tran 10p 10n
.end
