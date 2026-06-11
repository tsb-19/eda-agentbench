* RC low-pass filter - HSPICE netlist
.global 0
.param rp=4700

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 182.406n 364.812n

* RC low-pass filter
r1 in out 4700
c1 out 0 1e-12

* Analysis
.tran 50p 273.60900000000004n

* Measure rise and fall delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
