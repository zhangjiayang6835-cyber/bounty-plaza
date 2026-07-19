#include <math.h>
#include <stdint.h>
#include <stdio.h>

// Polynomial approximation for atan(x) in the range -1 to 1
float fast_atan(float x) {
    float x2 = x * x;
    return x * (0.9998660f + x2 * (-0.3302995f + x2 * (0.1801410f + x2 * (-0.0851330f + x2 * 0.0208351f))));
}

// Polynomial approximation for asin(x) in the range -1 to 1
float fast_asin(float x) {
    float x2 = x * x;
    return x * (1.5707288f + x * (0.2145988f + x2 * (-0.0181861f + x2 * (0.0003898f + x2 * (-0.0000062f)))));
}

// Polynomial approximation for acos(x) in the range -1 to 1
float fast_acos(float x) {
    return M_PI_2 - fast_asin(x);
}

int main() {
    float x = 0.5;

    // Example usage
    float result_atan = fast_atan(x);
    float result_asin = fast_asin(x);
    float result_acos = fast_acos(x);

    printf("fast_atan(%.2f) = %.6f\n", x, result_atan);
    printf("fast_asin(%.2f) = %.6f\n", x, result_asin);
    printf("fast_acos(%.2f) = %.6f\n", x, result_acos);

    return 0;
}