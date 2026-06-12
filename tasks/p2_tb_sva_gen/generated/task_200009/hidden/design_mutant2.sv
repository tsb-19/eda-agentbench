module fsm_simple (
    input  wire clk, rst_n, go, finish,
    output reg  busy, completed
);
    localparam S_IDLE=0, S_RUN=1, S_DONE=2;
    reg [1:0] state, next;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) state <= S_IDLE;
        else        state <= next;
    always @(*) begin
        next = state;
        busy = 0;
        completed = 0;
        case (state)
            S_IDLE: begin if (go) next = S_RUN; end
            S_RUN:  begin if (finish) next = S_DONE; end
            S_DONE: begin completed = 1; next = S_IDLE; end
        endcase
    end
endmodule
