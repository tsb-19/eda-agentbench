.title Buffer Wrong Name - Missing Subckt
X1 in out attenuator
R1 out gnd 4.7k
V1 in gnd PULSE(0 5 1n 100p 100p 2n 4n)
.subckt buffer in out
Rseries in out 470
.ends buffer
.tran 10p 8n
.end
