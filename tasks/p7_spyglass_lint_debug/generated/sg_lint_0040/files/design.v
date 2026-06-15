module sq_sticky (
    input  wire       clk,
    input  wire       rst_n,
    input  wire setf,
    output reg  flag
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            flag <= 1'b0;
        else if (setf)
            flag <= 1'b1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            flag <= {1{1'b0}};
    end
endmodule
