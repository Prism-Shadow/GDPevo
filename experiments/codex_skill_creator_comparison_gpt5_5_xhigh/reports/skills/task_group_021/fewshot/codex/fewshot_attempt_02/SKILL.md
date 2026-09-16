---
name: asteria-dq-hub-audits
description: Reconcile Asteria Fleet Data Quality Hub audit tasks that provide payloads/case_scope.json and payloads/answer_template.json. Use for contact canonicalization and readiness, fuel or freight transaction normalization, maintenance-log integrity, duplicate snapshot resolution, quarantine and mismatch reporting, code decision panels, rollups, rankings, and PASS/HOLD certification decisions.
---

# Asteria DQ Hub Audits

## Required Inputs

Read the task prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md` before querying the hub. Treat the answer template as the output contract: required keys, allowed enums, numeric precision, uniqueness, and ordering rules come from the template and case scope.

Read [references/audit_workflow.md](references/audit_workflow.md) before computing an answer. It contains the reusable reconciliation rules, code mappings, and family-specific audit recipes.

## Data Access

Use only the base URL and endpoints listed in `environment_access.md`. The public REST endpoints return:

```json
{"items": [], "limit": 100, "offset": 0, "total": 0}
```

Fetch every page until `offset + limit >= total`; many collections are larger than one page. The REST filter key for business collections is `collection`, not `collection_id`. Reference endpoints use `domain`, `kind`, and `currency` filters when applicable.

The read-only `/api/query` service may be used when credentials are present in `environment_access.md`. If it is unavailable or requires missing credentials, use paginated REST endpoints and do joins locally.

The bundled helper can export a full endpoint:

```bash
python skill/scripts/fetch_hub.py --env environment_access.md --endpoint /api/contacts --param collection=<collection_id> --out contacts.json
python skill/scripts/fetch_hub.py --env environment_access.md --endpoint /api/reference/aliases --param domain=fuel --out fuel_aliases.json
```

## One-Pass Workflow

1. Parse the case scope for the collection, cutoff, business period, focus IDs, ranking policies, status thresholds, and scoped decision panels.
2. Inspect `/api/catalog/collections`, `/api/catalog/schema`, and `/api/source-snapshots?collection=<collection_id>` to identify the family, fields, snapshots, and authoritative source evidence.
3. Fetch all in-scope source rows and relevant references: aliases, unit conversions, FX rates, or contacts/events/transactions as needed.
4. Reconstruct logical records before aggregating. Count raw rows before deduplication, then retain one row per logical ID using certified source evidence over provisional evidence, with recency only as a tie-breaker inside the same status.
5. Classify each retained logical record as valid, mismatch, quarantine, contested, or regression according to the family rules in the reference and the task wording.
6. Compute all requested sets, focus decisions, totals, rollups, rankings, and status/action outputs from the reconstructed records.
7. Validate the final JSON against the answer template manually: no extra keys, all required keys, exact enum strings, stable-ID ordering, unique arrays, count partitions, and required rounding.

## Output Discipline

Return exactly one JSON object and no Markdown. Do not hardcode values from prior examples. Stable-ID arrays are usually lexicographic unless the template or case scope gives a different sort. Ranked arrays must follow the declared sort and include rank numbers when the contract requires them.
