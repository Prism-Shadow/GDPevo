#!/usr/bin/env python3
"""Flask API for the Asteria Investment Office shared environment."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from flask import Flask, abort, jsonify, request


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

app = Flask(__name__)


def load_json(filename):
    path = DATA_DIR / filename
    if not path.exists():
        abort(503, description=f"Missing generated data file: {filename}. Run generate_data.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def filter_rows(rows, allowed_fields):
    filtered = rows
    for field in allowed_fields:
        value = request.args.get(field)
        if value is None:
            continue
        if value.lower() in {"true", "false"}:
            parsed = value.lower() == "true"
        else:
            parsed = value
        filtered = [row for row in filtered if row.get(field) == parsed]
    return filtered


@app.get("/")
def index():
    return """
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Asteria Investment Office API</title></head>
<body>
  <h1>Asteria Investment Office API</h1>
  <p>Shared public-data environment for institutional portfolio risk work.</p>
  <ul>
    <li><code>GET /api/catalog</code> - available portfolio, policy, index, issuer, bond, and opportunity-set ids.</li>
    <li><code>GET /api/policies</code> - portfolio constraints and allocation mapping policy.</li>
    <li><code>GET /api/portfolios</code> and <code>/api/portfolios/&lt;portfolio_id&gt;</code> - summaries and current holdings.</li>
    <li><code>GET /api/instruments/bonds</code> - held and candidate bond universe.</li>
    <li><code>GET /api/issuers</code> - issuer research and watchlist records.</li>
    <li><code>GET /api/market/energy</code> - current energy market signals.</li>
    <li><code>GET /api/indices</code>, <code>/api/index-levels</code>, and <code>/api/index-levels/&lt;index_id&gt;</code> - regional equity index data.</li>
    <li><code>GET /api/allocation/opportunity-sets</code>, <code>/api/allocation/prior-views</code>, and <code>/api/macro-signals</code> - allocation taxonomy and signal records.</li>
  </ul>
</body>
</html>
""".strip()


@app.get("/api/catalog")
def catalog():
    portfolios = load_json("portfolios.json")
    indices = load_json("indices.json")
    issuers = load_json("issuers.json")
    bonds = load_json("bonds.json")
    opportunity_sets = load_json("opportunity_sets.json")
    policies = load_json("policies.json")
    return jsonify(
        {
            "portfolio_ids": sorted(row["portfolio_id"] for row in portfolios),
            "index_ids": sorted(row["index_id"] for row in indices),
            "issuer_ids": sorted(row["issuer_id"] for row in issuers),
            "bond_instrument_ids": sorted(row["instrument_id"] for row in bonds),
            "policy_ids": sorted(
                value["policy_id"] for value in policies.values() if isinstance(value, dict) and "policy_id" in value
            ),
            "opportunity_sets": [
                row["opportunity_set"] for row in sorted(opportunity_sets, key=lambda item: item["display_order"])
            ],
        }
    )


@app.get("/api/policies")
def policies():
    return jsonify(load_json("policies.json"))


@app.get("/api/portfolios")
def portfolios():
    rows = load_json("portfolios.json")
    summaries = [
        {
            "portfolio_id": row["portfolio_id"],
            "name": row["name"],
            "strategy": row["strategy"],
            "as_of_date": row["as_of_date"],
            "base_currency": row["base_currency"],
            "market_value_usd_m": row["market_value_usd_m"],
            "objective": row["objective"],
            "constraint_policy_id": row["constraints"].get("policy_id"),
            "holding_count": len(row["holdings"]),
        }
        for row in rows
    ]
    return jsonify(filter_rows(summaries, {"portfolio_id", "strategy", "base_currency"}))


@app.get("/api/portfolios/<portfolio_id>")
def portfolio_detail(portfolio_id):
    rows = load_json("portfolios.json")
    for row in rows:
        if row["portfolio_id"] == portfolio_id:
            return jsonify(row)
    abort(404, description=f"Unknown portfolio_id: {portfolio_id}")


@app.get("/api/instruments/bonds")
def bonds():
    rows = load_json("bonds.json")
    return jsonify(
        filter_rows(
            rows, {"instrument_id", "issuer_id", "sector", "subsector", "rating_bucket", "candidate", "energy_linked"}
        )
    )


@app.get("/api/issuers")
def issuers():
    rows = load_json("issuers.json")
    return jsonify(
        filter_rows(rows, {"issuer_id", "sector", "subsector", "rating_bucket", "watchlist", "credit_outlook"})
    )


@app.get("/api/market/energy")
def energy_market():
    return jsonify(load_json("energy_market.json"))


@app.get("/api/indices")
def indices():
    rows = load_json("indices.json")
    return jsonify(filter_rows(rows, {"index_id", "region", "currency"}))


@app.get("/api/index-levels")
def index_levels():
    return jsonify(load_json("index_levels.json"))


@app.get("/api/index-levels/<index_id>")
def index_level_detail(index_id):
    rows = load_json("index_levels.json")
    if index_id not in rows:
        abort(404, description=f"Unknown index_id: {index_id}")
    return jsonify({"index_id": index_id, "levels": rows[index_id]})


@app.get("/api/allocation/opportunity-sets")
def opportunity_sets():
    rows = load_json("opportunity_sets.json")
    return jsonify(filter_rows(rows, {"asset_class", "sub_asset_class", "opportunity_set"}))


@app.get("/api/allocation/prior-views")
def prior_views():
    rows = load_json("prior_views.json")
    return jsonify(filter_rows(rows, {"quarter", "opportunity_set", "view", "conviction"}))


@app.get("/api/macro-signals")
def macro_signals():
    rows = load_json("macro_signals.json")
    return jsonify(filter_rows(rows, {"quarter", "opportunity_set", "rationale_code"}))


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Asteria Investment Office API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8073")))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app.run(host=args.host, port=args.port)
