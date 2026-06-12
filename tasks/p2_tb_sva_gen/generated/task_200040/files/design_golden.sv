module fifo_status (
    input  wire [3:0] count,
    output wire empty,
    output wire almost_full,
    output wire full
);
    assign empty        = (count == 4'd0);
    assign almost_full  = (count >= 4'd6);
    assign full         = (count >= 4'd8);
endmodule
