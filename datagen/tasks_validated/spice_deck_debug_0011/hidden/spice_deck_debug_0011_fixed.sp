.title Source Follower - Missing Model
M1 vdd in out gnd nmos W=2u L=90n
R1 out gnd 2k
Vdd vdd gnd 1.2
Vin in gnd PULSE(0 1.2 1n 100p 100p 2n 4n)
.model nmos nmos (level=1 vto=0.7 kp=120u)
.tran 10p 16n
.end
