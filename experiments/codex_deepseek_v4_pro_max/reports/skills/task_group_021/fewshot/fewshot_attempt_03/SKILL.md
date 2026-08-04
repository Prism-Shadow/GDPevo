---
name: asteria-fleet-dq-hub
description: Complete data-quality audits, reconciliations, and certification decisions using the Asteria Fleet Data Quality Hub REST API. Use when a task involves case_scope.json, answer_template.json, and environment_access.md payloads against the Fleet Hub.
---

# Asteria Fleet Data Quality Hub Skill

## Overview

The Asteria Fleet Data Quality Hub is a read-only REST API that exposes fleet-domain data collections (contacts, fuel transactions, freight charges, maintenance events, and reference tables) along with catalog, schema, and source-snapshot metadata. Tasks using this hub follow a consistent pattern: read the case scope and answer template, discover the API catalog and schema, reconcile overlapping source records, compute quality metrics, assign internal control/policy codes, determine a certification or release decision, and emit a single JSON object that conforms exactly to the answer template.

## Task Input File Layout

Every task supplies three files:

- `payloads/case_scope.json` — business parameters: collection ID, cutoff timestamps, focus entities, decision-panel IDs, ranking rules, and certification thresholds.
- `payloads/answer_template.json` — the exact output JSON schema, including required keys, enum values, numeric precision, ordering rules, and ID format patterns (often expressed as `pattern` regex constraints).
- `environment_access.md` — runtime connection details: base URL, allowed GET endpoints, and the POST `/api/query` authorization header.

Read all three files first. The case scope tells you **what** to compute; the answer template tells you **how** to shape the response; `environment_access.md` tells you **where**.

## API Reference

### Base URL

The base URL is provided in `environment_access.md` as `GDPEVO_ENV_BASE_URL`. All endpoints are relative to this value. Substitute any `<TASK_ENV_BASE_URL>` placeholder found in the task prompt with this value.

### Authentication

All read calls (GET) are unauthenticated. The query interface requires a header:

```
Authorization: Bearer asteria-read-021
```

### Endpoints

#### GET Endpoints (no auth)

| Endpoint | Purpose |
|---|---|
| `/api/catalog/collections` | List available collections with their stable IDs, business names, and snapshot summaries. |
| `/api/catalog/schema` | Column names, types, and nullability for every collection. |
| `/api/contacts` | Contact records from HR Directory, Dispatch, and Identity Registry sources. |
| `/api/transactions/fuel` | Fuel purchase transactions. |
| `/api/transactions/freight` | Freight charge records. |
| `/api/maintenance/events` | Maintenance event logs. |
| `/api/reference/aliases` | Lookup table mapping alias keys to canonical categories. |
| `/api/reference/conversions` | Unit-conversion factors (volume, weight, distance). |
| `/api/reference/fx` | Foreign-exchange rates against a base currency. |
| `/api/source-snapshots` | Snapshot metadata per collection: snapshot_id, status (`CERTIFIED`, `PROVISIONAL`, `STALE`), row count, creation timestamp. |

#### POST `/api/query` (auth required)

Send a SQL `SELECT` or `WITH` query in the JSON body. The hub exposes **public views** (all prefixed with `v_`). Use only views — never query underlying tables directly.

```bash
curl -s -X POST '<BASE>/api/query' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer asteria-read-021' \
  -d '{"query":"SELECT * FROM v_<collection> LIMIT 10"}'
```

Responses are paginated JSON arrays. When a collection is larger than one page, follow the pagination metadata returned by the API to fetch all rows.

## General Workflow

Follow these steps for every audit/certification task. Adapt the specifics to the domain (contacts, fuel, freight, maintenance) but preserve the sequence.

### 1. Discover the Catalog and Schema

Call `GET /api/catalog/collections` to confirm the target collection exists. Call `GET /api/catalog/schema` to understand column names, types, and which fields map to the case-scope parameters.

### 2. Identify the Authoritative Snapshot

Call `GET /api/source-snapshots` and filter for the target collection. When multiple snapshots exist for the same collection, prefer `CERTIFIED` over `PROVISIONAL` over `STALE`. The authoritative snapshot is the one whose `snapshot_status` is `CERTIFIED` and whose `created_at` is at or before the cutoff. Record its `snapshot_id` and `row_count`.

### 3. Fetch and Page Through the Data

Use `POST /api/query` to select rows from the authoritative snapshot. Include a `WHERE` clause that limits rows to the cutoff timestamp. When the result set exceeds one page, iterate until all rows are collected.

### 4. Fetch Reference Data

Depending on the domain, call the relevant GET endpoint or query reference views:

- **Contacts/People tasks**: `GET /api/contacts` — multiple source systems (HR Directory, Dispatch, Identity Registry).
- **Fuel tasks**: `GET /api/transactions/fuel`, `GET /api/reference/aliases`, `GET /api/reference/conversions`, `GET /api/reference/fx`.
- **Freight tasks**: `GET /api/transactions/freight`, `GET /api/reference/aliases`, `GET /api/reference/conversions`, `GET /api/reference/fx`.
- **Maintenance tasks**: `GET /api/maintenance/events`, `GET /api/reference/conversions`.

### 5. Reconcile Overlapping Sources

When multiple source systems or snapshots overlap on the same logical entity:

- **Deduplication**: Identify rows that represent the same logical entity (same person, same transaction, same event) across sources. Group them into clusters; each cluster yields one canonical entity.
- **Survivor selection**: When one row must represent the cluster, prefer the `CERTIFIED` snapshot. Within a snapshot, apply precedence rules from the case scope or the source-system hierarchy implied by the schema.
- **Duplicate reporting**: Report only cross-snapshot or cross-source duplicates where the same logical ID appears more than once. Do not report intra-snapshot duplicates unless the schema explicitly surfaces them.

### 6. Compute Quality Metrics

Count raw rows, canonical entities, duplicate clusters, and quarantined/invalid rows. Domain-specific issues include:

- **Contacts**: rows with no usable email or phone are quarantined.
- **Fuel**: rows with unrecognized or ambiguous fuel-category aliases, non-positive quantities, or invalid prices are quarantined.
- **Freight**: rows with unrecognized or ambiguous service-class aliases, non-positive weight, or non-positive distance are quarantined.
- **Maintenance**: rows with missing or unparseable timestamps, invalid odometer values (outside 0–9,999,999 range), negative labor hours, extreme labor hours (>1,000), or odometer regression within an asset are rejected.

Category/class mismatches (expected vs. actual) are **not** quarantined — they are reported separately as mismatches but still counted in valid totals. Quarantined rows are excluded from valid totals.

### 7. Assign Control and Policy Codes

The answer template defines allowed code values for each code family. Infer the correct code from the shared records and the reconciled audit results:

| Code Family | Typical Enum Values | Context |
|---|---|---|
| Identity Code (`IC`) | IC-25, IC-40, IC-70, IC-90 | Source identity or cluster resolution path |
| Outreach Code (`OR`) | OR-15, OR-35, OR-60, OR-80 | Communication consent/readiness state |
| Field Provenance Code (`FP`) | FP-20, FP-55, FP-75 | Data field origin and trust tier |
| Reference Policy Code (`RB`) | RB-17, RB-42, RB-83 | Reference-data classification policy |
| Source Basis Code (`SB`) | SB-24, SB-61, SB-79 | Source-evidence retention rule |
| Ledger Disposition Code (`LD`) | LD-14, LD-31, LD-53, LD-72, LD-88 | Financial ledger routing |
| Maintenance Source Code (`MS`) | MS-12, MS-47, MS-86 | Maintenance data provenance |
| History Route Code (`HR`) | HR-19, HR-33, HR-74 | Maintenance history pipeline |

Code assignments must be internally consistent: rows sharing the same reconciliation outcome or source provenance should receive the same code. The specific mapping is inferred from how data flows through the reconciliation pipeline — examine source-system origins, snapshot statuses, and whether a row was retained, merged, or quarantined.

### 8. Determine Certification / Release Status

Apply the thresholds and action map from `case_scope.json`:

- Compute the quarantine rate (quarantined rows / canonical entities) or exception rate as defined by the scope.
- Compare against `pass_max_quarantine_rate` and `pass_with_exceptions_max_quarantine_rate` (or equivalent fields).
- Map the resulting status (`PASS`, `PASS_WITH_EXCEPTIONS`, `HOLD`) to its action (`RELEASE`, `REVIEW_EXCEPTIONS`, `BLOCK_AND_REMEDIATE`) using `status_action_map`.

Some tasks use a hard gate (e.g., "any odometer regression → HOLD") instead of rate thresholds. Follow the case scope literally.

### 9. Format the Output

Construct one JSON object conforming to the answer template. Follow these rules strictly:

- **Enum values**: Use exactly the strings listed in the schema — no variants.
- **ID patterns**: Match the regex patterns exactly (e.g., `PAR-C[0-9]{5}`, `FC-[0-9]{6}-[0-9]{6}`, `ME-Q1-[0-9]{6}`).
- **Sorting**: Sort string arrays lexicographically ascending. Sort object arrays by their primary key ascending (as declared in the template's ordering rules).
- **Deduplication**: All ID arrays must have `uniqueItems: true`.
- **Numeric precision**: Round to the decimal places declared in the schema. Use `multipleOf` constraints as guidance. Count fields are always exact integers.
- **No extras**: The template typically has `additionalProperties: false`. Do not include keys outside the schema.
- **No commentary**: Output only the JSON object. No Markdown fences, no explanatory text.

## Domain-Specific Patterns

### Contact / People Reconciliation

Multiple source systems (HR Directory, Dispatch, Identity Registry) contribute rows for the same person. Resolve clusters by matching on name, email, phone, and regional identifiers. When systems disagree on a contact field, follow a precedence chain: the case scope or schema order typically implies which system is most trusted for each field. Survivor selection uses the most complete row within the preferred snapshot. Quarantined contacts have no usable email and no usable phone. Readiness depends on consent (must be `GRANTED`) and at least one usable channel.

### Fuel Purchase Audit

Map each transaction's `fuel_alias` through the aliases lookup to a recognized fuel type. Aliases that match zero or more than one canonical category produce unrecognized/ambiguous counts. Convert all volumes to the canonical unit (liters) using the conversions table. Convert all amounts to the base currency using the FX rates at the transaction date. Quarantined transactions (invalid quantity, unrecognized alias) are excluded from normalized totals.

### Freight Charge Audit

Map each charge's `service_alias` through aliases to a recognized service class. Convert weight and distance to canonical units. Quarantine reasons include unrecognized alias, ambiguous alias, non-positive weight, and non-positive distance. Carrier ranking uses mismatch spend (valid charges with class mismatch) as the primary sort.

### Maintenance Event Audit

Events span a business period but may have been snapshotted after it. Fetch all snapshots for the collection, retain the authoritative one, and reconcile overlapping events across snapshots. Reject events with invalid timestamps, invalid odometer readings (0–9,999,999 range), negative or extreme (>1,000) labor hours, or odometer regression (an odometer reading lower than the previous reading for the same asset). Compute corrected distance as the sum across assets of (last reliable odometer − first reliable odometer) for the business period.

## Error Handling

- If the API returns a non-2xx status, retry once after 2 seconds. If it still fails, include the error details in a query to the next available endpoint to determine if the service is partially available.
- If the collection has no `CERTIFIED` snapshot at or before the cutoff, fall back to the most recent `PROVISIONAL` snapshot.
- If pagination metadata is missing, assume one page of up to 1000 rows.
- Schema fields with `null` values should be treated as absent when checking validity (e.g., a null email does not count as a usable contact channel).

## Summary Checklist

Before emitting the answer, verify:

- [ ] All three input files read and cross-referenced.
- [ ] Catalog and schema fetched; target collection confirmed.
- [ ] Authoritative snapshot identified and its ID recorded.
- [ ] All data pages fetched; row count matches snapshot metadata.
- [ ] Reference data (aliases, conversions, FX) applied.
- [ ] Duplicates grouped and reported; survivors retained.
- [ ] Quality counts computed (raw, canonical, duplicates, quarantined, mismatches).
- [ ] Control/policy codes assigned consistently to every required panel entry.
- [ ] Certification thresholds evaluated; status and action set.
- [ ] Output JSON validates against the answer template schema.
- [ ] All arrays sorted and deduplicated per the ordering rules.
- [ ] No extra keys, no Markdown, no commentary.
