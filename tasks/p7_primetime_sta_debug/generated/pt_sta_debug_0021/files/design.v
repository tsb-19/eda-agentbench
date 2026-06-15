module comparator_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] a,
    input  wire [7:0] b,
    output reg        gt,
    output reg        eq
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            gt <= 1'b0;
            eq <= 1'b0;
        end else begin
            gt <= (a > b);
            eq <= (a == b);
        end
    end
endmodule
