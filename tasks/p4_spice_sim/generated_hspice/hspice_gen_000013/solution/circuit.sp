* RC low-pass filter - HSPICE netlist
.global 0
.param rp=470

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 118.14389999999999n 236.28779999999998n

* RC low-pass filter
r1 in out 470
c1 out 0 4.7e-12

* Analysis
.tran 50p 177.21585n

* Measure rise and fall delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
