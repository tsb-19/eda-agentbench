* Rc Rise Delay - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 108.02879999999999n 216.05759999999998n

* RC low-pass filter
r1 in out 10912
c1 out 0 3.3e-12

* Analysis
.tran 50p 162.04319999999998n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
