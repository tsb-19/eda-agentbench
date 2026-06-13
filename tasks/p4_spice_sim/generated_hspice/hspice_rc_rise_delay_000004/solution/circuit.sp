* Rc Rise Delay - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 19128.780000000002n 38257.560000000005n

* RC low-pass filter
r1 in out 22000
c1 out 0 2.2e-11

* Analysis
.tran 50p 28693.170000000006n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
