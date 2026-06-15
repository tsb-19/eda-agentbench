module cmb_byterev (
    input  wire [7:0] a,
    input  wire       sel,
    output reg  [7:0] y
);
    always @(*) begin
        if (sel)
            y = {a[3:0], a[7:4]};
    end
endmodule
