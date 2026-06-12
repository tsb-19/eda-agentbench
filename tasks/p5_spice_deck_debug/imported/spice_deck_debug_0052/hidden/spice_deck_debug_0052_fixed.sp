.title Ring Oscillator - Wrong Pin Count
.subckt inv in out vdd gnd
M1 out in vdd vdd pmos W=2u L=180n
M2 out in gnd gnd nmos W=1u L=180n
.ends inv
X1 n1 n2 vdd 0 inv
X2 n2 n3 vdd 0 inv
X3 n3 n1 vdd 0 inv
Vdd vdd 0 1.8
.ic v(n1)=1.8
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
.tran 1p 100n
.end
