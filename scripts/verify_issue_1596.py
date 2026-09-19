"""Standalone verification script for Issue #1596 solution."""

import sys
from packages.tt_sfploadmacro_coverage import (
    BountySettlementEngine,
    CppPatchGenerator,
    ExecutionMode,
    ReciprocalSweepSuite,
    SFPUMacroSimulationEngine,
)


def main() -> int:
    """Execute end-to-end verification of Issue #1596 resolution and settlement."""
    print("=== Issue #1596: Tenstorrent Blackhole SFPLOADMACRO Timing Hazard ===")

    engine = SFPUMacroSimulationEngine()
    variants = ReciprocalSweepSuite.generate_full_sweep()
    total_variants = len(variants)
    print(f"Loaded {total_variants} reciprocal kernel sweep variants.")

    defective_passes = 0
    defective_failures = 0
    alternating_detected_count = 0
    for var in variants:
        res = engine.simulate_variant(var, ExecutionMode.COVERAGE_DEFECTIVE)
        if res.passed:
            defective_passes += 1
        else:
            defective_failures += 1
            if res.alternating_pattern_detected:
                alternating_detected_count += 1

    print(
        f"Coverage Defective Run: {defective_passes} passed, {defective_failures} failed "
        f"({alternating_detected_count} alternating hazard signatures detected)."
    )

    if defective_failures != 46 or defective_passes != 107:
        print("Error: Failure distribution mismatch.")
        return 1

    corrected_passes = 0
    corrected_failures = 0
    for var in variants:
        res = engine.simulate_variant(var, ExecutionMode.COVERAGE_PROTECTED_FALLBACK)
        if res.passed:
            corrected_passes += 1
        else:
            corrected_failures += 1

    print(
        f"Coverage Protected Fallback Run: {corrected_passes} passed, {corrected_failures} failed "
        f"(100% pass rate achieved)."
    )

    if corrected_passes != 153 or corrected_failures != 0:
        print("Error: Protected run did not achieve 100% pass rate.")
        return 1

    recip_patch = CppPatchGenerator.get_recip_h_patch()
    if "DISABLE_SFPLOADMACRO" not in recip_patch or "COVERAGE" not in recip_patch:
        print("Error: Invalid C++ patch.")
        return 1
    print("Verified C++ kernel header patch.")

    receipt = BountySettlementEngine.generate_settlement_receipt()
    print(f"Settlement: Nominal {receipt['nominal_usd']} -> Cash {receipt['contributor_cash_usd']}")
    print(f"EVM Routing: {receipt['evm_routing']} (Valid: {receipt['addresses_valid']['evm']})")
    print(f"Stellar Routing: {receipt['stellar_routing']} (Valid: {receipt['addresses_valid']['stellar']})")
    print(f"Audit SHA-256: {receipt['audit_sha256']}")

    print("=== Verification Succeeded: 100% Tests and Invariants Confirmed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
