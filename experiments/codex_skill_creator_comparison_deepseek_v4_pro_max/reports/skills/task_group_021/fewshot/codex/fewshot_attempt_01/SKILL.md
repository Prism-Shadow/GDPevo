---
name: asteria-dqh
description: Reconcile, audit, and certify data collections through the Asteria Fleet Data Quality Hub REST API. Use when working with fleet operations data (partner contacts, fuel purchases, maintenance events, field-service rosters, freight charges) that requires snapshot reconciliation, duplicate detection, quarantine classification, control-code assignment, and conformant JSON audit reporting. Triggers on tasks referencing the Asteria Fleet DQH, source-snapshot reconciliation, or any of the /api/catalog, /api/contacts, /api/transactions, /api/maintenance, /api/reference, /api/source-snapshots, or /api/query endpoints.
---

# Asteria Fleet Data Quality Hub Reconciliation

## Overview

The Asteria Fleet Data Quality Hub (DQH) is a read-only REST API that exposes fleet operations collections with overlapping source snapshots. Every audit task follows the same fundamental pattern: resolve the authoritative snapshot, reconcile duplicates, classify records into valid/quarantine/mismatch categories, compute aggregate metrics, assign internal control codes, and produce a JSON answer conforming to a supplied template.

## General Workflow

Follow these steps in order for every DQH audit task. The exact domain rules are in [references/domain_workflows.md](references/domain_workflows.md); the full API reference is in [references/api_endpoints.md](references/api_endpoints.md); control code families and assignment principles are in [references/control_codes.md](references/control_codes.md).

### Step 1: Understand the Task

Read the prompt, `case_scope.json`, and `answer_template.json` from the payloads directory. The case scope defines the collection, cutoff, focus entities, and decision panels. The answer template is the exact JSON schema you must conform to—study its required keys, enum values, ordering rules, and numeric precision.

### Step 2: Discover the API Surface

Fetch `GET /api/catalog/collections` to confirm the collection exists. Fetch `GET /api/catalog/schema?collection_id=...` to learn the field names, types, and semantics of the target collection. Fetch `GET /api/source-snapshots?collection_id=...` to enumerate available snapshots for the collection.

### Step 3: Load the Data

The primary data endpoint depends on the domain:
- Partner/people records: `GET /api/contacts?collection_id=...`
- Fuel transactions: `GET /api/transactions/fuel?collection_id=...`
- Freight charges: `GET /api/transactions/freight?collection_id=...`
- Maintenance events: `GET /api/maintenance/events?collection_id=...`

Page through results. Use `offset` and `limit` query parameters when available. When the collection is larger than a single response page, fetch all pages.

Load reference data as needed: `GET /api/reference/aliases`, `GET /api/reference/conversions`, `GET /api/reference/fx`.

### Step 4: Resolve the Authoritative Snapshot

Among the available snapshots, the CERTIFIED snapshot (if present) is always authoritative. A PROVISIONAL snapshot contains additional raw rows that may duplicate CERTIFIED records. For duplicate resolution, retain the CERTIFIED copy. The authoritative snapshot ID is the one with `status == "CERTIFIED"`; if none is CERTIFIED, prefer PROVISIONAL over STALE.

Raw rows are identified by a unique ID field (`row_id`, `event_id`, `charge_id`, etc.). Logical records (the same business event appearing in two snapshots) share the same public stable ID. Count `raw_row_count` across all snapshots, `logical_*_count` as the deduplicated set of stable IDs, and `duplicate_raw_count` as `raw_row_count - logical_*_count`.

### Step 5: Classify Every Logical Record

For each logical record, determine its disposition:

- **Valid**: Meets all business rules (correct category, positive quantities, usable contact channels, parseable timestamps, etc.). Valid records enter normalized totals.
- **Quarantine**: Fails a hard rule (unrecognized category, invalid measure, no usable contact). Quarantined records are excluded from normalized totals and reported separately.
- **Mismatch**: A valid record whose actual category/class differs from the expected category/class. Mismatched records still enter normalized totals under their recognized category.

The specific classification rules for each domain are in [references/domain_workflows.md](references/domain_workflows.md).

### Step 6: Compute Aggregate Metrics

Count raw rows, logical records, duplicates, valid records, mismatches, and quarantines. Compute rates where required (e.g., quarantine_rate = quarantine_count / canonical_count).

For financial/physical totals: sum over valid records only, applying unit conversions via `GET /api/reference/conversions` and FX rates via `GET /api/reference/fx` when needed. Round to the precision declared in the answer template.

Rank entities (assets, merchants, carriers) using the sort criteria in `case_scope.json`: primary sort descending on the main metric, ties broken by secondary metric descending then ID ascending.

### Step 7: Assign Control Codes

Every audit task includes a decision panel of public stable IDs that need internal control codes. The code families are enumerated in [references/control_codes.md](references/control_codes.md). The codes are not arbitrary—they correlate with evidence patterns in the data. To assign them:

1. For each scoped public ID, look up its full record in the API response.
2. Compare the record's field values, source provenance, and disposition against the patterns documented in the control codes reference.
3. Assign the code that matches the evidence. Each code family has a consistent internal logic.

When the task asks for control codes without providing the mapping table, infer them by cross-referencing the evidence patterns across all scoped IDs. IDs with similar data characteristics tend to receive the same code.

### Step 8: Determine Certification Status

Apply the status thresholds from `case_scope.json` (or equivalent certification gate). Common mappings:

| Status | Action |
|--------|--------|
| PASS | RELEASE |
| PASS_WITH_EXCEPTIONS | REVIEW_EXCEPTIONS |
| HOLD | BLOCK_AND_REMEDIATE |

Determine the status by comparing computed metrics (quarantine rate, regression count, exception count) against the thresholds.

### Step 9: Assemble the JSON Output

Produce exactly one JSON object matching `answer_template.json`. Critical rules:

- Every required key must be present. No extra keys.
- Arrays must have the exact declared lengths (minItems == maxItems).
- Sort arrays lexicographically by their primary ID field unless a different ordering is declared.
- Use the exact enum string values from the template.
- Apply the declared numeric precision (rounding, decimal places).
- Include no commentary, Markdown, or extra text outside the JSON.
- Stable IDs must come from the actual API data or the case scope—never invent IDs.

## Quick Reference

| Concern | Reference |
|---------|-----------|
| Endpoint URLs, query params, response shapes | [references/api_endpoints.md](references/api_endpoints.md) |
| Code families, enum values, assignment logic | [references/control_codes.md](references/control_codes.md) |
| Domain-specific rules (fuel, freight, maintenance, contacts) | [references/domain_workflows.md](references/domain_workflows.md) |
