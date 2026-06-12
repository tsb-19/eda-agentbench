module arbiter_rr (
    input  wire       clk, rst_n,
    input  wire [3:0] req,
    output reg  [3:0] grant
);
    reg [1:0] last;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            grant <= 4'b0000;
            last  <= 2'd3;
        end else begin
            grant <= 4'b0000;
            if      (req[(last+1) & 2'b11]      ) begin grant[(last+1) & 2'b11] <= 1; last <= (last+1) & 2'b11; end
            else if (req[(last+2) & 2'b11]      ) begin grant[(last+2) & 2'b11] <= 1; last <= (last+2) & 2'b11; end
            else if (req[(last+3) & 2'b11]      ) begin grant[(last+3) & 2'b11] <= 1; last <= (last+3) & 2'b11; end
            else if (req[last]                   ) begin grant[last] <= 1; end
        end
    end
endmodule
