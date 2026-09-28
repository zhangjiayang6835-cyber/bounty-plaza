"""
fee_ledger.py — Production Implementation for Issue #1660 (Grainlify & Bounty Plaza)
Records factual network fee (fee_lamports) alongside conservative capped fee_micro estimate.

Key Requirements:
1. Database Schema & Migration:
   - Forward-only nullable integer `fee_lamports` added to inference_calls.
   - Existing records retain valid state (fee_lamports is NULL).
2. Conservative Budget Invariant:
   - fee_micro continues using the ceiling price ($400/SOL) to protect lifetime budgets.
   - fee_lamports stores the exact confirmed network fee from the transaction.
3. Backward Compatibility:
   - When fee_lamports is absent, omitted, or NULL, settlement functions correctly.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


SOL_USD_CEILING_PRICE = 400.0  # Conservative fixed SOL price ($400)
LAMPORTS_PER_SOL = 1_000_000_000
MICRO_PER_USD = 1_000_000


def lamports_to_micro_ceil(lamports: int, sol_usd_price: float = SOL_USD_CEILING_PRICE) -> int:
    """Convert lamports to micro-USD with ceiling to ensure budget never under-counts.
    1 SOL = 1e9 lamports; micro-USD = lamports * price * 1e6 / 1e9 = (lamports * price) / 1000.
    """
    if lamports <= 0:
        return 0
    return math.ceil((lamports * sol_usd_price) / 1000)


@dataclass
class PayResult:
    """Outcome of an on-chain transaction execution."""
    kind: str
    payer_wallet: str
    signature: str
    amount_micro: int
    fee_micro: int
    fee_lamports: Optional[int] = None
    error: Optional[str] = None


@dataclass
class SpendEntry:
    """Represents a budget ledger entry."""
    id: str
    phase: str
    kind: str
    amount_micro: int
    fee_micro: int = 0
    fee_lamports: Optional[int] = None
    status: str = "reserved"
    tx_signature: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SpendLedgerDB:
    """SQLite-backed spend ledger supporting forward-only migration for fee_lamports."""

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize base schema prior to migration."""
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS inference_calls (
                    id TEXT PRIMARY KEY,
                    phase TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    amount_micro INTEGER NOT NULL,
                    fee_micro INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    tx_signature TEXT,
                    created_at TEXT NOT NULL
                );
            """)

    def apply_migration_0011(self) -> bool:
        """Forward-only migration adding fee_lamports nullable column."""
        cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(inference_calls)")}
        if "fee_lamports" not in cols:
            with self.conn:
                self.conn.execute("ALTER TABLE inference_calls ADD COLUMN fee_lamports INTEGER DEFAULT NULL")
            return True
        return False

    def reserve(self, entry_id: str, phase: str, kind: str, amount_micro: int) -> SpendEntry:
        """Reserve budget before executing inference call."""
        entry = SpendEntry(id=entry_id, phase=phase, kind=kind, amount_micro=amount_micro, status="reserved")
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO inference_calls (id, phase, kind, amount_micro, fee_micro, status, created_at)
                VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (entry.id, entry.phase, entry.kind, entry.amount_micro, entry.status, entry.created_at)
            )
        return entry

    def settle(self, entry_id: str, amount_micro: int, fee_micro: int,
               fee_lamports: Optional[int] = None, tx_signature: Optional[str] = None) -> SpendEntry:
        """Settle confirmed transaction recording both capped fee_micro and factual fee_lamports."""
        cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(inference_calls)")}
        has_lamports = "fee_lamports" in cols

        with self.conn:
            if has_lamports:
                self.conn.execute(
                    """
                    UPDATE inference_calls
                    SET amount_micro = ?, fee_micro = ?, fee_lamports = ?, tx_signature = ?, status = 'settled'
                    WHERE id = ?
                    """,
                    (amount_micro, fee_micro, fee_lamports, tx_signature, entry_id)
                )
            else:
                self.conn.execute(
                    """
                    UPDATE inference_calls
                    SET amount_micro = ?, fee_micro = ?, tx_signature = ?, status = 'settled'
                    WHERE id = ?
                    """,
                    (amount_micro, fee_micro, tx_signature, entry_id)
                )

        row = self.conn.execute("SELECT * FROM inference_calls WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            raise ValueError(f"Entry {entry_id} not found")

        return SpendEntry(
            id=row["id"],
            phase=row["phase"],
            kind=row["kind"],
            amount_micro=row["amount_micro"],
            fee_micro=row["fee_micro"],
            fee_lamports=row["fee_lamports"] if "fee_lamports" in row.keys() else None,
            status=row["status"],
            tx_signature=row["tx_signature"],
            created_at=row["created_at"]
        )

    def get_entry(self, entry_id: str) -> Optional[SpendEntry]:
        """Retrieve entry by ID."""
        row = self.conn.execute("SELECT * FROM inference_calls WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return None
        return SpendEntry(
            id=row["id"],
            phase=row["phase"],
            kind=row["kind"],
            amount_micro=row["amount_micro"],
            fee_micro=row["fee_micro"],
            fee_lamports=row["fee_lamports"] if "fee_lamports" in row.keys() else None,
            status=row["status"],
            tx_signature=row["tx_signature"],
            created_at=row["created_at"]
        )

    def close(self):
        self.conn.close()
