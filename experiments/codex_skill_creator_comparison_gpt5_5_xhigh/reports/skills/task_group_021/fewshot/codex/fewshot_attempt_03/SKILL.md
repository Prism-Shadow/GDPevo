---
name: asteria-fleet-dq
description: Solve Asteria Fleet Data Quality Hub reconciliation and certification tasks for contacts, roster readiness, fuel purchases, freight charges, and maintenance logs. Use when Codex must read environment_access.md, payloads/case_scope.json, and payloads/answer_template.json, query the Asteria hub endpoints, reconcile overlapping snapshots and duplicates, normalize aliases, units, and FX, infer compact Asteria control codes, and return a strict JSON answer.
---

# Asteria Fleet Data Quality

## Core Workflow

1. Read the task prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md`. Treat the template as the output contract: no extra keys, no commentary, and all arrays sorted exactly as specified.
2. Pull live hub data instead of guessing from IDs. Use the REST endpoints listed in `environment_access.md`; if a read-only `/api/query` credential is available, SQL is fine, but do not depend on it.
3. For large collections, write a task-local analysis script and compute every count, ID set, ranking, and total from fetched JSON. Avoid manual tallying.
4. Apply the domain rules in [reconciliation_rules.md](references/reconciliation_rules.md) for snapshot retention, alias matching, contact canonicalization, maintenance history reconstruction, compact codes, and status decisions.
5. Emit exactly one JSON object. Validate it with `python -m json.tool` and, when the template is JSON Schema and `jsonschema` is available, validate against the template too.

## Fetch Helper

Use [scripts/fetch_hub.py](scripts/fetch_hub.py) to dump paged hub responses into a local working directory:

```bash
python /path/to/skill/scripts/fetch_hub.py \
  --env environment_access.md \
  --out asteria_dump \
  --collection "$COLLECTION_ID"
```

The helper reads the base URL from `environment_access.md`, follows `items`/`total` pagination with `offset`, and writes catalog, schema, snapshots, collection rows, aliases, conversions, and FX reference data as JSON. Collection-specific REST filters use `collection=<collection_id>`.

## Hub Access Notes

- Catalog endpoints: `/api/catalog/collections`, `/api/catalog/schema`.
- Collection endpoints: `/api/contacts`, `/api/transactions/fuel`, `/api/transactions/freight`, `/api/maintenance/events`, filtered with `collection`.
- Snapshot endpoint: `/api/source-snapshots`, filtered with `collection`.
- Alias endpoint: `/api/reference/aliases`, filtered with `domain=fuel` or `domain=freight`.
- Conversion endpoint: `/api/reference/conversions`, filtered with `kind=volume`, `kind=weight`, or `kind=distance`.
- FX endpoint: `/api/reference/fx`; page through all rows and select certified rates by business date and currency.

## Answer Discipline

- Use stable IDs from the task scope and public hub data only.
- Deduplicate ID lists, sort lexicographically unless the template gives another order, and preserve requested panel ordering.
- Round only final reported numeric totals to the precision declared by the template; keep intermediate sums unrounded.
- For Unicode contact fields, normalize for matching, but preserve the chosen source spelling in canonical display fields when the contract asks for Unicode-preserving output.
