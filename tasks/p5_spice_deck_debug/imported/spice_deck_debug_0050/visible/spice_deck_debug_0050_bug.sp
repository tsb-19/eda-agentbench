.title Buffer Subcircuit - Wrong Pin Count
.subckt buf in out
Rseries in out 220
.ends buf
X1 in out gnd buf
R1 out gnd 1k
V1 in gnd PULSE(0 3.3 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
