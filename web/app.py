#!/usr/bin/env python3
"""
web/app.py — Bounty Plaza Web Dashboard

Flask application serving the bounty plaza dashboard, coin ledger,
and redemption status. Also exposes the deep recursive generic type
solver used by src/types/state.ts consumers via a JSON endpoint so
that the TypeScript compiler no longer needs to instantiate the
excessively deep conditional type at build time.

The TypeScript side (src/types/state.ts) previously declared:

    type DeepInfiniteResolve<T> =
        T extends StateGraphNode<infer N>
            ? DeepInfiniteResolve<N>
            : T;

which triggered TS2589 ("Type instantiation is excessively deep and
possibly infinite") on cyclic StateGraphNode topologies. The fix is to
move the bidirectional state unwrapping into a runtime resolver here
and have the TS side consume a bounded, non-recursive type. This module
implements that resolver with an explicit visited-set so cyclic graphs
terminate, and exposes it over HTTP for the build pipeline.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template_string

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DB_PATH = os.path.join(REPO_ROOT, "data", "coins.db")

app = Flask(__name__)

# ── Deep recursive generic type solver ──────────────────────────────
#
# Mirrors the semantics of DeepInfiniteResolve<T> from
# src/types/state.ts but performs the unwrapping at runtime with an
# explicit visited set, so cyclic StateGraphNode topologies terminate
# instead of blowing the compiler's recursion budget.
#
# A StateGraphNode is represented as a dict:
#   {
#     "kind": "StateGraphNode",
#     "name": "<node name>",
#     "next": <StateGraphNode | null>,
#     "prev": <StateGraphNode | null>,
#     "payload": <any>
#   }
#
# The resolver walks both `next` and `prev` edges (bidirectional
# unwrapping) and returns a flat, cycle-free list of resolved nodes in
# deterministic order.

MAX_RESOLVE_DEPTH = 4096


class ResolveError(Exception):
    """Raised when a state graph cannot be resolved."""


def _is_node(value) -> bool:
    return isinstance(value, dict) and value.get("kind") == "StateGraphNode"


def _node_key(node: dict) -> str:
    """Stable identity for a node, used for cycle detection."""
    name = node.get("name")
    if isinstance(name, str) and name:
        return f"name:{name}"
    # Fall back to structural identity via sorted payload repr.
    try:
        payload = json.dumps(node.get("payload"), sort_keys=True, default=str)
    except (TypeError, ValueError):
        payload = repr(node.get("payload"))
    return f"anon:{payload}"


def deep_infinite_resolve(root, max_depth: int = MAX_RESOLVE_DEPTH):
    """
    Bidirectional, cycle-safe unwrapping of a StateGraphNode topology.

    Returns a list of resolved node dicts in breadth-first order,
    starting from `root`. Each node appears exactly once even if the
    graph contains cycles reachable through `next`/`prev` edges.

    Raises ResolveError if the graph exceeds `max_depth` distinct nodes
    (guards against pathological inputs) or if a non-node value is
    passed as root.
    """
    if root is None:
        return []
    if not _is_node(root):
        raise ResolveError(
            f"deep_infinite_resolve: root is not a StateGraphNode: {type(root).__name__}"
        )

    resolved = []
    seen = set()
    queue = [root]
    head = 0

    while head < len(queue):
        node = queue[head]
        head += 1

        if not _is_node(node):
            continue

        key = _node_key(node)
        if key in seen:
            continue
        seen.add(key)

        if len(resolved) >= max_depth:
            raise ResolveError(
                f"deep_infinite_resolve: exceeded max_depth={max_depth} "
                f"(possible unbounded topology)"
            )

        resolved.append({
            "name": node.get("name"),
            "payload": node.get("payload"),
            "has_next": _is_node(node.get("next")),
            "has_prev": _is_node(node.get("prev")),
        })

        nxt = node.get("next")
        prv = node.get("prev")
        if _is_node(nxt):
            queue.append(nxt)
        if _is_node(prv):
            queue.append(prv)

    return resolved


def unwrap_state_graph(graph):
    """
    Entry point used by the build pipeline. Accepts either a single
    root node or a list of roots and returns the fully unwrapped,
    cycle-free node list.
    """
    if graph is None:
        return []
    if isinstance(graph, list):
        out = []
        seen = set()
        for root in graph:
            for entry in deep_infinite_resolve(root):
                key = entry.get("name") or json.dumps(entry, sort_keys=True, default=str)
                if key in seen:
                    continue
                seen.add(key)
                out.append(entry)
        return out
    return deep_infinite_resolve(graph)


# ── Database helpers ────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_query(sql, params=()):
    try:
        conn = get_db()
        try:
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    except sqlite3.Error:
        return []


# ── Routes ──────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Bounty Plaza</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; background: #0f1115; color: #e6e6e6; }
    h1 { color: #7ee787; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { border: 1px solid #30363d; padding: 0.5rem 0.75rem; text-align: left; }
    th { background: #161b22; }
    .muted { color: #8b949e; }
  </style>
</head>
<body>
  <h1>Bounty Plaza</h1>
  <p class="muted">Generated {{ now }}</p>
  <h2>Accounts</h2>
  <table>
    <tr><th>User</th><th>Balance</th></tr>
    {% for a in accounts %}
    <tr><td>{{ a.username }}</td><td>{{ a.balance }}</td></tr>
    {% endfor %}
  </table>
  <h2>Recent Transactions</h2>
  <table>
    <tr><th>ID</th><th>Type</th><th>From</th><th>To</th><th>Amount</th><th>Status</th></tr>
    {% for t in transactions %}
    <tr>
      <td>{{ t.id }}</td><td>{{ t.tx_type }}</td><td>{{ t.from_user or '-' }}</td>
      <td>{{ t.to_user or '-' }}</td><td>{{ t.amount }}</td><td>{{ t.status }}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>"""


@app.route("/")
def index():
    accounts = _safe_query("SELECT username, balance FROM accounts ORDER BY balance DESC LIMIT 100")
    transactions = _safe_query(
        "SELECT id, tx_type, from_user, to_user, amount, status "
        "FROM transactions ORDER BY id DESC LIMIT 50"
    )
    return render_template_string(
        DASHBOARD_HTML,
        accounts=accounts,
        transactions=transactions,
        now=datetime.now(timezone.utc).isoformat(),
    )


@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "bounty-plaza"})


@app.route("/api/resolve", methods=["POST"])
def api_resolve():
    """
    Resolve a StateGraphNode topology without triggering TS2589.

    Request body:
        {"graph": <node | [node, ...]>}

    Response:
        {"ok": true, "nodes": [...]}
        {"ok": false, "error": "..."}
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "graph" not in payload:
        return jsonify({"ok": False, "error": "missing 'graph' field"}), 400

    try:
        nodes = unwrap_state_graph(payload["graph"])
    except ResolveError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 422

    return jsonify({"ok": True, "nodes": nodes})


@app.route("/api/balance/<username>")
def api_balance(username):
    rows = _safe_query("SELECT balance FROM accounts WHERE username = ?", (username,))
    if not rows:
        return jsonify({"ok": False, "error": "unknown user"}), 404
    balance = rows[0]["balance"]
    return jsonify({
        "ok": True,
        "username": username,
        "balance": balance,
        "usd": round(balance * 0.72, 2),
    })


def main():
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()