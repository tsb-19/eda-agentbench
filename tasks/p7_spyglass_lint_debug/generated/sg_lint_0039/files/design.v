module cmb_mux4 (
    input  wire [1:0] sel,
    input  wire [7:0] d0,
    input  wire [7:0] d1,
    input  wire [7:0] d2,
    input  wire [7:0] d3,
    output reg  [7:0] y
);
    always @(*) begin
        case (sel)
            2'd0: y = d0;
            2'd1: y = d1;
            2'd2: y = d2;
        endcase
    end
endmodule
