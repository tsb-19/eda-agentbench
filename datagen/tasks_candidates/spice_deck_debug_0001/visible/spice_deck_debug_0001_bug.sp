.title CMOS Inverter - Missing Model
M1 out gate vdd vdd pmos_typo W=2u L=180n
M2 out gate gnd gnd nmos W=1u L=180n
.model nmos nmos (level=1 vto=0.7 kp=120u)
Vdd vdd gnd 1.8
Vin gate gnd PULSE(0 1.8 1n 100p 100p 1n 2n)
.tran 10p 4n
.end
