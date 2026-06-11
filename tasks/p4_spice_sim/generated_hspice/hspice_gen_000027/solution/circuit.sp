* RC low-pass filter - HSPICE netlist
.global 0
.param rp=3900

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 24475.05n 48950.1n

* RC low-pass filter
r1 in out 3900
c1 out 0 1.5e-10

* Analysis
.tran 50p 36712.575n

* Measure rise and fall delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
