---
name: asteria-data-quality-hub
description: Reconcile Asteria Fleet Data Quality Hub collections and produce schema-exact JSON audit or certification answers. Use when a task mentions Asteria Fleet Data Quality Hub, case_scope.json, answer_template.json, environment_access.md, and partner/dealer/roster contacts, fuel purchases, freight charges, or maintenance event data quality audits.
---

# Asteria Data Quality Hub

## Core Workflow

1. Read the prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md` before querying the hub.
2. Treat `answer_template.json` as the output contract. Extract required keys, allowed enums, ordering rules, item counts, uniqueness rules, and numeric precision before doing calculations. Some templates are JSON Schema; others are compact field contracts.
3. Use the hub metadata first:
   - `GET /api/catalog/collections` to confirm `collection_id`, family, approximate count, and source systems.
   - `GET /api/catalog/schema` to confirm view/field names.
4. Fetch the complete collection and support references. Prefer the bundled helper:

```bash
python <skill-dir>/scripts/fetch_hub_collection.py \
  --env environment_access.md \
  --collection '<collection_id>' \
  --out hub_dump
```

Use `--header 'Name: value'` only when `environment_access.md` supplies credentials. If using curl manually, pass `collection=<collection_id>` to data and source-snapshot endpoints and page with `limit`/`offset` until `offset + limit >= total`.

5. Reconcile retained logical records, quality issues, canonical fields, totals, rankings, and code panels by collection family. Read [references/audit_patterns.md](references/audit_patterns.md) for the reusable family rules and opaque code semantics.
6. Build the final object directly from the answer contract. Use only stable IDs from the task scope or hub data, sort arrays exactly as specified, deduplicate set outputs, round only the final reported numeric totals, and return JSON only.

## Hub Access Notes

- Data endpoints return `{"items": [...], "limit": n, "offset": n, "total": n}`.
- Collection family selects the main endpoint:
  - `contacts`: `/api/contacts`
  - `fuel`: `/api/transactions/fuel`
  - `freight`: `/api/transactions/freight`
  - `maintenance`: `/api/maintenance/events`
- Support endpoints use filters by reference type, for example `domain=fuel`, `domain=freight`, `kind=volume`, `kind=weight`, `kind=distance`, and `currency=EUR`.
- `/api/query` can be useful for aggregate checks when credentials are provided, but all observed task families can be solved from the paginated GET endpoints.

## Final Checks

- Recompute counts from retained logical records, not raw rows, unless a field explicitly asks for raw rows.
- Keep quarantined financial rows out of normalized totals; keep valid mismatches in totals.
- Keep contact readiness partitions mutually exclusive.
- Keep maintenance invalid events and odometer-regression events separate unless the contract explicitly combines them.
- Validate JSON syntax with `python -m json.tool`; if `jsonschema` is available and the template is JSON Schema, validate against the template too.
