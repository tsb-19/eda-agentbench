* RC low-pass filter - HSPICE netlist
.global 0
.param rp=5600

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 4312.305n 8624.61n

* RC low-pass filter
r1 in out 5600
c1 out 0 1.5e-11

* Analysis
.tran 50p 6468.4575n

* Measure rise and fall delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
