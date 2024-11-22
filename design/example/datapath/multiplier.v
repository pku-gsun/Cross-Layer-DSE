module Multiplier (
    input wire clk,
    input [31:0] a,
    input [31:0] b,
    output [31:0] mult
);
    assign mult = a * b;
endmodule