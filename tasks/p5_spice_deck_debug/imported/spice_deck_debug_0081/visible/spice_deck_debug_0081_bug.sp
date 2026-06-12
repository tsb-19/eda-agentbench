.title Current Mirror - Bad Level
M1 ref ref gnd gnd nmos W=2u L=180n
M2 out ref gnd gnd nmos W=2u L=180n
R1 vdd ref 10k
Vdd vdd gnd 1.8
.model nmos nmos (level=99 vto=0.7 kp=120u)
.op
.end
