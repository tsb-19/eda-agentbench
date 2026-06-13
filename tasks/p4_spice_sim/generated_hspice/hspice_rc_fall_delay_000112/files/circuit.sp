* Rc Fall Delay - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 53222.37599999999n 106444.75199999998n

* RC low-pass filter
r1 in out 260894
c1 out 0 6.8e-11

* Analysis
.tran 50p 79833.56399999998n

* Measure delays
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1

.end
