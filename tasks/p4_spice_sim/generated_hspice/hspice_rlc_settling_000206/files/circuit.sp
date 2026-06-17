* RLC bandpass filter - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 1476.548547187203n 2953.097094374406n

* RLC bandpass filter
l1 in mid 0.00047
r1 mid out 4491
c1 out 0 4.7e-12

* Analysis - timestep fine enough for LC oscillation
.tran 2n 2953.097094374406n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 td=1476.548547187203n targ v(out) val=0.9 fall=1

.end
