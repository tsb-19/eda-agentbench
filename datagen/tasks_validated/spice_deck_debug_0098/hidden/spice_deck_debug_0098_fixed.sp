.title Common-Source Amplifier - Invalid Directive
M1 out in vdd vdd pmos W=10u L=180n
R1 out gnd 10k
Vdd vdd gnd 1.8
Vin in gnd PULSE(0 1.8 1n 100p 100p 2n 4n)
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.tran 10p 16n
.end
