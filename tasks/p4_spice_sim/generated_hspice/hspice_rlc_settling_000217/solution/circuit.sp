* RLC bandpass filter - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 2185.6094184751423n 4371.218836950285n

* RLC bandpass filter
l1 in mid 0.00022
r1 mid out 1800
c1 out 0 2.2e-11

* Analysis - timestep fine enough for LC oscillation
.tran 2n 4371.218836950285n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 td=2185.6094184751423n targ v(out) val=0.9 fall=1

.end
