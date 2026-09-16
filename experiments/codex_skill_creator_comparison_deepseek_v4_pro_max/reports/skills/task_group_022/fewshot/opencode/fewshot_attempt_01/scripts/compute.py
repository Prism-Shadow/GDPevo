#!/usr/bin/env python3
"""Skeleton for Atlas Commerce Operations answer computation.

This script provides the structure for fetching data from the Atlas API
and computing the answer JSON. Adapt the query logic and computation
to each task's specific business definitions.

Usage: python3 scripts/compute.py
"""

import json
import subprocess
import statistics
import sys


BASE = "http://task-env:9022"
AUTH_HEADER = "Authorization: Bearer atlas-ops-token-022"


def api_get(path):
    """GET request to the Atlas API."""
    result = subprocess.run(
        ["curl", "-s", "-H", AUTH_HEADER, f"{BASE}{path}"],
        capture_output=True, text=True,
    )
    result.check_returncode()
    return json.loads(result.stdout)


def api_sql(sql):
    """POST a read-only SQL query to the Atlas API."""
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            "-H", AUTH_HEADER,
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"sql": sql}),
            f"{BASE}/api/sql",
        ],
        capture_output=True, text=True,
    )
    result.check_returncode()
    data = json.loads(result.stdout)
    return data.get("rows", [])


def api_transaction(payload):
    """POST a controlled correction transaction."""
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            "-H", AUTH_HEADER,
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            f"{BASE}/api/sql/transaction",
        ],
        capture_output=True, text=True,
    )
    result.check_returncode()
    return json.loads(result.stdout)


def load_json(path):
    """Load a JSON file from disk."""
    with open(path) as f:
        return json.load(f)


def write_answer(data, path="answer.json"):
    """Write the answer JSON conforming to the template."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Written to {path}")


# --- Computation helpers ---

def compute_rate(numerator, denominator, decimals=4):
    """Compute a rate rounded to the given decimal places."""
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, decimals)


def rank_by(items, sort_keys):
    """Sort items by a list of (key, direction) tuples. Direction: 'asc' or 'desc'."""
    def sort_key(item):
        return tuple(
            (-item[k] if d == "desc" else item[k])
            for k, d in sort_keys
        )
    return sorted(items, key=sort_key)


def tiered_classify(rules, context, default_status):
    """Apply tiered classification rules in order.

    Each rule is a dict with 'status' and 'condition' keys.
    Context is a dict of variable names to values that condition
    strings can reference.
    """
    for rule in rules:
        condition = rule["condition"]
        try:
            if eval(condition, {"__builtins__": {}}, context):
                return rule["status"]
        except Exception:
            continue
    return default_status


def compute_median(values, decimals=2):
    """Compute median rounded to given decimal places."""
    if not values:
        return 0.0
    return round(statistics.median(values), decimals)


# If run directly, discover schema and dictionary as a starting point
if __name__ == "__main__":
    print("Discovering Atlas schema...")
    schema = api_get("/api/schema")
    with open("/tmp/atlas_schema.json", "w") as f:
        json.dump(schema, f, indent=2)
    print("Schema saved to /tmp/atlas_schema.json")

    print("Discovering data dictionary...")
    dictionary = api_get("/api/data-dictionary")
    with open("/tmp/atlas_dictionary.json", "w") as f:
        json.dump(dictionary, f, indent=2)
    print("Dictionary saved to /tmp/atlas_dictionary.json")

    print("\nReady. Load input/payloads/*.json and build queries.")
