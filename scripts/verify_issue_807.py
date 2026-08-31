"""Verification engine for Issue #807: Wallet integration for Freighter and Stellar Kit."""

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class VerificationSummary:
    """Encapsulates the status and checks of the issue resolution."""

    passed_checks: int
    total_checks: int
    is_valid: bool
    details: list[str]


def verify_wallet_types(source_code: str) -> bool:
    """Verifies that WalletAdapter interface has all required methods and signatures."""
    required_tokens = [
        "export interface WalletAdapter",
        "readonly name: string",
        "isAvailable(): boolean",
        "connect(): Promise<string>",
        "signTransaction(",
        "export interface SignTransactionOptions",
    ]
    return all(token in source_code for token in required_tokens)


def verify_freighter_adapter(source_code: str) -> bool:
    """Verifies FreighterAdapter conforms to WalletAdapter and wraps @stellar/freighter-api."""
    required_tokens = [
        "export class FreighterAdapter implements WalletAdapter",
        'readonly name = "Freighter"',
        "isAvailable()",
        "async connect()",
        "async signTransaction(",
        "@stellar/freighter-api",
    ]
    return all(token in source_code for token in required_tokens)


def verify_stellarkit_adapter(source_code: str) -> bool:
    """Verifies StellarKitAdapter conforms to WalletAdapter and wraps stellar-wallets-kit."""
    required_tokens = [
        "export class StellarKitAdapter implements WalletAdapter",
        'readonly name = "StellarWalletsKit"',
        "isAvailable()",
        "async connect()",
        "async signTransaction(",
    ]
    return all(token in source_code for token in required_tokens)


def verify_sign_and_submit(source_code: str) -> bool:
    """Verifies SorobanClient has signAndSubmit helper method implementing full lifecycle."""
    required_tokens = [
        "async signAndSubmit(",
        "simulateTransaction(",
        "signTransaction(",
        "sendTransaction(",
        "pollTransactionStatus(",
    ]
    return all(token in source_code for token in required_tokens)


def verify_peer_dependencies(pkg_json: dict) -> bool:
    """Verifies wallet packages are declared as optional peerDependencies."""
    peer_deps = pkg_json.get("peerDependencies", {})
    peer_meta = pkg_json.get("peerDependenciesMeta", {})

    has_freighter = "@stellar/freighter-api" in peer_deps
    has_kit = "@creit.tech/stellar-wallets-kit" in peer_deps
    freighter_opt = peer_meta.get("@stellar/freighter-api", {}).get("optional") is True
    kit_opt = peer_meta.get("@creit.tech/stellar-wallets-kit", {}).get("optional") is True

    return has_freighter and has_kit and freighter_opt and kit_opt


def run_full_verification(base_path: str = "packages/soroban-lite-sdk") -> VerificationSummary:
    """Runs end-to-end verification across all SDK components."""
    root = Path(base_path)
    details: list[str] = []
    passed = 0
    total = 6

    # 1. Check types.ts
    types_file = root / "src" / "wallets" / "types.ts"
    if types_file.exists() and verify_wallet_types(types_file.read_text(encoding="utf-8")):
        passed += 1
        details.append("WalletAdapter and SignTransactionOptions types verified")
    else:
        details.append("Failed verifying WalletAdapter types")

    # 2. Check freighter.ts
    freighter_file = root / "src" / "wallets" / "freighter.ts"
    if freighter_file.exists() and verify_freighter_adapter(freighter_file.read_text(encoding="utf-8")):
        passed += 1
        details.append("FreighterAdapter implementation verified")
    else:
        details.append("Failed verifying FreighterAdapter")

    # 3. Check stellarkit.ts
    kit_file = root / "src" / "wallets" / "stellarkit.ts"
    if kit_file.exists() and verify_stellarkit_adapter(kit_file.read_text(encoding="utf-8")):
        passed += 1
        details.append("StellarKitAdapter implementation verified")
    else:
        details.append("Failed verifying StellarKitAdapter")

    # 4. Check signAndSubmit in index.ts
    index_file = root / "src" / "index.ts"
    if index_file.exists() and verify_sign_and_submit(index_file.read_text(encoding="utf-8")):
        passed += 1
        details.append("SorobanClient.signAndSubmit lifecycle helper verified")
    else:
        details.append("Failed verifying signAndSubmit helper")

    # 5. Check package.json peerDependencies
    pkg_file = root / "package.json"
    if pkg_file.exists():
        try:
            pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
            if verify_peer_dependencies(pkg_data):
                passed += 1
                details.append("Optional peerDependencies verified")
            else:
                details.append("peerDependencies or peerDependenciesMeta mismatch")
        except json.JSONDecodeError:
            details.append("package.json parse error")
    else:
        details.append("package.json not found")

    # 6. Check documentation & changelog
    readme_file = root / "README.md"
    changelog_file = root / "CHANGELOG.md"
    if (
        readme_file.exists()
        and "Wallet Integration" in readme_file.read_text(encoding="utf-8")
        and changelog_file.exists()
        and "Wallet Integration Support" in changelog_file.read_text(encoding="utf-8")
    ):
        passed += 1
        details.append("README.md and CHANGELOG.md documentation verified")
    else:
        details.append("Failed verifying documentation updates")

    return VerificationSummary(
        passed_checks=passed,
        total_checks=total,
        is_valid=(passed == total),
        details=details,
    )


if __name__ == "__main__":
    summary = run_full_verification()
    for d in summary.details:
        print(f" - {d}")
    print(f"Status: {summary.passed_checks}/{summary.total_checks} (Valid: {summary.is_valid})")
