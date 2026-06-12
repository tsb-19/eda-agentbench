module vr_pipe (
    input  wire       clk, rst_n,
    input  wire       valid_in,
    input  wire       ready_out,
    input  wire [7:0] data_in,
    output reg        valid_out,
    output reg        ready_in,
    output reg [7:0]  data_out
);
    localparam S_IDLE=0, S_FULL=1;
    reg state, next;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) state <= S_IDLE;
        else        state <= next;
    always @(*) begin
        next = state;
        valid_out = 0;
        ready_in  = 0;
        case (state)
            S_IDLE: begin
                ready_in = 1;
                if (valid_in) next = S_FULL;
            end
            S_FULL: begin
                valid_out = 1;
                if (ready_out) next = S_IDLE;
            end
        endcase
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) data_out <= 8'd0;
        else data_out <= 8'd0;
endmodule
