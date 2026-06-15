module cmb_seg (
    input  wire [1:0] sel,
    output reg  [7:0] y
);
    always @(*) begin
        case (sel)
            2'd0: y = 8'h3f;
            2'd1: y = 8'h06;
            2'd2: y = 8'h5b;
            2'd3: y = 8'h4f;
        endcase
    end
endmodule
