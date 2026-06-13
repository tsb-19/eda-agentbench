* Rc Fall Delay - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 252.17399999999998n 504.34799999999996n

* RC low-pass filter
r1 in out 84058
c1 out 0 1e-12

* Analysis
.tran 50p 378.26099999999997n

* Measure delays
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1

.end
