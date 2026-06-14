.title CMOS Inverter - Missing Include
.include cmos_models.lib
M1 out gate vdd vdd pmos W=3u L=130n
M2 out gate gnd gnd nmos W=1.5u L=130n
Vdd vdd gnd 1.5
Vin gate gnd PULSE(0 1.5 1n 100p 100p 1n 2n)
.tran 10p 4n
.end
