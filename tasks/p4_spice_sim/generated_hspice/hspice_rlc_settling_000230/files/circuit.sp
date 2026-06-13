* RLC bandpass filter - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 319.4553325697725n 638.910665139545n

* RLC bandpass filter
l1 in mid 2.2e-05
r1 mid out 833
c1 out 0 4.7e-12

* Analysis - timestep fine enough for LC oscillation
.tran 2n 638.910665139545n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
