* RLC bandpass filter - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 83.83192039085154n 167.66384078170307n

* RLC bandpass filter
l1 in mid 6.8e-06
r1 mid out 2700
c1 out 0 1e-11

* Analysis - timestep fine enough for LC oscillation
.tran 2n 528.5992316918657n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 td=83.83192039085154n targ v(out) val=0.9 fall=1

.end
