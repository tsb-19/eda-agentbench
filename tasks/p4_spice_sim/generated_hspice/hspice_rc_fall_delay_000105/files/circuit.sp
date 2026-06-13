* Rc Fall Delay - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 90119.70000000001n 180239.40000000002n

* RC low-pass filter
r1 in out 200266
c1 out 0 1.5e-10

* Analysis
.tran 50p 135179.55000000002n

* Measure delays
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1

.end
