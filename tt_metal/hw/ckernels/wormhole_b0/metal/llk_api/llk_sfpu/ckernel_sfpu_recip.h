<content>
#include "llk_math_sfpu_dpu.h"
#include "llk_math_sfpu_common.h"
#include "llk_math_sfpu_recip_ref.h"

namespace llk {
namespace math {

template <typename T>
inline void reciprocate(T* __restrict__ dst, T* __restrict__ src) {
    // Handle special cases first
    uint32_t src_bits = reinterpret_cast<uint32_t&>(*src);
    uint32_t sign_bit = src_bits & 0x80000000;
    
    // Check for zero, infinity, NaN
    if ((src_bits & 0x7F800000) == 0x7F800000) {
        // Infinity or NaN
        *dst = *src;
        return;
    }
    
    if ((src_bits & 0x7FFFFFFF) == 0) {
        // Zero (1/0 = infinity with same sign)
        *dst = sign_bit ? 0xFF800000 : 0x7F800000;
        return;
    }
    
    // Convert to float32 for calculation if needed
    float32_t src_f32;
    if constexpr (std::is_same_v<T, bfloat16>) {
        src_f32 = bfloat16_to_float32(*src);
    } else {
        src_f32 = *reinterpret_cast<float32_t*>(src);
    }
    
    // Calculate reciprocal
    float32_t result_f32 = 1.0f / src_f32;
    
    // Convert back to target type
    if constexpr (std::is_same_v<T, bfloat16>) {
        // Use improved rounding for BF16
        *dst = float32_to_bfloat16_correctly_rounded(result_f32);
    } else {
        // Preserve existing faithful rounding for FP32
        *dst = *reinterpret_cast<T*>(&result_f32);
    }
}

// Explicit template instantiation
template void reciprocate<bfloat16>(bfloat16* __restrict__, bfloat16* __restrict__);
template void reciprocate<float32_t>(float32_t* __restrict__, float32_t* __restrict__);

} // namespace math
} // namespace llk
</content>