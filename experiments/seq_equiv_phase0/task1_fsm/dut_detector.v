// Design under test: the SAME "1011" overlapping detector, re-encoded one-hot.
// Next-state is expressed as boolean product terms (one term per incoming transition),
// not a case table -- this is a structural re-encoding of ref_detector, claimed equivalent.
// q is one-hot:  q[0]=S0("")  q[1]=S1("1")  q[2]=S2("10")  q[3]=S3("101").
module dut_detector (
    input  wire clk,
    input  wire rst,      // sync, active-high -> S0
    input  wire din,
    output wire det
);
    reg  [3:0] q;
    wire ns0, ns1, ns2, ns3;

    // incoming transitions to each one-hot state:
    assign ns0 = (q[0] & ~din) | (q[2] & ~din) | (q[3] & ~din);
    assign ns1 = (q[0] &  din) | (q[1] &  din) | (q[3] &  din);
    assign ns2 = (q[1] & ~din);
    assign ns3 = (q[2] &  din);

    assign det = q[3] & din;

    always @(posedge clk)
        if (rst) q <= 4'b0001;            // S0
        else     q <= {ns3, ns2, ns1, ns0};
endmodule
