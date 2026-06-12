.title MOSFET with Include - Missing Include
.include models_1.lib
M1 out gate gnd gnd nmos W=2u L=180n
R1 out 0 1k
Vdd gate 0 1.8
.tran 10p 10n
.end
