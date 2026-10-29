"""
Automated acceptance tests for Bounty #1: ChIP-seq & DunedinPACE Pipeline.
Run: pytest tests/test_bounty1_pace.py -v
"""
import json
import pathlib
import subprocess

import pytest

REFERENCE_INTERCEPT = 51.024577
INTERCEPT_TOLERANCE = 0.001
MIN_PEARSON_R = 0.92


# ---------------------------------------------------------------------------
# Helper: load submission manifest (submitter must provide results/manifest.json)
# ---------------------------------------------------------------------------
MANIFEST = pathlib.Path("results/manifest.json")

# Every test in this module validates a submission described by MANIFEST.
# Without it there is nothing to validate, so the whole module skips rather
# than reporting a false pass. This is declared at module level so that a
# test added later cannot run by accident just because it forgot to request
# the `manifest` fixture.
pytestmark = pytest.mark.skipif(
    not MANIFEST.exists(),
    reason=f"{MANIFEST} not found — no Bounty #1 submission to validate; run the ChIP-seq / DunedinPACE pipeline first",
)


@pytest.fixture(scope="module")
def manifest():
    if not MANIFEST.exists():
        pytest.skip("results/manifest.json not found — run pipeline first")
    with open(MANIFEST) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test 1: DunedinPACE intercept
# ---------------------------------------------------------------------------
def test_dunedinpace_intercept(manifest):
    intercept = manifest["dunedinpace"]["intercept"]
    assert abs(intercept - REFERENCE_INTERCEPT) <= INTERCEPT_TOLERANCE, (
        f"DunedinPACE intercept {intercept:.6f} deviates from reference "
        f"{REFERENCE_INTERCEPT} by more than {INTERCEPT_TOLERANCE}"
    )


# ---------------------------------------------------------------------------
# Test 2: H3K9ac Pearson r
# ---------------------------------------------------------------------------
def test_h3k9ac_pearson_r(manifest):
    r = manifest["correlations"]["H3K9ac_vs_DunedinPACE"]["pearson_r"]
    assert r > MIN_PEARSON_R, (
        f"H3K9ac → DunedinPACE Pearson r = {r:.4f}, required > {MIN_PEARSON_R}"
    )


# ---------------------------------------------------------------------------
# Test 3: H3K56ac Pearson r
# ---------------------------------------------------------------------------
def test_h3k56ac_pearson_r(manifest):
    r = manifest["correlations"]["H3K56ac_vs_DunedinPACE"]["pearson_r"]
    assert r > MIN_PEARSON_R, (
        f"H3K56ac → DunedinPACE Pearson r = {r:.4f}, required > {MIN_PEARSON_R}"
    )


# ---------------------------------------------------------------------------
# Test 4: Docker image checksum
# ---------------------------------------------------------------------------
def test_docker_image_checksum(manifest):
    expected_md5 = manifest.get("docker_image_md5")
    if not expected_md5:
        pytest.skip("docker_image_md5 not provided in manifest")
    image_path = pathlib.Path(manifest["docker_image_path"])
    assert image_path.exists(), f"Docker image not found: {image_path}"
    result = subprocess.run(
        ["md5sum", str(image_path)], capture_output=True, text=True, check=True
    )
    actual_md5 = result.stdout.split()[0]
    assert actual_md5 == expected_md5, (
        f"Docker image MD5 mismatch: got {actual_md5}, expected {expected_md5}"
    )


# ---------------------------------------------------------------------------
# Test 5: FDR threshold on peak calling
# ---------------------------------------------------------------------------
def test_peak_calling_fdr(manifest):
    fdr = manifest["peak_calling"]["fdr"]
    assert fdr < 0.05, f"Peak-calling FDR {fdr} >= 0.05"


# ---------------------------------------------------------------------------
# Test 6: MAPQ filter applied
# ---------------------------------------------------------------------------
def test_mapq_filter(manifest):
    mapq_threshold = manifest["alignment"]["mapq_threshold"]
    assert mapq_threshold >= 30, (
        f"MAPQ threshold {mapq_threshold} < 30 — reads insufficiently filtered"
    )


# ---------------------------------------------------------------------------
# Test 7: DOI present for data deposit
# ---------------------------------------------------------------------------
def test_data_deposit_doi(manifest):
    doi = manifest.get("data_deposit_doi", "")
    assert doi.startswith("10."), f"Invalid or missing DOI: '{doi}'"


# ---------------------------------------------------------------------------
# Test 8: ChIP-seq library quality — IDR and NRF
# ---------------------------------------------------------------------------
IDR_THRESHOLD = 0.05
NRF_THRESHOLD = 0.9


def test_chip_seq_library_quality(manifest):
    """IDR ≤ 0.05 and NRF > 0.9 for both H3K9ac and H3K56ac (spec §Bounty1 QC)."""
    qc = manifest["chip_seq_qc"]
    for mark in ["H3K9ac", "H3K56ac"]:
        idr = qc[mark]["idr"]
        nrf = qc[mark]["nrf"]
        assert idr <= IDR_THRESHOLD, (
            f"{mark} IDR {idr:.4f} > {IDR_THRESHOLD} — irreproducible peak calls"
        )
        assert nrf > NRF_THRESHOLD, (
            f"{mark} NRF {nrf:.4f} ≤ {NRF_THRESHOLD} — library complexity too low"
        )
