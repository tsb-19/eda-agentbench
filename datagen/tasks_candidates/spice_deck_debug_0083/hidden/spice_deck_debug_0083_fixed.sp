.title CMOS Latch - Bad Level
M1 out in gnd gnd nmos W=2u L=180n
M2 in out gnd gnd nmos W=2u L=180n
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd 0 1.8
Vin in 0 PULSE(0 1.8 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
