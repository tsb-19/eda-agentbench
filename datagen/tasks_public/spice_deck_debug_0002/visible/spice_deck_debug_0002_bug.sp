.title Buffer Circuit - Bug 2
* BUG: X1 references subckt "buf" which is not defined
X1 in out buf
R1 out gnd 1k
V1 in gnd PULSE(0 1.8 1n 100p 100p 2n 4n)
.tran 10p 8n
.end
