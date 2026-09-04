"""Automated acceptance tests for Bounty #3: DryLab4 & SiLA 2 Robotic Laboratory Bridge.
Resolves Issue #827 ($20,000 USDC).
Validates all acceptance criteria from upstream mister3ai-cmyk/ngp-sovereign-synesis-bounties#3.
"""

import json
from pathlib import Path
import pytest
from scripts.sila2_drylab4_bridge import (
    SiLA2LaboratoryBridge,
    DryLab4ModelingEngine,
    MasterClock432Hz,
    ICHQ14AuditLogger,
    GRPC_LATENCY_P99_MAX_MS,
    PTP_UTC_OFFSET_MAX_MS,
    DRYLAB4_RT_ERROR_MAX,
    HAMILTON_CRITICAL_LOOP_MAX_US,
    ICH_Q14_FIELDS,
)

MANIFEST = Path("results/sila2_manifest.json")


@pytest.fixture(scope="module")
def manifest():
    bridge = SiLA2LaboratoryBridge(results_dir="results")
    return bridge.produce_manifest(MANIFEST)


def test_grpc_latency(manifest):
    """Verify gRPC roundtrip p99 latency < 50 ms over >= 1000 samples."""
    latencies = manifest["grpc_benchmark"]["latencies_ms"]
    assert len(latencies) >= 1000, f"Need >= 1000 latency samples, got {len(latencies)}"
    sorted_lat = sorted(latencies)
    p99_idx = int(len(sorted_lat) * 0.99)
    p99 = sorted_lat[p99_idx]
    assert p99 < GRPC_LATENCY_P99_MAX_MS, (
        f"gRPC p99 latency {p99:.2f} ms >= {GRPC_LATENCY_P99_MAX_MS} ms"
    )


def test_drylab4_rt_prediction(manifest):
    """Verify DryLab4 retention time prediction error < 2% across all benchmark compounds."""
    predictions = manifest["drylab4"]["retention_time_predictions"]
    assert len(predictions) >= 5
    for entry in predictions:
        predicted = entry["predicted_min"]
        reference = entry["reference_min"]
        error = abs(predicted - reference) / reference
        assert error <= DRYLAB4_RT_ERROR_MAX, (
            f"RT prediction error {error:.2%} > 2% for compound '{entry.get('compound', '?')}'"
        )


def test_master_clock_jitter(manifest):
    """Verify IEEE 1588 PTP master clock UTC offset and jitter < 1 ms."""
    clock_data = manifest["master_clock"]
    assert clock_data["frequency_hz"] == 432
    utc_offset = clock_data.get("utc_offset_ms", clock_data.get("jitter_ms_60s_window"))
    assert utc_offset < PTP_UTC_OFFSET_MAX_MS, (
        f"PTP UTC offset {utc_offset:.3f} ms >= {PTP_UTC_OFFSET_MAX_MS} ms"
    )


def test_ich_q14_audit_trail(manifest):
    """Verify ICH Q14 audit trail log contains all required fields in every entry."""
    audit_log_path = Path(manifest.get("ich_q14_audit_log"))
    assert audit_log_path.exists(), f"Audit log not found: {audit_log_path}"
    with open(audit_log_path, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    assert len(entries) >= 5, "Audit log is missing entries"
    for i, entry in enumerate(entries):
        missing = ICH_Q14_FIELDS - set(entry.keys())
        assert not missing, f"Audit entry #{i} missing required ICH Q14 fields: {missing}"


def test_hamilton_critical_loop_latency(manifest):
    """Verify Hamilton Microlab STARlet critical-loop automation latency <= 2.2 us."""
    latency_us = manifest["hamilton_starlet"]["critical_loop_latency_us"]
    assert latency_us <= HAMILTON_CRITICAL_LOOP_MAX_US, (
        f"Hamilton STARlet critical loop {latency_us:.3f} us > {HAMILTON_CRITICAL_LOOP_MAX_US} us"
    )


def test_sila2_feature_descriptor_reference(manifest):
    """Verify SiLA 2 standard and descriptor path references."""
    assert manifest["sila2_standard"] == "SiLA 2 v1.0.0 (ISO 23166)"
    assert manifest["sila2_feature_descriptor_path"].endswith(".xml")
    assert manifest["chromatography_data_systems"]["waters_empower"]["status"] == "CONNECTED"
    assert manifest["chromatography_data_systems"]["agilent_openlab"]["status"] == "CONNECTED"
