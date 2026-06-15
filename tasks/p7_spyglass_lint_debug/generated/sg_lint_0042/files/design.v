module cmb_decode (
    input  wire [1:0] sel,
    output reg  [3:0] y
);
    always @(*) begin
        case (sel)
            2'd0: y = 4'b0001;
            2'd1: y = 4'b0010;
            2'd2: y = 4'b0100;
        endcase
    end
endmodule
