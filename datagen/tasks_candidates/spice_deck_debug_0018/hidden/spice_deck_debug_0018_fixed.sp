.title Buffer Circuit - Missing Subckt
.subckt buf in out
Rseries in out 470
.ends buf
X1 in out buf
R1 out gnd 4.7k
V1 in gnd PULSE(0 5 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
