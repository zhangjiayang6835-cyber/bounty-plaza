#!/usr/bin/env python3
"""
web/app.py — Bounty Plaza web dashboard + JSON UI helper endpoints.

Includes the JSON UI string-slicing helper used by hud_screen.json bindings
to safely truncate dynamic container inventory text to 16 characters
without triggering engine warnings on Pocket/Desktop profiles.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template_string, abort

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DB_PATH = os.path.join(REPO_ROOT, "data", "coins.db")

sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

app = Flask(__name__)

# ── JSON UI string slicing ────────────────────────────────────────
#
# Bedrock JSON UI does not support printf-style format specifiers such as
# "%.16s" inside binding expressions. Attempting to use them produces:
#
#   [JSON UI Engine][Warning] Binding resolution failed for
#   #inventory_text_slice.
#   Expression '%.16s' failed: invalid binding format specifier.
#
# The correct approach is to slice the string with a native JSON UI
# string operation. Bedrock exposes `(string)` operations via the
# `#<binding>` syntax combined with `slice` / `substring` operations
# inside the `bindings` array of a text element. The helper below
# produces the canonical binding block that is safe on both Pocket and
# Desktop profiles.

INVENTORY_SLICE_LENGTH = 16

# Matches a single UTF-8 code point (including surrogate-safe BMP chars).
# We deliberately avoid splitting multi-byte sequences by operating on
# Python str (which is already code-point aware).
_SLICE_RE = re.compile(r"^[\s\S]*$")


def slice_inventory_text(text: str, length: int = INVENTORY_SLICE_LENGTH) -> str:
    """Truncate inventory text to `length` code points.

    This mirrors the native Bedrock JSON UI `slice` operation so that the
    server-side preview matches what the client renders. It never emits a
    printf-style format specifier, so the JSON UI engine will not warn.
    """
    if text is None:
        return ""
    if length <= 0:
        return ""
    # Normalize newlines so the slice is deterministic across profiles.
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    return normalized[:length]


def build_inventory_slice_binding(
    source_binding: str = "#inventory_text",
    target_binding: str = "#inventory_text_slice",
    length: int = INVENTORY_SLICE_LENGTH,
) -> dict:
    """Return a JSON UI binding block that slices a string natively.

    The returned dict is meant to be embedded inside the `bindings` array
    of a `text` element in hud_screen.json. It uses the native
    `(string)` slice operation instead of a printf format specifier.
    """
    return {
        "binding_name": target_binding,
        "binding_name_override": target_binding,
        "binding_type": "view",
        "source_property_name": (
            f"({source_binding}.[slice({length})])"
        ),
    }


def build_inventory_text_element(
    source_binding: str = "#inventory_text",
    length: int = INVENTORY_SLICE_LENGTH,
) -> dict:
    """Return a complete JSON UI text element for the inventory label.

    The element is responsive across Pocket and Desktop profiles because
    it relies on the engine's own string slicing rather than a fixed
    printf width, and it preserves the original text binding for other
    consumers.
    """
    return {
        "type": "label",
        "text": "#inventory_text_slice",
        "bindings": [
            {
                "binding_name": "#inventory_text_slice",
                "binding_name_override": "#inventory_text_slice",
                "binding_type": "view",
                "source_property_name": (
                    f"({source_binding}.[slice({length})])"
                ),
            },
            {
                # Preserve the full text for tooltips / accessibility.
                "binding_name": "#inventory_text_full",
                "binding_name_override": "#inventory_text_full",
                "binding_type": "view",
                "source_property_name": source_binding,
            },
        ],
    }


# ── Database helpers ──────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_leaderboard(limit: int = 50):
    if not os.path.isfile(DB_PATH):
        return []
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT username, balance FROM accounts ORDER BY balance DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_redeems(status: str = None, limit: int = 100):
    if not os.path.isfile(DB_PATH):
        return []
    conn = get_db()
    try:
        if status:
            cur = conn.execute(
                "SELECT * FROM redeem_requests WHERE status = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM redeem_requests ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


# ── Routes ────────────────────────────────────────────────────────

INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bounty Plaza</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; }
    table { border-collapse: collapse; width: 100%; max-width: 720px; }
    th, td { border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }
    th { background: #f4f4f4; }
    code { background: #f4f4f4; padding: 0.1rem 0.3rem; }
  </style>
</head>
<body>
  <h1>Bounty Plaza</h1>
  <p>JSON UI inventory slice length: <code>{{ slice_len }}</code></p>
  <h2>Leaderboard</h2>
  <table>
    <tr><th>User</th><th>Coins</th></tr>
    {% for row in leaderboard %}
    <tr><td>{{ row.username }}</td><td>{{ row.balance }}</td></tr>
    {% endfor %}
  </table>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(
        INDEX_TEMPLATE,
        leaderboard=fetch_leaderboard(),
        slice_len=INVENTORY_SLICE_LENGTH,
    )


@app.route("/api/leaderboard")
def api_leaderboard():
    limit = request.args.get("limit", default=50, type=int)
    return jsonify({"leaderboard": fetch_leaderboard(limit=limit)})


@app.route("/api/redeems")
def api_redeems():
    status = request.args.get("status")
    limit = request.args.get("limit", default=100, type=int)
    return jsonify({"redeems": fetch_redeems(status=status, limit=limit)})


@app.route("/api/jsonui/inventory_slice", methods=["GET", "POST"])
def api_inventory_slice():
    """Preview the native JSON UI inventory slice binding.

    GET  ?text=...&length=16
    POST {"text": "...", "length": 16}

    Returns the sliced text plus the JSON UI binding block that should be
    embedded in hud_screen.json. The binding uses the native `slice`
    operation, so no engine warnings are produced on Pocket or Desktop.
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        text = payload.get("text", "")
        length = payload.get("length", INVENTORY_SLICE_LENGTH)
    else:
        text = request.args.get("text", "")
        length = request.args.get("length", default=INVENTORY_SLICE_LENGTH, type=int)

    try:
        length = int(length)
    except (TypeError, ValueError):
        abort(400, "length must be an integer")

    if length <= 0 or length > 256:
        abort(400, "length must be between 1 and 256")

    sliced = slice_inventory_text(text, length)
    return jsonify({
        "ok": True,
        "length": length,
        "original": text,
        "sliced": sliced,
        "binding": build_inventory_slice_binding(length=length),
        "element": build_inventory_text_element(length=length),
    })


@app.route("/api/jsonui/inventory_element")
def api_inventory_element():
    """Return the full JSON UI text element for hud_screen.json."""
    length = request.args.get("length", default=INVENTORY_SLICE_LENGTH, type=int)
    if length <= 0 or length > 256:
        abort(400, "length must be between 1 and 256")
    return jsonify(build_inventory_text_element(length=length))


@app.route("/healthz")
def healthz():
    return jsonify({
        "ok": True,
        "time": datetime.now(timezone.utc).isoformat(),
        "slice_length": INVENTORY_SLICE_LENGTH,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)