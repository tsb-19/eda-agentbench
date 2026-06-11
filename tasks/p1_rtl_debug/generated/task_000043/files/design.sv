module mux2 (
    input  wire a, b, sel,
    output reg  y
);
    always @(a or sel) begin
        if (sel) y = a;
        else     y = b;
    end
endmodule
