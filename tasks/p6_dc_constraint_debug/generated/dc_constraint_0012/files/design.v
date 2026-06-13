module fsm_ctrl (
    input  wire clk,
    input  wire rst_n,
    input  wire start,
    output reg  busy,
    output reg  done
);
    localparam S_IDLE = 2'd0, S_RUN = 2'd1, S_DONE = 2'd2;
    reg [1:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy  <= 1'b0;
            done  <= 1'b0;
        end else begin
            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    done <= 1'b0;
                    if (start) state <= S_RUN;
                end
                S_RUN: begin
                    busy <= 1'b1;
                    done <= 1'b0;
                    state <= S_DONE;
                end
                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
