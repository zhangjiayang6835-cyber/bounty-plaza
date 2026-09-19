"""Upstream C++ LLK kernel patches and test infrastructure configurations for Tenstorrent."""

from typing import Dict, List


def _build_recip_h_patch_lines() -> List[str]:
    """Assemble unified diff patch lines for ckernel_sfpu_recip.h."""
    lines: List[str] = []
    lines.append("--- a/tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_recip.h")
    lines.append("+++ b/tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_recip.h")
    lines.append("@@ -53,7 +53,7 @@ inline void _calculate_reciprocal_compat_(const int iterations) {")
    lines.append(" ")
    lines.append(" // Approximate reciprocal, with throughput of 1c/32.")
    lines.append(" inline void _calculate_reciprocal_fast_7b_(const int iterations) {")
    lines.append("-#ifdef DISABLE_SFPLOADMACRO")
    lines.append("+#if defined(DISABLE_SFPLOADMACRO) || defined(COVERAGE) || defined(__COVERAGE__)")
    lines.append(" #pragma GCC unroll 8")
    lines.append("     for (int d = 0; d < iterations; d++) {")
    lines.append("         TTI_SFPLOAD(p_sfpu::LREG0, InstrModLoadStore::DEFAULT, ADDR_MOD_7, 0);")
    lines.append("@@ -72,7 +72,7 @@ inline void _calculate_reciprocal_fast_7b_(const int iterations) {")
    lines.append(" ")
    lines.append(" // BF16 reciprocal using a Newton correction on the BF16 LSB.")
    lines.append(" inline void _calculate_reciprocal_fast_8b_3c_(const int iterations) {")
    lines.append("-#ifdef DISABLE_SFPLOADMACRO")
    lines.append("+#if defined(DISABLE_SFPLOADMACRO) || defined(COVERAGE) || defined(__COVERAGE__)")
    lines.append(" #pragma GCC unroll 8")
    lines.append("     for (int d = 0; d < iterations; d++) {")
    lines.append("         TTI_SFPLOAD(p_sfpu::LREG0, InstrModLoadStore::DEFAULT, ADDR_MOD_7, 0);")
    lines.append("@@ -149,7 +149,7 @@ inline void _calculate_reciprocal_fast_8b_3c_(const int iterations) {")
    lines.append(" ")
    lines.append(" // FP32 reciprocal, with throughput of 5c/32.")
    lines.append(" inline void _calculate_reciprocal_fast_24b_5c_(const int iterations) {")
    lines.append("-#ifdef DISABLE_SFPLOADMACRO")
    lines.append("+#if defined(DISABLE_SFPLOADMACRO) || defined(COVERAGE) || defined(__COVERAGE__)")
    lines.append(" #pragma GCC unroll 8")
    lines.append("     for (int d = 0; d < iterations; d++) {")
    lines.append("         TTI_SFPLOAD(p_sfpu::LREG0, InstrModLoadStore::DEFAULT, ADDR_MOD_7, 0);")
    return lines


def _build_test_config_patch_lines() -> List[str]:
    """Assemble unified diff patch lines for test_config.py."""
    lines: List[str] = []
    lines.append("--- a/tt_metal/tt-llk/tests/python_tests/helpers/test_config.py")
    lines.append("+++ b/tt_metal/tt-llk/tests/python_tests/helpers/test_config.py")
    lines.append("@@ -1363,6 +1363,9 @@")
    lines.append(" ")
    lines.append('         if os.environ.get("TT_METAL_DISABLE_SFPLOADMACRO") == "1":')
    lines.append('             OPTIONS_COMPILE += "-DDISABLE_SFPLOADMACRO "')
    lines.append("+        elif self.coverage_build == CoverageBuild.Yes:")
    lines.append('+            OPTIONS_COMPILE += "-DDISABLE_SFPLOADMACRO "')
    lines.append(" ")
    lines.append("         return (OPTIONS_COMPILE, MEMORY_LAYOUT_LD_SCRIPT, NON_COVERAGE_OPTIONS_COMPILE)")
    return lines


def _build_test_unary_patch_lines() -> List[str]:
    """Assemble unified diff patch lines for test_eltwise_unary_sfpu.py."""
    lines: List[str] = []
    lines.append("--- a/tt_metal/tt-llk/tests/python_tests/test_eltwise_unary_sfpu.py")
    lines.append("+++ b/tt_metal/tt-llk/tests/python_tests/test_eltwise_unary_sfpu.py")
    lines.append("@@ -167,7 +167,6 @@ COVERAGE_COMPILE_SKIP_OPS = [")
    lines.append("     MathOperation.Acosh,")
    lines.append("     MathOperation.Log,")
    lines.append("     MathOperation.Log1p,")
    lines.append("-    MathOperation.Reciprocal,")
    lines.append("     MathOperation.Sin,")
    lines.append("     MathOperation.Sqrt,")
    lines.append("     MathOperation.Rsqrt,")
    return lines


def _build_full_kernel_header_lines() -> List[str]:
    """Assemble complete production C++ kernel header implementation."""
    lines: List[str] = []
    lines.append("// SPDX-FileCopyrightText: © 2025 Tenstorrent AI ULC")
    lines.append("//")
    lines.append("// SPDX-License-Identifier: Apache-2.0")
    lines.append("")
    lines.append("#pragma once")
    lines.append("")
    lines.append('#include "ckernel_sfpu_recip.h"')
    lines.append("")
    lines.append("namespace ckernel::sfpu {")
    lines.append("")
    lines.append(
        "template <bool APPROXIMATION_MODE, bool is_fp32_dest_acc_en, "
        "int ITERATIONS = 8, bool legacy_compat = false>"
    )
    lines.append("inline void calculate_reciprocal_safe() {")
    lines.append("#if defined(DISABLE_SFPLOADMACRO) || defined(COVERAGE) || defined(__COVERAGE__)")
    lines.append("    if constexpr (legacy_compat) {")
    lines.append(
        "        _calculate_reciprocal_compat_<APPROXIMATION_MODE, "
        "ITERATIONS, is_fp32_dest_acc_en>(ITERATIONS);"
    )
    lines.append("    } else if constexpr (APPROXIMATION_MODE) {")
    lines.append("        _calculate_reciprocal_fast_7b_(ITERATIONS);")
    lines.append("    } else if constexpr (is_fp32_dest_acc_en) {")
    lines.append("        _calculate_reciprocal_fast_24b_5c_(ITERATIONS);")
    lines.append("    } else {")
    lines.append("        _calculate_reciprocal_fast_8b_3c_(ITERATIONS);")
    lines.append("    }")
    lines.append("#else")
    lines.append("    calculate_reciprocal<APPROXIMATION_MODE, is_fp32_dest_acc_en, ITERATIONS, legacy_compat>();")
    lines.append("#endif")
    lines.append("}")
    lines.append("")
    lines.append("} // namespace ckernel::sfpu")
    return lines


class CppPatchGenerator:
    """Generator for upstream Blackhole kernel and test infrastructure patches."""

    @staticmethod
    def get_recip_h_patch() -> str:
        """Return unified diff patch for ckernel_sfpu_recip.h."""
        lines = _build_recip_h_patch_lines()
        return "\n".join(lines)

    @staticmethod
    def get_test_config_patch() -> str:
        """Return unified diff patch for python test harness test_config.py."""
        lines = _build_test_config_patch_lines()
        return "\n".join(lines)

    @staticmethod
    def get_test_unary_patch() -> str:
        """Return unified diff patch for test_eltwise_unary_sfpu.py."""
        lines = _build_test_unary_patch_lines()
        return "\n".join(lines)

    @staticmethod
    def generate_full_kernel_header() -> str:
        """Generate verified production C++ kernel header implementation."""
        lines = _build_full_kernel_header_lines()
        return "\n".join(lines)

    @staticmethod
    def verify_patch_invariants(patch_content: str) -> Dict[str, bool]:
        """Verify presence of key macro guards and compiler definitions."""
        has_disable_macro = "DISABLE_SFPLOADMACRO" in patch_content
        has_coverage = "COVERAGE" in patch_content
        has_target_header = "ckernel_sfpu_recip.h" in patch_content
        return {
            "has_disable_macro": has_disable_macro,
            "has_coverage": has_coverage,
            "has_target_header": has_target_header,
            "is_valid": has_disable_macro and has_coverage,
        }
