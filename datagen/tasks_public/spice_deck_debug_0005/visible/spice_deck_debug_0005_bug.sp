.title MOSFET with Include - Bug 5
* BUG: .include references a file that does not exist
.include nonexistent_models.lib
M1 out gate gnd gnd nmos W=1u L=180n
R1 out 0 1k
Vdd gate 0 1.8
.tran 10p 10n
.end
