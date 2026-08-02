# Extraction & aggregation pipeline (outline)

A matter-parameterized way to pull and stage one matter's rows. Read the hub
base URL, the API-key header name/value, and the permitted endpoints from the
**task's environment-access file** (or from environment variables you set from
it) — do not hardcode them. Query business data only from the hub's read
endpoints; never read local source/db/seed/manifest files.

## Discover, then extract

1. Read the hub's schema/layout resource once to confirm the available read
   endpoints and the table/column layout.
2. For each table, pull this matter's rows via the hub's read-only SQL query
   endpoint: `SELECT * FROM <table> WHERE matter_id = '<matter>'`. Save each
   table's rows to a local scratch file so you can re-read while building the
   answer. (Stay outside the deliverable; the answer is JSON only.)

The base URL, the API-key header, and the exact query-endpoint path all come
from the task's environment-access file — read them at runtime, do not hardcode:

```python
# helper.py — every access detail is read from the environment at runtime.
import json, os, urllib.request

BASE  = os.environ["HUB_BASE_URL"].rstrip("/")       # from the env-access file
QPATH = os.environ["HUB_QUERY_PATH"]                 # e.g. the SQL query endpoint path
HDR   = {os.environ["HUB_KEY_HEADER"]: os.environ["HUB_KEY_VALUE"],
         "Content-Type": "application/json"}
TABLES = ["subpoena_categories", "production_stats", "custodian_sources",
          "review_documents", "privilege_entries", "qc_findings",
          "retention_events", "remediation_actions"]

def query(sql):
    req = urllib.request.Request(BASE + QPATH,
        data=json.dumps({"sql": sql}).encode(), headers=HDR, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["rows"]

def pull(matter, outdir):
    os.makedirs(outdir, exist_ok=True)
    for t in TABLES:
        rows = query(f"SELECT * FROM {t} WHERE matter_id = '{matter}'")
        json.dump(rows, open(f"{outdir}/{t}.json", "w"), indent=2)
        print(t, len(rows))
```

## Triage the material set

```python
# 1. Spine: non-noise remediation actions -> material anchor target_refs.
acts = json.load(open(f"{outdir}/remediation_actions.json"))
material_targets = [a["target_ref"] for a in acts
                    if "NOISE" not in a["action_id"]
                    and "realistic operational noise" not in a["description"]
                    and a["target_ref"].startswith(("SRC-", "PRIV-", "QC-", "RET-"))]

# 2. Pull each anchor from its home table by ID; read its note for the numbers.
# 3. Extend: scan production_stats for a contradicted zero-claim, and
#    custodian_sources for an available-archive/retained source.
# 4. Drop distractors: rows whose note matches the boilerplate list (SKILL §3)
#    and that no non-noise remediation action targets.
```

## Aggregate for metrics

Reduce only the material anchors into the counts the template asks for
(see `field-mapping.md` §5.a). Cross-check `review_documents` only to confirm a
single count that a material `qc_finding` references (e.g. a lone
responsiveness-miscode doc). Keep whole integers; `unlogged = withheld − logged`;
category lists = sorted unions; ready-booleans false when any gap remains.

## Assemble & validate

Build the JSON from the template's `required_top_level_keys`, populate each list
from the material set, sort per `ordering_rules`, and validate every enum value
against the template's `enums` before returning one JSON object with no prose.
