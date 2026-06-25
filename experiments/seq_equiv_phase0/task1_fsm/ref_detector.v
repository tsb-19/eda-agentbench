// Reference: "1011" overlapping sequence detector (Mealy), binary state encoding.
// States encode the matched prefix of "1011":  S0="", S1="1", S2="10", S3="101".
// `det` asserts on the input bit that completes "1011". Overlapping: after a match the
// trailing "1" seeds the next attempt.
module ref_detector (
    input  wire clk,
    input  wire rst,      // sync, active-high -> S0
    input  wire din,
    output wire det
);
    localparam S0 = 2'd0, S1 = 2'd1, S2 = 2'd2, S3 = 2'd3;
    reg  [1:0] state;
    reg  [1:0] nstate;
    reg        det_c;

    always @(*) begin
        nstate = state;
        det_c  = 1'b0;
        case (state)
            S0: nstate = din ? S1 : S0;
            S1: nstate = din ? S1 : S2;
            S2: nstate = din ? S3 : S0;
            S3: begin
                if (din) begin nstate = S1; det_c = 1'b1; end  // match; overlap -> "1"
                else            nstate = S2;                    // keep "10" context
            end
        endcase
    end

    assign det = det_c;

    always @(posedge clk)
        if (rst) state <= S0;
        else     state <= nstate;
endmodule
