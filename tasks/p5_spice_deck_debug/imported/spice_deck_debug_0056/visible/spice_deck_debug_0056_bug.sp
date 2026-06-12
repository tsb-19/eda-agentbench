.title NOR Gate Subcircuit - Wrong Pin Count
.subckt nor2 a b out vdd gnd
M1 mid a vdd vdd pmos W=2u L=130n
M2 out b mid mid pmos W=2u L=130n
M3 out a gnd gnd nmos W=1u L=130n
M4 out b gnd gnd nmos W=1u L=130n
.ends nor2
X1 a b out vdd nor2
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.5
Va a gnd PULSE(0 1.5 0 100p 100p 1n 2n)
Vb b gnd PULSE(0 1.5 0 100p 100p 2n 4n)
.tran 10p 8n
.end
