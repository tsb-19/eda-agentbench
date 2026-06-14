.title Inverter Chain Wrong Name - Missing Subckt
X1 a b vdd gnd inverter
X2 b c vdd gnd inverter
.subckt buf_stage in out vdd gnd
M1 out in vdd vdd pmos W=2u L=180n
M2 out in gnd gnd nmos W=1u L=180n
.ends buf_stage
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.8
Va a gnd PULSE(0 1.8 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
