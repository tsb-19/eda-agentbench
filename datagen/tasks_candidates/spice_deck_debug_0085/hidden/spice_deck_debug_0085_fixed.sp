.title Inverter - Bad PMOS Level
M1 out gate vdd vdd pmos W=2u L=180n
.model pmos pmos (level=1 vto=-0.7 kp=50u)
Vdd vdd gnd 1.8
Vin gate gnd PULSE(0 1.8 1n 100p 100p 1n 2n)
.tran 10p 4n
.end
