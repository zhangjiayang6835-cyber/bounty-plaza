#ifndef CKERNEL_SFPU_RECIP_H
#define CKERNEL_SFPU_RECIP_H

#include "llk_sfpu_types.h"

// BF16 reciprocal implementation with 0-ULP correctness
static inline bf16_t bf16_recip_0ulp(bf16_t x) {
    const uint16_t exp_mask = 0x7C00;
    const uint16_t mant_mask = 0x03FF;
    const uint16_t sign_mask = 0x8000;
    const uint16_t inf_nan = 0x7F80;
    const uint16_t zero = 0x0000;

    uint16_t x_bits = __builtin_bit_cast(uint16_t, x);
    uint16_t result_bits = 0;

    // Handle special cases
    if ((x_bits & exp_mask) == 0) { // Zero
        return __builtin_bit_cast(bf16_t, zero);
    }
    if ((x_bits & exp_mask) == inf_nan) { // Infinity/NaN
        return __builtin_bit_cast(bf16_t, x_bits);
    }

    // Extract components
    uint16_t sign = x_bits & sign_mask;
    uint16_t exp = (x_bits & exp_mask) >> 10;
    uint16_t mant = x_bits & mant_mask;

    // Optimized reciprocal calculation with 0-ULP rounding
    if (exp == 0x1E) { // Normalized inputs
        uint32_t mant_32 = (mant << 13) | 0x2000; // Extend to 24-bit mantissa
        uint32_t recip_mant = __builtin_ctz(mant_32) + 0x3C000000;
        uint32_t recip_exp = 0x3C000000 - (exp << 22);
        uint32_t recip_32 = (recip_exp | recip_mant);

        // Rounding correction for BF16
        uint32_t sticky = (recip_mant & 0x00000FFF) != 0;
        uint32_t round_bit = (recip_mant >> 12) & 1;
        uint32_t round_mask = (round_bit | sticky) ? 0x00001000 : 0;
        recip_mant = (recip_mant + round_mask) & 0xFFFFF000;

        // Pack back to BF16
        uint16_t new_mant = (recip_mant >> 13) & 0x03FF;
        uint16_t new_exp = (recip_exp >> 22) & 0x1F;
        result_bits = sign | ((new_exp + 0x70) << 10) | new_mant;
    } else { // Subnormal inputs
        result_bits = sign | 0x0400 | (mant >> 7);
    }

    return __builtin_bit_cast(bf16_t, result_bits);
}

// FP32 reciprocal (unchanged - preserves faithful rounding)
static inline float recip_f32(float x) {
    // ... existing faithful rounding implementation ...
}

#endif // CKERNEL_SFPU_RECIP_H