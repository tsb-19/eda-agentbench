* RLC bandpass filter - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 180.4707580845021n 360.9415161690042n

* RLC bandpass filter
l1 in mid 3.3e-06
r1 mid out 820
c1 out 0 1e-11

* Analysis - timestep fine enough for LC oscillation
.tran 2n 360.9415161690042n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 td=180.4707580845021n targ v(out) val=0.9 fall=1

.end
