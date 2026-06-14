.title NOR Gate - Missing Include
.include nor_models.lib
M1 mid a vdd vdd pmos W=4u L=180n
M2 out b mid mid pmos W=4u L=180n
M3 out a gnd gnd nmos W=1u L=180n
M4 out b gnd gnd nmos W=1u L=180n
Vdd vdd gnd 1.8
Va a gnd PULSE(0 1.8 0 100p 100p 1n 2n)
Vb b gnd PULSE(0 1.8 0 100p 100p 2n 4n)
.tran 10p 8n
.end
