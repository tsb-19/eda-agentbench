* RC low-pass filter - HSPICE netlist
.global 0
.param rp=1.2k

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 100n 200n

* RC low-pass filter
r1 in out 1.2k
c1 out 0 10p

* Analysis
.tran 50p 150n

* Measure rise delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1

.end
