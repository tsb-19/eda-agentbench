module adder_wide (
    input  wire [7:0] a, b,
    output wire [8:0] sum
);
    wire [7:0] s8;
    assign s8 = a + b;
    assign sum = {1'b0, s8};
endmodule
