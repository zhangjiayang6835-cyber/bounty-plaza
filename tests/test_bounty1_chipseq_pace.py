"""Acceptance and unit tests for Bounty #1: ChIP-seq & Methylation PACE Pipeline (#829 - $15,000 USDC).
Validates all acceptance criteria from upstream mister3ai-cmyk/ngp-sovereign-synesis-bounties#1.
Compatible with both pytest and python -m unittest.
"""

import json
from pathlib import Path
import unittest

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


class TestBounty1ChIPSeqPace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipeline = ChIPSeqPacePipeline(results_dir="results")
        cls.manifest = pipeline.produce_manifest()

    def test_dunedinpace_intercept(self):
        """Verify DunedinPACE intercept == 51.024577 ± 0.001."""
        intercept = self.manifest["dunedinpace"]["intercept"]
        self.assertAlmostEqual(
            intercept,
            REFERENCE_INTERCEPT,
            delta=INTERCEPT_TOLERANCE,
            msg=f"DunedinPACE intercept {intercept:.6f} deviates from reference {REFERENCE_INTERCEPT}",
        )

    def test_h3k9ac_pearson_r(self):
        """Verify Pearson r > 0.92 for H3K9ac vs DunedinPACE."""
        r = self.manifest["correlations"]["H3K9ac_vs_DunedinPACE"]["pearson_r"]
        self.assertGreater(
            r,
            MIN_PEARSON_R,
            msg=f"H3K9ac → DunedinPACE Pearson r = {r:.4f}, required > {MIN_PEARSON_R}",
        )

    def test_h3k56ac_pearson_r(self):
        """Verify Pearson r > 0.92 for H3K56ac vs DunedinPACE."""
        r = self.manifest["correlations"]["H3K56ac_vs_DunedinPACE"]["pearson_r"]
        self.assertGreater(
            r,
            MIN_PEARSON_R,
            msg=f"H3K56ac → DunedinPACE Pearson r = {r:.4f}, required > {MIN_PEARSON_R}",
        )

    def test_peak_calling_fdr(self):
        """Verify peak-calling FDR < 0.05."""
        fdr = self.manifest["peak_calling"]["fdr"]
        self.assertLess(fdr, FDR_MAX, msg=f"Peak-calling FDR {fdr} >= {FDR_MAX}")

    def test_mapq_filter(self):
        """Verify alignment MAPQ threshold >= 30."""
        mapq = self.manifest["alignment"]["mapq_threshold"]
        self.assertGreaterEqual(
            mapq, MAPQ_MIN, msg=f"MAPQ threshold {mapq} < {MAPQ_MIN}"
        )

    def test_data_deposit_doi(self):
        """Verify DOI is present and valid."""
        doi = self.manifest.get("data_deposit_doi", "")
        self.assertTrue(
            doi.startswith("10."), msg=f"Invalid or missing DOI: '{doi}'"
        )

    def test_chip_seq_library_quality(self):
        """Verify IDR <= 0.05 and NRF > 0.90 for both marks."""
        qc = self.manifest["chip_seq_qc"]
        for mark in ["H3K9ac", "H3K56ac"]:
            idr = qc[mark]["idr"]
            nrf = qc[mark]["nrf"]
            self.assertLessEqual(
                idr, IDR_MAX, msg=f"{mark} IDR {idr:.4f} > {IDR_MAX}"
            )
            self.assertGreater(
                nrf, NRF_MIN, msg=f"{mark} NRF {nrf:.4f} <= {NRF_MIN}"
            )

    def test_pearson_calculation_edge_cases(self):
        """Verify Pearson correlation calculation under edge cases."""
        # Degenerate zero variance
        self.assertEqual(calculate_pearson_r([1.0, 1.0], [2.0, 3.0]), 0.0)
        # Perfect positive correlation
        self.assertAlmostEqual(
            calculate_pearson_r([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]), 1.0
        )
        # Perfect negative correlation
        self.assertAlmostEqual(
            calculate_pearson_r([1.0, 2.0, 3.0], [6.0, 4.0, 2.0]), -1.0
        )

    def test_qc_filter_mapq(self):
        """Verify ChIPSeqQCFilter threshold logic."""
        qc = ChIPSeqQCFilter(mapq_threshold=30)
        self.assertTrue(qc.validate_mapq(30))
        self.assertTrue(qc.validate_mapq(42))
        self.assertFalse(qc.validate_mapq(29))
        self.assertEqual(qc.calculate_nrf(100, 95), 0.95)


if __name__ == "__main__":
    unittest.main()
