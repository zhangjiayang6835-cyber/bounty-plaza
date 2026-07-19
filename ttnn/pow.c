#include <math.h>
#include <stdint.h>

// Function to compute pow(x, y) with improved accuracy for non-integer exponents
float ttnn_pow(float x, float y) {
    // Use natural logarithm and exponential for better accuracy
    if (y!= (int)y) {  // Check if y is not an integer
        return exp(y * log(x));
    } else {
        // For integer exponents, use the existing fast path
        float result = 1.0;
        int int_y = (int)y;
        if (int_y < 0) {
            x = 1.0 / x;
            int_y = -int_y;
        }
        while (int_y > 0) {
            if (int_y & 1) {
                result *= x;
            }
            x *= x;
            int_y >>= 1;
        }
        return result;
    }
}

// Existing fast path for integer exponents
float ttnn_pow_int(float x, int y) {
    float result = 1.0;
    if (y < 0) {
        x = 1.0 / x;
        y = -y;
    }
    while (y > 0) {
        if (y & 1) {
            result *= x;
        }
        x *= x;
        y >>= 1;
    }
    return result;
}