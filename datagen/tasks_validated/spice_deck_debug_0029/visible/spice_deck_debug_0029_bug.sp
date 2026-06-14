.title 7-Stage Ring Oscillator - Missing Subckt
X1 n1 n2 vdd 0 inv
X2 n2 n3 vdd 0 inv
X3 n3 n4 vdd 0 inv
X4 n4 n5 vdd 0 inv
X5 n5 n6 vdd 0 inv
X6 n6 n7 vdd 0 inv
X7 n7 n1 vdd 0 inv
Vdd vdd 0 1.8
.ic v(n1)=1.8
.subckt inv_stage in out vdd gnd
M1 out in vdd vdd pmos W=2u L=180n
M2 out in gnd gnd nmos W=1u L=180n
.ends inv_stage
.model pmos pmos (level=1 vto=-0.7 kp=50u)
.model nmos nmos (level=1 vto=0.7 kp=120u)
.tran 1p 500n
.end
