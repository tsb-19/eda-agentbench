.title Buffer Wrong Name - Missing Subckt
.subckt attenuator in out
Rseries in out 470
.ends attenuator
X1 in out attenuator
R1 out gnd 4.7k
V1 in gnd PULSE(0 5 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
