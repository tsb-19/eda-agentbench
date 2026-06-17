* RLC bandpass filter - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 5706.986466042728n 11413.972932085457n

* RLC bandpass filter
l1 in mid 0.00033
r1 mid out 1800
c1 out 0 1e-10

* Analysis - timestep fine enough for LC oscillation
.tran 2n 11413.972932085457n

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 td=5706.986466042728n targ v(out) val=0.9 fall=1

.end
