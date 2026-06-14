.title Inverter Chain - Missing Subckt
.subckt inv in out vdd gnd
M1 out in vdd vdd pmos W=3u L=90n
M2 out in gnd gnd nmos W=1.5u L=90n
.ends inv
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
X1 a b vdd gnd inv
X2 b c vdd gnd inv
Vdd vdd gnd 1.2
Va a gnd PULSE(0 1.2 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
