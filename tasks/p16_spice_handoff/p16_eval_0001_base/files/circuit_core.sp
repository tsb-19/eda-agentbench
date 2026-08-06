* Family B measurement-handoff circuit (IMMUTABLE CORE — do not edit; integrity-hashed).
* The executable deck (circuit_built.sp) is REGENERATED from this core + meas_config.json by build_deck.py.
.param av={av} cload={cload}
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
