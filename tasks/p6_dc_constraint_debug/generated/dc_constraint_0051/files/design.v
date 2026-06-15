module accumulator (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        en,
    input  wire [7:0]  data,
    output reg  [15:0] acc
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            acc <= 16'd0;
        else if (en)
            acc <= acc + {8'd0, data};
    end
endmodule
