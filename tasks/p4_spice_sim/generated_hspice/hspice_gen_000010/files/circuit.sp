* RC low-pass filter - HSPICE netlist
.global 0
.param rp=20400

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 2876.4n 5752.8n

* RC low-pass filter
r1 in out 20400
c1 out 0 4.7e-11

* Analysis
.tran 50p 4314.6n

* Measure rise and fall delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
