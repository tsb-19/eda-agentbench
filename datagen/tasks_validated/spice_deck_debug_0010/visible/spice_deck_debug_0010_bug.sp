.title Source Follower - Missing Model
M1 vdd in out gnd nmos_bad W=4u L=180n
R1 out gnd 1k
Vdd vdd gnd 1.8
Vin in gnd PULSE(0 1.8 1n 100p 100p 2n 4n)
.tran 10p 16n
.end
