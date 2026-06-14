.title CMOS Inverter - Missing Model
M1 out gate vdd vdd pmos W=1u L=250n
M2 out gate gnd gnd nmos W=500n L=250n
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 2.5
Vin gate gnd PULSE(0 2.5 1n 100p 100p 1n 2n)
.tran 10p 4n
.end
