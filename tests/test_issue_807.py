"""
Pytest suite for Issue #807: Wallet integration support for Freighter and Stellar Kit.
"""

import json
from pathlib import Path
from scripts.verify_issue_807 import (
    verify_wallet_types,
    verify_freighter_adapter,
    verify_stellarkit_adapter,
    verify_sign_and_submit,
    verify_peer_dependencies,
    run_full_verification,
)

SDK_ROOT = Path("packages/soroban-lite-sdk")


def test_wallet_types_interface():
    """Verify WalletAdapter interface and SignTransactionOptions definitions."""
    types_path = SDK_ROOT / "src" / "wallets" / "types.ts"
    assert types_path.exists(), "types.ts must exist"
    code = types_path.read_text(encoding="utf-8")
    assert verify_wallet_types(code)


def test_freighter_adapter_contract():
    """Verify FreighterAdapter implementation, properties, and error guards."""
    freighter_path = SDK_ROOT / "src" / "wallets" / "freighter.ts"
    assert freighter_path.exists(), "freighter.ts must exist"
    code = freighter_path.read_text(encoding="utf-8")
    assert verify_freighter_adapter(code)
    assert "Freighter wallet extension is not installed" in code
    assert "name = \"Freighter\"" in code


def test_stellarkit_adapter_contract():
    """Verify StellarKitAdapter implementation, properties, and error guards."""
    kit_path = SDK_ROOT / "src" / "wallets" / "stellarkit.ts"
    assert kit_path.exists(), "stellarkit.ts must exist"
    code = kit_path.read_text(encoding="utf-8")
    assert verify_stellarkit_adapter(code)
    assert "Stellar Wallets Kit is not available or initialized" in code
    assert "name = \"StellarWalletsKit\"" in code


def test_sign_and_submit_lifecycle():
    """Verify SorobanClient.signAndSubmit orchestrates simulate -> sign -> send -> poll."""
    index_path = SDK_ROOT / "src" / "index.ts"
    assert index_path.exists(), "src/index.ts must exist"
    code = index_path.read_text(encoding="utf-8")
    assert verify_sign_and_submit(code)


def test_peer_dependencies_meta():
    """Verify package.json declares wallet libraries as optional peerDependencies."""
    pkg_path = SDK_ROOT / "package.json"
    assert pkg_path.exists(), "package.json must exist"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    assert verify_peer_dependencies(pkg)


def test_documentation_and_changelog():
    """Verify README.md and CHANGELOG.md are updated with wallet integration details."""
    readme_path = SDK_ROOT / "README.md"
    changelog_path = SDK_ROOT / "CHANGELOG.md"
    assert readme_path.exists()
    assert changelog_path.exists()

    readme_content = readme_path.read_text(encoding="utf-8")
    changelog_content = changelog_path.read_text(encoding="utf-8")

    assert "## Wallet Integration" in readme_content
    assert "FreighterAdapter" in readme_content
    assert "StellarKitAdapter" in readme_content
    assert "signAndSubmit" in readme_content
    assert "Wallet Integration Support" in changelog_content


def test_end_to_end_verification_summary():
    """Run full verification routine and ensure 100% check pass rate."""
    summary = run_full_verification()
    assert summary.is_valid
    assert summary.passed_checks == summary.total_checks
    assert summary.total_checks == 6
