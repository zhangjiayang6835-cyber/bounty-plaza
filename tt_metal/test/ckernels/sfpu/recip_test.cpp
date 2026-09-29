#include "gtest/gtest.h"
#include "ckernel_sfpu_recip.h"
#include <random>
#include <algorithm>

class BF16RecipTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Adversarial test cases
        adversarial_inputs = {
            0x3380, 0x3301, 0x3381, 0x3302, 0x3382, 0x3303, // Edge cases
            0x3C00, 0x3C80, 0x3CC0, 0x3D00, 0x3D80, 0x3DC0, // Normalized
            0x0401, 0x0402, 0x0404, 0x0408, 0x0410, 0x0420  // Subnormal
        };
    }

    std::vector<uint16_t> adversarial_inputs;
};

TEST_F(BF16RecipTest, ZeroAndSpecialCases) {
    EXPECT_EQ(bf16_recip_0ulp(__builtin_bit_cast(bf16_t, 0x0000)), __builtin_bit_cast(bf16_t, 0x7F80));
    EXPECT_EQ(bf16_recip_0ulp(__builtin_bit_cast(bf16_t, 0x7F80)), __builtin_bit_cast(bf16_t, 0x7F80));
    EXPECT_TRUE(std::isnan(bf16_recip_0ulp(__builtin_bit_cast(bf16_t, 0x7FC0))));
}

TEST_F(BF16RecipTest, AdversarialCases) {
    for (uint16_t input : adversarial_inputs) {
        bf16_t x = __builtin_bit_cast(bf16_t, input);
        bf16_t result = bf16_recip_0ulp(x);
        bf16_t ref_result = compute_reference_recip(x); // Reference implementation

        // Verify 0-ULP correctness
        uint16_t result_bits = __builtin_bit_cast(uint16_t, result);
        uint16_t ref_bits = __builtin_bit_cast(uint16_t, ref_result);
        EXPECT_EQ(result_bits, ref_bits) << "Input: " << std::hex << input;
    }
}

TEST_F(BF16RecipTest, RandomizedInputs) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<uint16_t> dist(0x0400, 0x7BFF);

    for (int i = 0; i < 10000; ++i) {
        uint16_t input = dist(gen);
        bf16_t x = __builtin_bit_cast(bf16_t, input);
        bf16_t result = bf16_recip_0ulp(x);
        bf16_t ref_result = compute_reference_recip(x);

        uint16_t result_bits = __builtin_bit_cast(uint16_t, result);
        uint16_t ref_bits = __builtin_bit_cast(uint16_t, ref_result);
        EXPECT_EQ(result_bits, ref_bits) << "Random input failed: " << std::hex << input;
    }
}

// Reference implementation (would be in separate file in actual repo)
bf16_t compute_reference_recip(bf16_t x) {
    float f = __builtin_bit_cast(float, x);
    float recip_f = 1.0f / f;
    return __builtin_bit_cast(bf16_t, __builtin_bit_cast(float, recip_f));
}