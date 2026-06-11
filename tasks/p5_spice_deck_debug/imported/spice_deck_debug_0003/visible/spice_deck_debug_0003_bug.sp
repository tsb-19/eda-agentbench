.title Inverter Subcircuit - Bug 3
.subckt inv in out vdd gnd
M1 out in vdd vdd pmos W=2u L=180n
M2 out in gnd gnd nmos W=1u L=180n
.ends inv
* BUG: X1 passes only 3 pins but subckt expects 4
X1 in out vdd inv
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.8
Vin in gnd PULSE(0 1.8 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
