#!/usr/bin/env python3
"""Cedar Ridge Portal query helper.

Usage:
  python3 query_portal.py <base_url> sql "<SQL statement>"
  python3 query_portal.py <base_url> get <endpoint>
  python3 query_portal.py <base_url> icd-chapter <icd10_code>
  python3 query_portal.py <base_url> doc-freshness <received_date> <doc_type> [--ref-date YYYY-MM-DD]
"""

import json
import sys
import urllib.request
from datetime import date, timedelta

FRESHNESS_LIMITS = {
    "hbsag": 30,
    "monthly_labs": 30,
    "ppd_or_cxr": 30,
    "history_physical": 365,
}

ICD_CHAPTER_RANGES = [
    ("A00-B99", "Certain infectious and parasitic diseases"),
    ("C00-D49", "Neoplasms"),
    ("E00-E89", "Endocrine, nutritional and metabolic diseases"),
    ("F01-F99", "Mental, Behavioral and Neurodevelopmental disorders"),
    ("G00-G99", "Diseases of the nervous system"),
    ("H00-H59", "Diseases of the eye and adnexa"),
    ("H60-H95", "Diseases of the ear and mastoid process"),
    ("I00-I99", "Diseases of the circulatory system"),
    ("J00-J99", "Diseases of the respiratory system"),
    ("K00-K95", "Diseases of the digestive system"),
    ("L00-L99", "Diseases of the skin and subcutaneous tissue"),
    ("M00-M99", "Diseases of the musculoskeletal system and connective tissue"),
    ("N00-N99", "Diseases of the genitourinary system"),
    ("O00-O9A", "Pregnancy, childbirth and the puerperium"),
    ("P00-P96", "Certain conditions originating in the perinatal period"),
    ("Q00-Q99", "Congenital malformations, deformations and chromosomal abnormalities"),
    ("R00-R99", "Symptoms, signs and abnormal clinical and laboratory findings"),
    ("S00-T88", "Injury, poisoning and certain other consequences of external causes"),
    ("V00-Y99", "External causes of morbidity"),
    ("Z00-Z99", "Factors influencing health status and contact with health services"),
    ("U00-U85", "Codes for special purposes"),
]


def get(base_url: str, endpoint: str) -> dict | list:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


def query(base_url: str, sql: str) -> list:
    url = f"{base_url.rstrip('/')}/query"
    body = json.dumps({"sql": sql}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def icd_category_bounds(code_range: str) -> tuple[str, str]:
    """Return (start_code, end_code) for a range like 'M00-M99'."""
    parts = code_range.split("-")
    return parts[0].strip(), parts[1].strip()


def code_in_range(code: str, start: str, end: str) -> bool:
    """Check if an ICD-10 code falls within a chapter range."""
    def key(c: str) -> tuple:
        alpha = c[0]
        num = 0
        dot = 0
        rest = c[1:]
        if rest:
            dot_idx = rest.find(".")
            if dot_idx >= 0:
                num = int(rest[:dot_idx])
                dot = int(rest[dot_idx + 1:])
            else:
                num = int(rest)
        return (alpha, num, dot)

    return key(start) <= key(code) <= key(end)


def find_icd_chapter(code: str) -> dict:
    """Return chapter info for an ICD-10 code."""
    for ch_range, ch_desc in ICD_CHAPTER_RANGES:
        start, end = icd_category_bounds(ch_range)
        if code_in_range(code, start, end):
            return {"chapter": ch_range, "chapter_description": ch_desc}
    return {"chapter": None, "chapter_description": "Unknown"}


def check_freshness(received_str: str, doc_type: str, ref_date_str: str | None = None) -> dict:
    """Check if a document is stale given its received date and type."""
    if doc_type not in FRESHNESS_LIMITS:
        return {"stale": False, "reason": f"No freshness limit defined for {doc_type}"}

    received = date.fromisoformat(received_str)
    ref = date.fromisoformat(ref_date_str) if ref_date_str else date.today()
    limit = FRESHNESS_LIMITS[doc_type]
    age = (ref - received).days
    stale = age > limit
    return {
        "stale": stale,
        "doc_type": doc_type,
        "received_date": received_str,
        "reference_date": str(ref),
        "age_days": age,
        "freshness_limit_days": limit,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: query_portal.py <base_url> <command> [args...]", file=sys.stderr)
        print("Commands: sql, get, icd-chapter, doc-freshness", file=sys.stderr)
        sys.exit(1)

    base_url = sys.argv[1]
    cmd = sys.argv[2]

    if cmd == "sql":
        if len(sys.argv) < 4:
            print("Usage: query_portal.py <base_url> sql '<SQL>'", file=sys.stderr)
            sys.exit(1)
        result = query(base_url, sys.argv[3])
        print(json.dumps(result, indent=2))

    elif cmd == "get":
        if len(sys.argv) < 4:
            print("Usage: query_portal.py <base_url> get <endpoint>", file=sys.stderr)
            sys.exit(1)
        result = get(base_url, sys.argv[3])
        print(json.dumps(result, indent=2))

    elif cmd == "icd-chapter":
        if len(sys.argv) < 4:
            print("Usage: query_portal.py <base_url> icd-chapter <ICD-10-code>", file=sys.stderr)
            sys.exit(1)
        result = find_icd_chapter(sys.argv[3])
        print(json.dumps(result, indent=2))

    elif cmd == "doc-freshness":
        if len(sys.argv) < 5:
            print("Usage: query_portal.py <base_url> doc-freshness <received_date> <doc_type> [--ref-date YYYY-MM-DD]", file=sys.stderr)
            sys.exit(1)
        ref_date = None
        args = sys.argv[3:]
        if "--ref-date" in args:
            idx = args.index("--ref-date")
            if idx + 1 < len(args):
                ref_date = args[idx + 1]
                args = args[:idx] + args[idx + 2:]
        if len(args) < 2:
            print("Missing received_date or doc_type", file=sys.stderr)
            sys.exit(1)
        result = check_freshness(args[0], args[1], ref_date)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
