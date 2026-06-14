.title NAND Gate - Duplicate Element
M1 out a vdd vdd pmos W=2u L=180n
M2 out b vdd vdd pmos W=2u L=180n
M3 out a mid mid nmos W=1u L=180n
M4 mid b gnd gnd nmos W=1u L=180n
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.8
Va a gnd PULSE(0 1.8 0 100p 100p 1n 2n)
Vb b gnd PULSE(0 1.8 0 100p 100p 2n 4n)
.tran 10p 8n
.end
