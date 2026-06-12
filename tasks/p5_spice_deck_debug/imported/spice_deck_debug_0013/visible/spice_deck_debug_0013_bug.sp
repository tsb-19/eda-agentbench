.title Common-Source Amplifier - Missing Model
M1 out in vdd vdd pmos_bad W=10u L=180n
R1 out gnd 10k
Vdd vdd gnd 1.8
Vin in gnd PULSE(0 1.8 1n 100p 100p 2n 4n)
.tran 10p 16n
.end
