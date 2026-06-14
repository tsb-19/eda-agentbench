.title MOSFET with Include - Missing Include
.include models_3.lib
M1 out gate gnd gnd nmos W=1u L=250n
R1 out 0 1k
Vdd gate 0 2.5
.tran 10p 10n
.end
