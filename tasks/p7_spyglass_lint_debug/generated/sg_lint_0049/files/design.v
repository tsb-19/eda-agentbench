module cmb_prio4 (
    input  wire [3:0] r,
    output reg  [1:0] y
);
    always @(*) begin
        if (r[3])
            y = 2'd3;
        else if (r[2])
            y = 2'd2;
        else if (r[1])
            y = 2'd1;
    end
endmodule
