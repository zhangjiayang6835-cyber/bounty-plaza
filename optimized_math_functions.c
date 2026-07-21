#include <math.h>
#include <stdint.h>
#include <stdio.h>

// Optimized minimax polynomial approximation for atan(x) in the range [-1, 1]
float fast_atan(float x) {
    float x2 = x * x;
    return x * (0.9998660f + x2 * (-0.3302905f + x2 * 
           (0.1801410f + x2 * (-0.0851330f + x2 * 
           0.0208351f))));
}

// Optimized minimax polynomial approximation for asin(x) in the range [-1, 1]
float fast_asin(float x) {
    float x2 = x * x;
    return x * (1.5707288f + x2 * (0.2145088f + x2 * 
           (-0.0181861f + x2 * (0.0003838f + x2 * 
           (-0.0000062f)))));
}

// Optimized acos(x) derived from the fast asin implementation
float fast_acos(float x) {
    return (float)M_PI_2 - fast_asin(x);
}


