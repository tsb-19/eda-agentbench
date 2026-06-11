* RC low-pass filter - HSPICE netlist
.global 0
.param rp=68315

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 20494.500000000004n 40989.00000000001n

* RC low-pass filter
r1 in out 68315
c1 out 0 1e-10

* Analysis
.tran 50p 30741.750000000007n

* Measure rise and fall delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
