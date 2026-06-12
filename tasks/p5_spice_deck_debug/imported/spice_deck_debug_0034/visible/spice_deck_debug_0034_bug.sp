.title CMOS Latch - Duplicate Element
M1 out in vdd vdd pmos W=4u L=90n
M2 out in gnd gnd nmos W=2u L=90n
M3 in out vdd vdd pmos W=4u L=90n
M1 in out gnd gnd nmos W=2u L=90n
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd 0 1.2
Vin in 0 PULSE(0 1.2 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
