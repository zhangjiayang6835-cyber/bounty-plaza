"""Unit tests for Memanto + OKF Migration Showcase & Freedom Loop Engine.
Resolves Issue #665: [BOUNTY $200] The Great Memory Migration: Own Your Agentic Memory with Memanto + OKF.
"""

import json
import os
import pytest
from scripts.memanto_okf_migration_showcase import (
    MemantoOKFMigrationShowcase,
    OKFMemoryItem,
    MigrationTelemetry,
    OKF_VERSION,
)


@pytest.fixture
def showcase():
    return MemantoOKFMigrationShowcase()


@pytest.fixture
def sample_proprietary_memories():
    return [
        {
            "id": "mem_pref_001",
            "title": "Zero Negotiation Crypto Pivot",
            "text": "User strictly prioritizes autonomous 24/7 crypto and web3 revenue operations.",
            "category": "preference",
            "confidence": 0.98,
            "entities": ["crypto", "web3", "arbitrage"],
            "custom_metadata_secret_engine": "proprietary_vector_v4",
            "internal_run_id": 9942,
        },
        {
            "uuid": "mem_arch_002",
            "topic": "Multi-Base Spot Portfolio Liquidity",
            "content": "Binance triangular arbitrage running across multi-base pairs with BNB fee optimization.",
            "type": "architecture",
            "score": 0.95,
            "tags": ["binance", "spot", "liquidity"],
            " proprietary_flag": True,
        }
    ]


def test_ingest_proprietary_memories_lossless(showcase, sample_proprietary_memories):
    """Verifies ingestion maps standard fields and captures 100% of unmapped proprietary attributes."""
    count = showcase.ingest_proprietary_memories(sample_proprietary_memories, platform_name="crewai")
    assert count == 2
    assert len(showcase.memories) == 2

    m1 = showcase.memories["mem_pref_001"]
    assert m1.title == "Zero Negotiation Crypto Pivot"
    assert m1.category == "preference"
    assert m1.confidence == 0.98
    assert "crypto" in m1.entities
    # Unmapped vendor fields preserved losslessly
    assert m1.unmapped_fields.get("custom_metadata_secret_engine") == "proprietary_vector_v4"
    assert m1.unmapped_fields.get("internal_run_id") == 9942


def test_okf_markdown_serialization(showcase, sample_proprietary_memories):
    """Verifies that OKF Markdown formatting contains valid YAML frontmatter and clean Markdown body."""
    showcase.ingest_proprietary_memories(sample_proprietary_memories, platform_name="crewai")
    m1 = showcase.memories["mem_pref_001"]
    md = m1.to_okf_markdown()

    assert f"okf_version: \"{OKF_VERSION}\"" in md
    assert "id: \"mem_pref_001\"" in md
    assert "Zero Negotiation Crypto Pivot" in md
    assert "# Zero Negotiation Crypto Pivot" in md
    assert "User strictly prioritizes" in md


def test_export_okf_bundle_directory(showcase, sample_proprietary_memories, tmp_path):
    """Verifies bundle export creates browsable INDEX.md and individual memory files."""
    showcase.ingest_proprietary_memories(sample_proprietary_memories, platform_name="letta")
    bundle_dir = str(tmp_path / "okf_memory_bundle")
    created_files = showcase.export_okf_bundle(bundle_dir)

    assert len(created_files) == 3  # INDEX.md + 2 memories
    assert os.path.exists(os.path.join(bundle_dir, "INDEX.md"))
    assert os.path.exists(os.path.join(bundle_dir, "mem_pref_001.md"))

    # Check INDEX.md contents
    with open(os.path.join(bundle_dir, "INDEX.md"), "r", encoding="utf-8") as f:
        index_content = f.read()
        assert "Agent Memory Wiki" in index_content
        assert "Total Portable Memories: 2" in index_content


def test_migration_telemetry_metrics(showcase, sample_proprietary_memories):
    """Verifies zero data loss and calculated token savings telemetry."""
    showcase.ingest_proprietary_memories(sample_proprietary_memories, platform_name="supermemory")
    raw_payload_bytes = len(json.dumps(sample_proprietary_memories).encode("utf-8"))
    telemetry = showcase.calculate_telemetry(raw_payload_bytes)

    assert telemetry.total_memories == 2
    assert telemetry.unmapped_data_loss_pct == 0.0
    assert telemetry.portability_score == 100.0
    assert telemetry.estimated_token_savings_pct > 0.0
