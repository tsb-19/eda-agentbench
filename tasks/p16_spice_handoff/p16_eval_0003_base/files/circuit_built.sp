* Family B measurement-handoff circuit (macro amplifier; real HSPICE computation)
.param av=50.0 cload=5e-12
vin in 0 dc 0 ac 1
ein outc 0 in 0 av
r1 outc outa 1e3
c1 outa 0 1.59e-9
r2 outa out 1e3
c2 out 0 cload
rl out 0 1e12
.ac dec 20 1 1g
.measure ac gain_db max vdb(out)
.measure ac gbw_hz when vdb(out)=0 fall=1
.end
