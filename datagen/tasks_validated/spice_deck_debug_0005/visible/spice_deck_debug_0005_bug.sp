.title NAND Gate - Missing Model
M1 out a vdd vdd pmos_bad W=3u L=130n
M2 out b vdd vdd pmos_bad W=3u L=130n
M3 out a mid mid nmos W=1.5u L=130n
M4 mid b gnd gnd nmos W=1.5u L=130n
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.5
Va a gnd PULSE(0 1.5 0 100p 100p 1n 2n)
Vb b gnd PULSE(0 1.5 0 100p 100p 2n 4n)
.tran 10p 8n
.end
