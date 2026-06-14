.title Inverter Subcircuit - Wrong Pin Count
.subckt inv in out vdd gnd
M1 out in vdd vdd pmos W=3u L=130n
M2 out in gnd gnd nmos W=1.5u L=130n
.ends inv
X1 in out vdd gnd inv
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.5
Vin in gnd PULSE(0 1.5 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
