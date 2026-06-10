* RC Delay Circuit - BUGGY: R too large, delay out of spec
Vin in 0 PULSE 0 1.8 0 0.1n 0.1n 50n 100n
R1 in out 10k
C1 out 0 10p
.tran 0.1n 80n
.measure TRAN tdrise TRIG v(in) VAL=0.9 RISE=1 TARG v(out) VAL=0.9 RISE=1
.end
