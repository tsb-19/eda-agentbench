.title MOSFET with Include - Missing Include
.include models_2.lib
M1 out gate gnd gnd nmos W=4u L=90n
R1 out 0 1k
Vdd gate 0 1.2
.tran 10p 10n
.end
