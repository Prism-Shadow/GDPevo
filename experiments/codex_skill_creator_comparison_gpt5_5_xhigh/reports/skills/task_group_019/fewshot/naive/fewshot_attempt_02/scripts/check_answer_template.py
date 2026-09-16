#!/usr/bin/env python3
"""Lightweight sanity checks for licensing JSON answers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def required_top_keys(template: dict) -> list[str]:
    if isinstance(template.get("required_top_level_keys"), list):
        return list(template["required_top_level_keys"])
    if isinstance(template.get("top_level_keys"), dict):
        return list(template["top_level_keys"].keys())
    instructions = template.get("instructions")
    if isinstance(instructions, dict) and isinstance(instructions.get("top_level_keys"), list):
        return list(instructions["top_level_keys"])
    schema = template.get("schema")
    if isinstance(schema, dict):
        return list(schema.keys())
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template")
    parser.add_argument("answer")
    args = parser.parse_args()

    template = json.loads(Path(args.template).read_text(encoding="utf-8"))
    answer = json.loads(Path(args.answer).read_text(encoding="utf-8"))
    errors: list[str] = []

    if not isinstance(answer, dict):
        errors.append("answer must be one JSON object")
    else:
        required = required_top_keys(template)
        if required:
            missing = [key for key in required if key not in answer]
            extra = [key for key in answer if key not in required]
            if missing:
                errors.append(f"missing top-level keys: {missing}")
            if extra:
                errors.append(f"extra top-level keys: {extra}")

        decisions = answer.get("application_decisions")
        summary = answer.get("summary")
        if isinstance(decisions, list) and isinstance(summary, dict):
            counts = {"APPROVE": 0, "HOLD": 0, "DENY": 0}
            high_risk: list[str] = []
            policy_impacted: list[str] = []
            ids = []
            for item in decisions:
                if not isinstance(item, dict):
                    continue
                app_id = item.get("application_id")
                if isinstance(app_id, str):
                    ids.append(app_id)
                det = item.get("determination")
                if det in counts:
                    counts[det] += 1
                if item.get("risk_tier") == "high" and isinstance(app_id, str):
                    high_risk.append(app_id)
                if item.get("policy_impacted") is True and isinstance(app_id, str):
                    policy_impacted.append(app_id)
            if ids != sorted(ids):
                errors.append("application_decisions are not sorted by application_id")
            for det, key in [("APPROVE", "approve_count"), ("HOLD", "hold_count"), ("DENY", "deny_count")]:
                if key in summary and summary[key] != counts[det]:
                    errors.append(f"{key} does not match application decisions")
            if "high_risk_application_ids" in summary and summary["high_risk_application_ids"] != sorted(high_risk):
                errors.append("high_risk_application_ids does not match high-risk decisions")
            if "policy_impacted_application_ids" in summary and summary["policy_impacted_application_ids"] != sorted(policy_impacted):
                errors.append("policy_impacted_application_ids does not match decisions")

        queue = answer.get("queue")
        if isinstance(queue, list):
            ranks = [item.get("rank") for item in queue if isinstance(item, dict)]
            if ranks != list(range(1, len(queue) + 1)):
                errors.append("queue ranks must be contiguous from 1")
            if isinstance(summary, dict) and "queue_size" in summary and summary["queue_size"] != len(queue):
                errors.append("summary.queue_size does not match queue length")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
