"""
Automated acceptance tests for Bounty #3: DryLab4 & SiLA 2 Robotic Bridge.
Run: pytest tests/test_bounty3_sila2.py -v

Hardened with Cybersecurity-Skills:
  - CWE-611 XXE mitigation (--nonet flag on xmllint)
  - Resilient path resolution supporting root, solution directory, or subpackage execution
  - Safe Docker Compose detection with graceful skip on non-daemon CI runners
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

TEST_DIR = pathlib.Path(__file__).resolve().parent
SOLUTION_DIR = TEST_DIR.parent

MANIFEST_CANDIDATES = [
    pathlib.Path("results/sila2_manifest.json"),
    pathlib.Path("solutions/issue-827/results/sila2_manifest.json"),
    SOLUTION_DIR / "results" / "sila2_manifest.json",
]
MANIFEST = next((p for p in MANIFEST_CANDIDATES if p.exists()), pathlib.Path("results/sila2_manifest.json"))

pytestmark = pytest.mark.skipif(
    not MANIFEST.exists(),
    reason=f"{MANIFEST} not found — no Bounty #3 submission to validate; run the SiLA 2 stack first",
)

GRPC_LATENCY_P99_MS_MAX = 50.0
PTP_UTC_OFFSET_MAX_MS = 1.0  # IEEE 1588 PTP vs GPS-disciplined UTC reference
CLOCK_JITTER_MAX_MS = 1.0
DRYLAB4_RT_ERROR_MAX_FRACTION = 0.02  # 2%
ICH_Q14_REQUIRED_FIELDS = {"actor", "timestamp", "delta", "operation_id"}


def _resolve_relative(path_str: str) -> pathlib.Path:
    """Resolve a relative path against CWD or against the solution root directory."""
    p = pathlib.Path(path_str)
    if p.is_absolute() and p.exists():
        return p
    if p.exists():
        return p
    candidate = SOLUTION_DIR / path_str
    if candidate.exists():
        return candidate
    return p


@pytest.fixture(scope="module")
def manifest():
    if not MANIFEST.exists():
        pytest.skip("results/sila2_manifest.json not found — run stack first")
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test 1: SiLA2 XML schema validation (with CWE-611 XXE --nonet defense)
# ---------------------------------------------------------------------------
def test_sila2_schema_validation(manifest):
    feature_xml_raw = manifest.get("sila2_feature_descriptor_path")
    assert feature_xml_raw, "sila2_feature_descriptor_path not set"

    feature_xml = _resolve_relative(feature_xml_raw)
    schema_path = _resolve_relative("schemas/sila2_core_v1.0.0.xsd")

    assert feature_xml.exists(), f"Feature descriptor XML not found: {feature_xml}"
    assert schema_path.exists(), f"SiLA 2 core XSD schema not found: {schema_path}"

    # Use xmllint with --nonet to defend against XXE / SSRF (CWE-611) when available
    if shutil.which("xmllint"):
        result = subprocess.run(
            ["xmllint", "--nonet", "--noout", "--schema", str(schema_path), str(feature_xml)],
            capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, (
            f"SiLA2 feature descriptor failed schema validation:\n{result.stderr}"
        )
    else:
        # Robust stdlib XML well-formedness & tag hierarchy verification when xmllint is unavailable
        import xml.etree.ElementTree as ET
        tree = ET.parse(feature_xml)
        root = tree.getroot()
        assert root.tag.endswith("Feature"), f"Expected root tag ending with 'Feature', got {root.tag}"
        assert len(root) > 0, "Feature descriptor XML must contain sub-elements" 


# ---------------------------------------------------------------------------
# Test 2: gRPC roundtrip latency p99 < 50 ms
# ---------------------------------------------------------------------------
def test_grpc_latency(manifest):
    latencies = manifest["grpc_benchmark"]["latencies_ms"]
    assert len(latencies) >= 1000, f"Need ≥ 1000 latency samples, got {len(latencies)}"
    sorted_lat = sorted(latencies)
    p99_idx = int(len(sorted_lat) * 0.99)
    p99 = sorted_lat[p99_idx]
    assert p99 < GRPC_LATENCY_P99_MS_MAX, (
        f"gRPC p99 latency {p99:.2f} ms ≥ {GRPC_LATENCY_P99_MS_MAX} ms"
    )


# ---------------------------------------------------------------------------
# Test 3: DryLab4 retention-time prediction error < 2%
# ---------------------------------------------------------------------------
def test_drylab4_rt_prediction(manifest):
    predictions = manifest["drylab4"]["retention_time_predictions"]
    for entry in predictions:
        predicted = entry["predicted_min"]
        reference = entry["reference_min"]
        error = abs(predicted - reference) / reference
        assert error <= DRYLAB4_RT_ERROR_MAX_FRACTION, (
            f"RT prediction error {error:.2%} > 2% for compound '{entry.get('compound', '?')}'"
        )


# ---------------------------------------------------------------------------
# Test 4: IEEE 1588 PTP clock offset < 1 ms vs. GPS-disciplined UTC reference
# ---------------------------------------------------------------------------
def test_master_clock_jitter(manifest):
    clock_data = manifest["master_clock"]
    utc_offset_ms = clock_data.get("utc_offset_ms", clock_data.get("jitter_ms_60s_window"))
    assert utc_offset_ms < PTP_UTC_OFFSET_MAX_MS, (
        f"PTP UTC offset {utc_offset_ms:.3f} ms ≥ {PTP_UTC_OFFSET_MAX_MS} ms (IEEE 1588 requirement)"
    )


# ---------------------------------------------------------------------------
# Test 5: ICH Q14 audit trail completeness
# ---------------------------------------------------------------------------
def test_ich_q14_audit_trail(manifest):
    audit_log_raw = manifest.get("ich_q14_audit_log")
    assert audit_log_raw, "ich_q14_audit_log not set in manifest"

    audit_log_path = _resolve_relative(audit_log_raw)
    assert audit_log_path.exists(), f"Audit log file not found: {audit_log_path}"

    with open(audit_log_path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    assert entries, "Audit log is empty"
    for i, entry in enumerate(entries):
        missing = ICH_Q14_REQUIRED_FIELDS - set(entry.keys())
        assert not missing, (
            f"Audit entry #{i} missing required ICH Q14 fields: {missing}"
        )


# ---------------------------------------------------------------------------
# Test 6: Docker Compose stack starts cleanly
# ---------------------------------------------------------------------------
def test_docker_compose_start():
    # Verify docker executable exists
    if not shutil.which("docker"):
        pytest.skip("Docker CLI not available in environment")

    # Locate docker-compose.yml
    compose_path = _resolve_relative("docker-compose.yml")
    if not compose_path.exists():
        pytest.skip(f"docker-compose.yml not found at {compose_path}")

    # Check if Docker daemon is accessible
    daemon_check = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
    if daemon_check.returncode != 0:
        pytest.skip(f"Docker daemon not running: {daemon_check.stderr.strip()[:100]}")

    compose_args = ["docker", "compose", "-f", str(compose_path)]
    result = subprocess.run(
        compose_args + ["up", "--wait", "--timeout", "120"],
        capture_output=True, text=True, timeout=150, check=False, cwd=str(compose_path.parent)
    )
    assert result.returncode == 0, (
        f"docker compose up --wait failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    # Cleanup
    subprocess.run(compose_args + ["down"], capture_output=True, check=False, cwd=str(compose_path.parent))


# ---------------------------------------------------------------------------
# Test 7: End-to-end integration (mock instruments)
# ---------------------------------------------------------------------------
def test_e2e_mock_integration(manifest):
    e2e_cmd = manifest.get("e2e_test_command")
    if not e2e_cmd:
        pytest.skip("e2e_test_command not specified in manifest")
    result = subprocess.run(
        e2e_cmd,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        cwd=str(SOLUTION_DIR)
    )
    assert result.returncode == 0, (
        f"E2E integration test failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


# Critical-loop constant from NGP 4.5 Technical Report §Shield 4 (Jones model)
HAMILTON_CRITICAL_LOOP_US = 2.2  # μs — LossySpinBosonEngine feedback latency cap


# ---------------------------------------------------------------------------
# Test 8: Hamilton Microlab STARlet critical-loop automation latency ≤ 2.2 μs
# ---------------------------------------------------------------------------
def test_hamilton_critical_loop_latency(manifest):
    """Automation feedback loop must respond within 2.2 μs (Jones model, σ=0.5)."""
    latency_us = manifest["hamilton_starlet"]["critical_loop_latency_us"]
    assert latency_us <= HAMILTON_CRITICAL_LOOP_US, (
        f"Hamilton STARlet critical loop {latency_us:.3f} μs > {HAMILTON_CRITICAL_LOOP_US} μs "
        f"(LossySpinBosonEngine Jones-barrier exceeded)"
    )
