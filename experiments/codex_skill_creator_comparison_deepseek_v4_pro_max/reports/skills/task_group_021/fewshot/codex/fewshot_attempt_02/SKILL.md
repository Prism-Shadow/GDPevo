---
name: asteria-fleet-hub
description: Reconcile and audit Asteria Fleet data-quality collections against the read-only Fleet Data Quality Hub REST API. Use when the task involves partner onboarding contacts, fuel-purchase normalization, maintenance-event integrity, field-service roster readiness, freight-charge accrual reconciliation, or any Asteria fleet data audit that requires querying the hub, resolving overlapping source snapshots, deduplicating logical records, normalizing measures through reference aliases/conversions/fx, assigning internal control codes from evidence patterns, computing corrected metrics, and producing certification decisions against a strict JSON answer contract.
---

# Asteria Fleet Hub

## Overview

The Asteria Fleet Data Quality Hub is a read-only REST API that serves curated collections of operational records (contacts, transactions, events) drawn from multiple source systems and overlapping snapshots. Each task reconciles one collection as of a stated cutoff, deduplicates overlapping rows, classifies quality issues, normalizes measures, applies deterministic control codes, and produces a certification decision in strict JSON.

## API Discovery Flow

1. `GET /api/catalog/collections` — list available collections and their metadata (id, display name, snapshot associations)
2. `GET /api/catalog/schema` — returns column definitions, source-system fields, and quality-rule semantics for each collection
3. `GET /api/source-snapshots` — list snapshots with status (`certified`, `provisional`) and row counts per collection

Use the schema response to understand which column is the logical-record identifier, which columns hold source-system provenance, and which columns participate in quality checks (timestamp validity, odometer range, labor range, contact-channel presence, consent status, expected-vs-actual category, physical measures).

Runtime access details including base URL and credentials come from `environment_access.md`.

## Core Reconciliation Workflow

### 1. Parse the case scope

Read `payloads/case_scope.json` for:
- `collection_id` — which collection to audit
- `cutoff_at` / `as_of` / `business_cutoff` — temporal filter (ISO-8601 UTC)
- Focus-entity lists, decision-panel ID lists, threshold rules, ranking policies

### 2. Resolve the authoritative snapshot

From the source-snapshot response, identify the snapshot with status `certified` whose `collection_id` matches the case scope. This is the authoritative snapshot. When the same logical record appears in multiple snapshots (typically `certified` and `provisional`), the `certified` snapshot's row is authoritative and the `provisional` duplicate is excluded from normalized totals.

### 3. Fetch the data

Use either the domain-specific GET endpoint or the SQL query interface:

- **Contacts**: `GET /api/contacts` returns the full row set for the collection. Filter by `collection_id` query param or by the schema's collection-scoping field.
- **Transactions**: `GET /api/transactions/fuel` or `GET /api/transactions/freight` per domain.
- **Maintenance events**: `GET /api/maintenance/events`. Larger collections may require pagination; use `POST /api/query` with SQL `LIMIT`/`OFFSET` to fetch all pages.
- **General**: `POST /api/query` with a SQL `SELECT` that scopes to the collection and cutoff.

The hub's `/api/query` endpoint supports standard SQL `SELECT` with `WHERE`, `ORDER BY`, `LIMIT`, and `OFFSET` clauses. Use it when you need server-side filtering, pagination, or when the dedicated GET endpoint does not return the full dataset.

### 4. Deduplicate overlapping records

Identify rows that share the same logical-record identifier (the stable ID column from the schema: `transaction_id`, `event_id`, `charge_id`, etc.) but appear in different snapshots. Group by logical ID:

- If a group contains a row from the authoritative (`certified`) snapshot, retain that row and exclude all others.
- The `duplicate_raw_count` is the total number of excluded rows across all groups.
- Report each duplicate group with the shared logical ID, list of snapshot IDs containing it, and which snapshot's row was retained.

For contact-merging tasks where there is no explicit logical ID across snapshots, merge by contact-identity matching (name similarity, email match, phone match) across source systems. See [Contact Merging](references/contact_merging.md).

### 5. Apply quality classification

For each retained (non-duplicate) logical record, classify issues based on the schema's quality rules:

**Common quality checks:**
- **Unrecognized / ambiguous category**: Map a descriptive field through reference aliases. If no alias matches or multiple aliases match, classify as unrecognized.
- **Category mismatch**: Compare the expected category (from alias lookup) against the actual category on the record. If different, it is a mismatch.
- **Invalid physical measures**: Non-positive weight/distance/volume/quantity values.
- **Invalid timestamps**: Unparseable, missing, or outside business-period timestamps.
- **Invalid odometer / labor ranges**: Values outside the acceptable range defined in the schema.
- **Odometer regression**: Within a single asset, any event whose odometer reading is lower than a chronologically earlier event.
- **No usable contact channel**: A contact row with no valid email and no valid phone.
- **Extreme labor hours**: Labor hours exceeding a schema-defined threshold.

### 6. Identify quarantined records

Records with any quality issue that disqualifies them from normalized totals. Common quarantine conditions:
- Unrecognized category (cannot be assigned to exactly one canonical category)
- Invalid physical measures (non-positive)
- No usable contact channel
- Timestamps that cannot be parsed or fall outside the business period (for maintenance events)

Quarantined records are excluded from normalized volume/spend/summary totals but are still reported in quarantine lists and counts.

### 7. Normalize measures

Use the reference endpoints to convert raw values into canonical units:

- `GET /api/reference/aliases` — maps free-text descriptions to canonical categories (fuel types, service classes). Each alias row has a `label` (the raw description text), a `canonical_value` (the recognized category), and a `category` (the domain: `fuel_type`, `service_class`).
- `GET /api/reference/conversions` — provides conversion factors between units (e.g., gallons to liters, miles to kilometers, pounds to kilograms). Each row has a `from_unit`, `to_unit`, and `factor`.
- `GET /api/reference/fx` — provides exchange rates for converting foreign-currency amounts to the base currency (typically USD).

Apply conversions: multiply the raw value by the conversion factor. Apply FX: multiply the raw amount by the rate. Round normalized monetary values and physical measures to the precision specified in the answer contract (typically 2 decimal places).

### 8. Assign control codes

Internal control codes are deterministic mappings from evidence patterns. The allowed code values for each domain are defined in the answer template's enum constraints. Infer the correct code by matching the evidence pattern, not by memorizing task-specific answers.

Code families that appear across domains:
- **Reference-policy codes** (e.g., RB-17, RB-42, RB-83): assigned based on whether the alias mapping is exact/unambiguous (RB-42), the reference itself is provisional or deprecated (RB-17), or the reference is exotic/unclassified (RB-83).
- **Source-basis / source-retention codes** (e.g., SB-24, SB-61, SB-79): assigned to each retained transaction row based on whether it survived as a single-snapshot record (SB-24), an authoritative-snapshot survivor from a multi-snapshot group (SB-61), or was reconciled from the provisional snapshot when no certified version existed (SB-79).
- **Ledger-disposition / ledger-routing codes** (e.g., LD-14, LD-31, LD-53, LD-72, LD-88): assigned based on the record's quality classification — quarantined (LD-14 or LD-88), valid mismatch (LD-31), valid/no issues (LD-53 or LD-72).

**Contact-domain codes:**
- **Identity codes** (IC-25, IC-40, IC-70, IC-90): single-source clear (IC-25), quarantined (IC-40), merged across systems with field-level precedence (IC-70), merged within the same source system (IC-90).
- **Outreach codes** (OR-15, OR-35, OR-60, OR-80): inactive (OR-15), granted consent with usable channel (OR-35), no usable contact (OR-60), pending/denied consent with usable channel (OR-80).
- **Field-provenance codes** (FP-20, FP-55, FP-75): single-source record (FP-20), multi-source merged with precedence (FP-55), quarantined/contested record (FP-75).

**Maintenance-domain codes:** Assigned by the schema's source-system rules; infer from the event's source provenance and history routing patterns in the data.

When uncertain about a code, read the schema's code assignments, re-examine the evidence rows for the anchor case, and apply the pattern consistently across all rows in the same evidence class.

### 9. Compute metrics and summaries

- **Raw row count**: total rows fetched before deduplication.
- **Logical record count**: distinct logical IDs after deduplication.
- **Valid count**: non-quarantined logical records.
- **Mismatch count**: valid records with an expected-vs-actual category mismatch.
- **Unrecognized count**: records whose description maps to zero or multiple canonical categories.
- **Quarantine count / rate**: quarantined records relative to a contract-defined base.
- **Normalized totals**: sum physical measures and spend only over valid (non-quarantined) records, rounded to contract precision.

### 10. Certification decision

Apply the thresholds from `case_scope.json`:
- If `quarantine_rate <= pass_max_quarantine_rate` → `PASS` / `RELEASE`
- If `quarantine_rate <= pass_with_exceptions_max_quarantine_rate` → `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`
- Otherwise → `HOLD` / `BLOCK_AND_REMEDIATE`

For maintenance events, the presence of odometer regression may gate to `HOLD` regardless of other metrics. For contact readiness, the absence of dispatchable people in any region may gate to `HOLD`.

Use the `status_action_map` in the case scope when present; when absent, infer the mapping from the answer contract's enum values for status and action.

### 11. Produce the answer

Write one JSON object conforming exactly to `payloads/answer_template.json`. Respect all:
- `required` key sets
- `enum` constraints on codes
- `pattern` constraints on ID formats
- `minItems`/`maxItems` array lengths
- `additionalProperties: false` — no extra keys
- `uniqueItems` on arrays
- Array ordering rules (in the contract's `x-ordering_rules` or prose descriptions)
- Numeric precision (`multipleOf`, decimal-place descriptions)
- Lexicographic sorting for ID lists
- Case-insensitive or ascending ordering for scored rankings

## References

- [API Endpoints](references/api_endpoints.md) — detailed endpoint reference with response shapes and query patterns
- [Contact Merging](references/contact_merging.md) — field-level precedence rules for merging contacts across HR Directory, Dispatch, and Identity Registry source systems
