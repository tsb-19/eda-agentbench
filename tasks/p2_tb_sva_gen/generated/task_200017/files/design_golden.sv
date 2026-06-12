module priority_enc (
    input  wire [3:0] req,
    output reg  [1:0] grant
);
    always @(*) begin
        if      (req[0]) grant = 2'd0;
        else if (req[1]) grant = 2'd1;
        else if (req[2]) grant = 2'd2;
        else if (req[3]) grant = 2'd3;
        else             grant = 2'd0;
    end
endmodule
