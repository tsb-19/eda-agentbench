.title Source Follower - Missing Model
M1 vdd in out gnd nmos_bad W=2u L=90n
R1 out gnd 2k
Vdd vdd gnd 1.2
Vin in gnd PULSE(0 1.2 1n 100p 100p 2n 4n)
.tran 10p 16n
.end
