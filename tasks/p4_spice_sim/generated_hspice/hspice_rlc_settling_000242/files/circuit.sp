* RLC bandpass filter - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 6810.810574749528n 13621.621149499057n

* RLC bandpass filter
l1 in mid 0.0001
r1 mid out 7713
c1 out 0 4.7e-10

* Analysis - timestep fine enough for LC oscillation
.tran 2n 13621.621149499057n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 td=6810.810574749528n targ v(out) val=0.9 fall=1

.end
