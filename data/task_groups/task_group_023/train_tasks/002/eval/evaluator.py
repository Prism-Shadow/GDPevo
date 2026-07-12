#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def get_path(obj, path):
    cur = obj
    for part in path.split("."):
        cur = cur[part]
    return cur


def main():
    script_dir = Path(__file__).resolve().parent
    pred_path = Path(sys.argv[1]) if len(sys.argv) > 1 else script_dir.parent / "output" / "answer.json"
    expected_path = script_dir.parent / "output" / "answer.json"
    checks_path = script_dir / "checks.json"
    pred = json.loads(pred_path.read_text(encoding="utf-8"))
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    checks = json.loads(checks_path.read_text(encoding="utf-8"))
    total = sum(item["weight"] for item in checks)
    earned = 0
    details = []
    for item in checks:
        ok = True
        mismatches = []
        for path in item["paths"]:
            try:
                got = get_path(pred, path)
            except Exception:
                ok = False
                mismatches.append({"path": path, "expected": get_path(expected, path), "got": "__missing__"})
                continue
            exp = get_path(expected, path)
            if got != exp:
                ok = False
                mismatches.append({"path": path, "expected": exp, "got": got})
        if ok:
            earned += item["weight"]
        details.append({"goal": item["goal"], "weight": item["weight"], "matched": ok, "mismatches": mismatches})
    result = {"score": earned / total if total else 0.0, "earned_weight": earned, "total_weight": total, "points": details}
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
