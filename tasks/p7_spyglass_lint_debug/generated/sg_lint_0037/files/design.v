module sq_capture (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       valid,
    input  wire [7:0] din,
    output reg  [7:0] data
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            data <= 8'd0;
        else if (valid)
            data <= din;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            data <= {8{1'b0}};
    end
endmodule
