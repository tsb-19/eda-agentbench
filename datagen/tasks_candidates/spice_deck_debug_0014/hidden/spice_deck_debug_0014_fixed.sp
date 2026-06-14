.title CMOS Inverter Variant - Missing Model
M1 out gate vdd vdd pmos W=2u L=130n
M2 out gate gnd gnd nmos W=1u L=130n
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.5
Vin gate gnd PULSE(0 1.5 1n 100p 100p 1n 2n)
.tran 10p 4n
.end
