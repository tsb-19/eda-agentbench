* Rc Rise Delay - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 8774.898000000001n 17549.796000000002n

* RC low-pass filter
r1 in out 132953
c1 out 0 2.2e-11

* Analysis
.tran 50p 13162.347000000002n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
