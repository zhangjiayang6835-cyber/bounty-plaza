#include "pow.h"
#include <stdio.h>
#include <math.h>

int main() {
    float x = 10000.0;
    float y = 1.7984;

    float result = ttnn_pow(x, y);
    float expected = pow(x, y);

    printf("ttnn_pow(%.6f, %.6f) = %.6f\n", x, y, result);
    printf("Expected: %.6f\n", expected);
    printf("Error (ULP): %f\n", fabs(result - expected) / (FLT_EPSILON * fmax(fabs(result), fabs(expected))));

    return 0;
}