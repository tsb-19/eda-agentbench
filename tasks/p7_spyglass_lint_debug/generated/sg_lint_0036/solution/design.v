module cmb_clamp (
    input  wire [7:0] d,
    input  wire [7:0] lim,
    output reg  [7:0] y
);
    always @(*) begin
        if (d > lim)
            y = lim;
        else
            y = d;
    end
endmodule
