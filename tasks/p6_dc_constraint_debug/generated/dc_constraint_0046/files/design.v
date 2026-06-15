module alu_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] op,
    input  wire [7:0] a,
    input  wire [7:0] b,
    output reg  [7:0] result
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            result <= 8'd0;
        else begin
            case (op)
                2'd0: result <= a + b;
                2'd1: result <= a - b;
                2'd2: result <= a & b;
                2'd3: result <= a | b;
            endcase
        end
    end
endmodule
