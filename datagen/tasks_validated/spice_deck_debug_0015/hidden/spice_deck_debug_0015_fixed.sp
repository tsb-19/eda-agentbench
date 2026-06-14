.title CMOS Inverter Variant - Missing Model
M1 out gate vdd vdd pmos W=4u L=90n
M2 out gate gnd gnd nmos W=2u L=90n
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.0
Vin gate gnd PULSE(0 1.0 1n 100p 100p 1n 2n)
.tran 10p 4n
.end
