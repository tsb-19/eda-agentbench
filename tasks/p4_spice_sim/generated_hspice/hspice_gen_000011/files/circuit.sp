* RC low-pass filter - HSPICE netlist
.global 0
.param rp=219381

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 65814.29999999999n 131628.59999999998n

* RC low-pass filter
r1 in out 219381
c1 out 0 1e-10

* Analysis
.tran 50p 98721.44999999998n

* Measure rise and fall delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
