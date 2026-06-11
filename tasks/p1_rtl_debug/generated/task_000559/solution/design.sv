module mux4 (
    input  wire [1:0] sel,
    input  wire [7:0] d0, d1, d2, d3,
    output reg  [7:0] y
);
    always @(*) begin
        case (sel)
            2'b00: y = d0;
            2'b01: y = d1;
            2'b10: y = d2;
            2'b11: y = d3;
        endcase
    end
endmodule
