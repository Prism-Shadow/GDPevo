---
name: asteria-hub-reconciliation
description: Reconcile Asteria Fleet Data Quality Hub collections and produce strict JSON audit, certification, release, or close answers. Use for Asteria contact-master or roster readiness, partner/dealer/warranty contact resolution, fuel or freight transaction normalization, maintenance-history integrity, source-snapshot retention, reference alias/conversion/fx reconciliation, and opaque Asteria control, policy, source, ledger, or maintenance code panels.
---

# Asteria Hub Reconciliation

Use this skill when a task points to the Asteria Fleet Data Quality Hub and asks for a JSON answer matching a local `payloads/answer_template.json`.

## Required Inputs

Read these before querying data:

- `prompt.txt` for the business objective and endpoint family.
- `payloads/case_scope.json` for collection IDs, cutoff/as-of times, scoped IDs, ranking limits, status gates, and ordering rules.
- `payloads/answer_template.json` for exact keys, enum values, required lengths, numeric precision, and additional-property rules.
- `environment_access.md` for the base URL, allowed endpoints, and any query credentials.

Do not rely on remembered answer values from previous tasks. Treat every count, ID list, ranking, normalized total, and code assignment as something to derive from the current hub data.

## Hub Access

Start with catalog and schema:

```bash
SKILL_DIR=/path/to/this/skill
python "$SKILL_DIR/scripts/hub_query.py" --env environment_access.md get /api/catalog/collections
python "$SKILL_DIR/scripts/hub_query.py" --env environment_access.md get /api/catalog/schema
```

If `/api/query` is available, prefer SQL against the schema views because it is the most reliable way to page, aggregate, and join:

```bash
python "$SKILL_DIR/scripts/hub_query.py" --env environment_access.md query "select * from v_source_snapshots limit 5"
python "$SKILL_DIR/scripts/hub_query.py" --env environment_access.md dump-view v_fuel_transactions --collection COLLECTION_ID --out fuel.jsonl
```

If the query endpoint requires credentials, provide them from `environment_access.md` or environment variables supported by the script (`ASTERIA_AUTH_HEADER`, `ASTERIA_QUERY_TOKEN`, `TASK_ENV_QUERY_TOKEN`, or `QUERY_TOKEN`). If only GET endpoints are available, use the endpoint family named in the prompt and verify its filter syntax from the returned errors/schema before relying on it.

## One-Pass Workflow

1. Parse the answer template into a checklist: top-level keys, required nested keys, array lengths, enum domains, sort orders, uniqueness rules, and rounding precision.
2. Read the case scope. Copy scoped public IDs exactly, but only into the final answer positions requested by the contract.
3. Pull all relevant source rows, source snapshots, aliases, conversions, and FX rows. Page until the returned count matches catalog/snapshot evidence or a query count.
4. Select in-scope snapshots by collection and cutoff/as-of time. Prefer the certified or otherwise authoritative snapshot at or before the cutoff; keep provisional rows only when needed to count raw coverage or report overlaps.
5. Reconcile logical records before computing business metrics. Group by the stable logical ID for the family, retain the authoritative occurrence, and separately record duplicates/overlaps when the contract asks for them.
6. Apply business validation and normalization to retained logical records. Exclude quarantined records from normalized totals unless the contract explicitly says otherwise.
7. Fill scoped decision panels from the reconciled evidence and the codebook in `references/asteria-codebook.md`.
8. Sort every array exactly as the template or case scope says. When no explicit order is provided, use lexicographic ascending by the stable public ID.
9. Validate the final object:

```bash
python "$SKILL_DIR/scripts/check_answer.py" payloads/answer_template.json answer.json
```

Return only the JSON object requested by the task.

## General Reconciliation Rules

Use business timestamps for cutoff eligibility and source-update precedence. Use ingestion timestamps only as a tie-breaker or for hub lineage.

For overlapping source rows, retain the row from the authoritative snapshot. If multiple rows remain tied inside the retained snapshot, prefer verified/active rows, then latest `business_updated_at`, then latest `ingested_at`, then stable ID ascending. Report all snapshot IDs in duplicate groups sorted lexicographically.

Reference aliases, unit conversions, and FX rates apply only when their validity window covers the business date and their publication/status is usable as of the task cutoff. A text value that matches zero active aliases is unrecognized; a text value that matches more than one active canonical value is ambiguous.

Normalize text by trimming, Unicode NFKC where appropriate, case-folding for emails and alias comparison, collapsing whitespace, and stripping punctuation that is not business-meaningful. Normalize phone fields to digits only.

Use decimal arithmetic or carefully rounded floats for currency and physical units. Round only at the output boundary unless the contract states an intermediate precision.

## Contacts

Contact tasks use `v_contacts` or `/api/contacts`. Resolve people/entities from `master_hint`, source identifiers, and usable contact evidence. Multi-row clusters need a complete sorted member list and one survivor/master row. Canonical fields may come from different source systems; choose each field from the most authoritative usable evidence rather than blindly copying the survivor row.

Usable channels:

- Email: nonempty, normalized lowercase, syntactically usable.
- Phone: nonempty digits after normalization.
- Dispatch/readiness: active canonical record, at least one usable channel, and consent `GRANTED`.

Partition blocked contacts by the contract:

- Non-granted consent with a usable channel is a consent block.
- No usable canonical channel is a no-contact/quarantine block.
- Inactive records with usable contact are inactive exclusions.

For readiness rollups, make disposition counts mutually exclusive and prove that they sum to the relevant total for each region/depot.

## Fuel And Freight

Fuel uses `v_fuel_transactions`; freight uses `v_freight_charges`. Group by `transaction_id` or `charge_id` before validation.

For each retained logical row:

- Recognize the actual fuel type or service class from the description using active reference aliases for the business date.
- Quarantine rows with unrecognized/ambiguous class/category or invalid nonpositive physical measures.
- Mark a mismatch only when the row has exactly one recognized class/category and it differs from the expected class/category.
- Exclude quarantined rows from normalized totals.
- Include valid mismatches in normalized totals unless the task says otherwise.

Normalize fuel volume to liters, freight weight to kilograms, freight distance to kilometers, and spend to USD using valid conversion and FX rows. Rank exception merchants/carriers exactly by the scope rule, usually exception exposure/count descending with stable ID ascending tie-breaks.

## Maintenance

Maintenance tasks use `v_maintenance_events` or `/api/maintenance/events`. The collection can be larger than one response page, so count and page explicitly.

Reconstruct history after snapshot retention:

- Reject events with missing/unparseable timestamps, invalid odometer values, negative labor, or extreme labor when the contract names those issues.
- Do not treat sequence-only odometer regressions as invalid-event rejections unless the contract says so; report them in corrected metrics and risk ranking.
- Convert odometers to the requested unit before comparing sequence order.
- For each asset, sort reliable events by event time and stable ID, identify regressions where a later reliable odometer is less than the prior reliable odometer, and compute corrected distance as last reliable odometer minus first reliable odometer.

Risk rankings normally sort by rejected event count descending, then regression count descending, then asset ID ascending.

## Final Gate

Before returning JSON, check:

- The answer has no Markdown or commentary.
- No top-level or nested extra keys violate the template.
- All scoped panels contain exactly the requested IDs and only those IDs.
- Counts agree with the ID lists and partitions in the same answer.
- Duplicates, quarantine IDs, mismatches, rankings, and rollups are sorted as specified.
- Status/action values come from case-scope gates or template enums, not from a hardcoded default.
