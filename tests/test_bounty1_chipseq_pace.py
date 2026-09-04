"""Acceptance and unit tests for Bounty #1: ChIP-seq & Methylation PACE Pipeline (#829 - $15,000 USDC).
Validates all acceptance criteria from upstream mister3ai-cmyk/ngp-sovereign-synesis-bounties#1.
"""

import json
from pathlib import Path
import pytest
from scripts.bounty1_chipseq_pace import (
    ChIPSeqPacePipeline,
    calculate_pearson_r,
    DunedinPACEModel,
    ChIPSeqQCFilter,
    REFERENCE_INTERCEPT,
    INTERCEPT_TOLERANCE,
    MIN_PEARSON_R,
    MAPQ_MIN,
    FDR_MAX,
    IDR_MAX,
    NRF_MIN,
)


@pytest.fixture(scope="module")
def manifest():
    pipeline = ChIPSeqPacePipeline(results_dir="results")
    manifest_data = pipeline.produce_manifest()
    return manifest_data


def test_dunedinpace_intercept(manifest):
    """Verify DunedinPACE intercept == 51.024577 ± 0.001."""
    intercept = manifest["dunedinpace"]["intercept"]
    assert abs(intercept - REFERENCE_INTERCEPT) <= INTERCEPT_TOLERANCE, (
        f"DunedinPACE intercept {intercept:.6f} deviates from {REFERENCE_INTERCEPT}"
    )


def test_h3k9ac_pearson_r(manifest):
    """Verify H3K9ac → DunedinPACE Pearson r > 0.92."""
    r = manifest["correlations"]["H3K9ac_vs_DunedinPACE"]["pearson_r"]
    assert r > MIN_PEARSON_R, (
        f"H3K9ac → DunedinPACE Pearson r = {r:.4f}, required > {MIN_PEARSON_R}"
    )
    p = manifest["correlations"]["H3K9ac_vs_DunedinPACE"]["p_value"]
    assert p < 0.01, f"H3K9ac p-value {p} must be < 0.01"


def test_h3k56ac_pearson_r(manifest):
    """Verify H3K56ac → DunedinPACE Pearson r > 0.92."""
    r = manifest["correlations"]["H3K56ac_vs_DunedinPACE"]["pearson_r"]
    assert r > MIN_PEARSON_R, (
        f"H3K56ac → DunedinPACE Pearson r = {r:.4f}, required > {MIN_PEARSON_R}"
    )
    p = manifest["correlations"]["H3K56ac_vs_DunedinPACE"]["p_value"]
    assert p < 0.01, f"H3K56ac p-value {p} must be < 0.01"


def test_peak_calling_fdr(manifest):
    """Verify peak calling FDR < 0.05."""
    fdr = manifest["peak_calling"]["fdr"]
    assert fdr < FDR_MAX, f"Peak-calling FDR {fdr} >= {FDR_MAX}"


def test_mapq_filter(manifest):
    """Verify alignment MAPQ threshold >= 30."""
    mapq_threshold = manifest["alignment"]["mapq_threshold"]
    assert mapq_threshold >= MAPQ_MIN, (
        f"MAPQ threshold {mapq_threshold} < {MAPQ_MIN}"
    )


def test_data_deposit_doi(manifest):
    """Verify persistent data deposit DOI starts with '10.'."""
    doi = manifest.get("data_deposit_doi", "")
    assert doi.startswith("10."), f"Invalid or missing DOI: '{doi}'"


def test_chip_seq_library_quality(manifest):
    """Verify IDR <= 0.05 and NRF > 0.9 for both H3K9ac and H3K56ac marks."""
    qc = manifest["chip_seq_qc"]
    for mark in ["H3K9ac", "H3K56ac"]:
        idr = qc[mark]["idr"]
        nrf = qc[mark]["nrf"]
        assert idr <= IDR_MAX, f"{mark} IDR {idr:.4f} > {IDR_MAX}"
        assert nrf > NRF_MIN, f"{mark} NRF {nrf:.4f} <= {NRF_MIN}"


def test_pearson_r_math_edge_cases():
    """Verify exact mathematical behavior of Pearson r calculator."""
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [2.0, 4.0, 6.0, 8.0, 10.0]
    r, p = calculate_pearson_r(x, y)
    assert abs(r - 1.0) < 1e-6

    # Inverse correlation
    y_inv = [10.0, 8.0, 6.0, 4.0, 2.0]
    r_inv, _ = calculate_pearson_r(x, y_inv)
    assert abs(r_inv - (-1.0)) < 1e-6

    # Zero variance returns 0.0
    flat = [5.0, 5.0, 5.0, 5.0, 5.0]
    r_zero, _ = calculate_pearson_r(x, flat)
    assert r_zero == 0.0


def test_qc_filter_logic():
    filter_engine = ChIPSeqQCFilter(min_mapq=30, max_fdr=0.05)
    filtered_mapqs = filter_engine.filter_alignments([10, 25, 30, 42, 60])
    assert filtered_mapqs == [30, 42, 60]

    with pytest.raises(ValueError):
        filter_engine.filter_alignments([5, 12, 29])
