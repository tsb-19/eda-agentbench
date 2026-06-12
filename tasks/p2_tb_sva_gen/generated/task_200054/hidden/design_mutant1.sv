module handshake_reg (
    input  wire       clk, rst_n,
    input  wire       valid_in,
    input  wire       ready_in,
    input  wire [7:0] data_in,
    output reg        valid_out,
    output reg        ready_out,
    output reg [7:0]  data_out
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out <= 0;
            ready_out <= 1;
            data_out  <= 8'd0;
        end else begin
            if (valid_in && ready_out) begin
                valid_out <= 1;
                ready_out <= 0;
            end else if (ready_in && valid_out) begin
                valid_out <= 0;
                ready_out <= 1;
            end
        end
    end
endmodule
