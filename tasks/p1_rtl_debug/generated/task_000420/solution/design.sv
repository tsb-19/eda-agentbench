module range_check (
    input  wire [3:0] val,
    output reg        in_range
);
    always @(*) begin
        in_range = (val >= 4'd3) && (val <= 4'd12);
    end
endmodule
