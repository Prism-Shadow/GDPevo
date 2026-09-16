---
name: asteria-fleet-dq-hub
description: Navigate and audit the Asteria Fleet Data Quality Hub, a read-only operational data lake with collections of contacts, fuel transactions, freight charges, and maintenance events, plus reference data for aliases, unit conversions, and FX rates. Use when Codex needs to reconcile source snapshots, deduplicate entity clusters, normalize financial totals across currencies and units, resolve canonical contacts, classify transactions with alias lookups, detect data-quality issues (missing timestamps, odometer regressions, invalid quantities, unrecognized descriptions), apply internal control codes (identity, outreach, field-provenance, source-basis, ledger-disposition, maintenance-source, history-route codes), and produce structured certification answers. Also use when the task mentions "Asteria Fleet Data Quality Hub", "Fleet DQ Hub", or a task environment base URL pointing to a read-only data quality hub.
---

# Asteria Fleet Data Quality Hub

## Overview

You are auditing operational fleet data through a stateless read-only HTTP hub at the URL in `environment_access.md` (key `base_url`). The hub exposes collections through views you query with SQL via `POST /api/query`. Every audit produces a single machine-readable JSON answer matching the provided answer template — no commentary, no markdown wrapping.

## Quick Start

1. Read the task `prompt.txt` fully — identify the collection, cutoff, and answer template.
2. Read `payloads/case_scope.json` for business parameters (focus entities, decision panels, thresholds, ranking policies).
3. Read `payloads/answer_template.json` for the exact output shape, required fields, allowed enum values, and ordering rules.
4. Read `environment_access.md` for the base URL and any query credentials.
5. Discover the hub: `GET /api/catalog/schema` and `GET /api/catalog/collections`.
6. Query data through `POST /api/query` with JSON body `{"sql": "<query>"}`. Use the scripts helper for paginated queries.
7. Produce one JSON object conforming to every constraint in the answer template. Order lists per template rules (ascending sort, lexicographic for strings).

## Hub API

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/catalog/collections` | List all collections with family, source systems, time range, approximate row counts |
| GET | `/api/catalog/schema` | Unified schema for all views (field names, types, meanings) |
| GET | `/api/contacts` | Contact records (query param: `collection_id`) |
| GET | `/api/transactions/fuel` | Fuel transaction records (query param: `collection_id`) |
| GET | `/api/transactions/freight` | Freight charge records (query param: `collection_id`) |
| GET | `/api/maintenance/events` | Maintenance event records (query param: `collection_id`) |
| GET | `/api/reference/aliases` | Alias-to-canonical mappings for fuel types, service classes, and freight categories |
| GET | `/api/reference/conversions` | Unit conversion factors (kind, from_unit, to_unit, factor, precision) |
| GET | `/api/reference/fx` | FX rates with USD-per-unit values |
| GET | `/api/source-snapshots` | Snapshot metadata (query param: `collection_id`) |
| POST | `/api/query` | Execute read-only SQL against schema views. Include any credential from `environment_access.md`. |

### Views (from `/api/catalog/schema`)

- **v_contacts** — `collection_id`, `row_id`, `snapshot_id`, `source_system`, `source_record_id`, `person_or_org_name`, `email`, `phone`, `city`, `region`, `country`, `consent_status`, `record_status`, `verified_flag`, `business_updated_at`, `ingested_at`, `master_hint`
- **v_fuel_transactions** — `collection_id`, `transaction_id`, `snapshot_id`, `asset_id`, `merchant_id`, `purchased_at`, `expected_fuel_type`, `purchased_description`, `quantity`, `quantity_unit`, `currency`, `amount`, `record_status`, `business_updated_at`, `ingested_at`
- **v_freight_charges** — `collection_id`, `charge_id`, `snapshot_id`, `invoice_id`, `invoice_line_no`, `carrier_id`, `lane_id`, `service_date`, `expected_service_class`, `description`, `billed_weight`, `weight_unit`, `distance`, `distance_unit`, `currency`, `amount`, `record_status`, `business_updated_at`, `ingested_at`
- **v_maintenance_events** — `collection_id`, `snapshot_id`, `event_id`, `work_order_id`, `asset_id`, `event_type`, `event_time_raw`, `odometer_value`, `odometer_unit`, `labor_hours`, `parts_cost`, `currency`, `technician_id`, `event_status`, `business_updated_at`, `ingested_at`
- **v_reference_aliases** — `domain`, `alias_id`, `alias_text`, `canonical_value`, `valid_from`, `valid_to`, `reference_status`, `published_at`
- **v_source_snapshots** — `collection_id`, `snapshot_id`, `source_system`, `snapshot_status`, `business_cutoff`, `created_at`, `ingested_at`, `row_count`, `checksum`
- **v_unit_conversions** — `kind`, `from_unit`, `to_unit`, `factor`, `valid_from`, `valid_to`, `precision`
- **v_fx_rates** — `rate_date`, `currency`, `usd_per_unit`, `rate_status`, `published_at`

### Snapshot Resolution

Every collection has multiple snapshots. Resolve the authoritative source:

1. Query `v_source_snapshots` filtered by `collection_id`.
2. The authoritative snapshot is the one with `snapshot_status = 'CERTIFIED'` whose `business_cutoff` is on or before the task cutoff. If multiple certified snapshots exist, take the latest.
3. For most audits, filter all data queries to the certified snapshot.
4. For cross-snapshot deduplication: when the same logical ID (transaction_id, charge_id, event_id) appears in multiple snapshots, keep the certified occurrence and report the others as duplicates. Always prefer the certified snapshot's row.

### Querying

- Use `POST /api/query` with JSON `{"sql": "<SQL>"}`.
- The hub returns paginated results: check if `total` > number of returned `items`. If so, use `LIMIT` and `OFFSET` to page.
- Use [scripts/query_hub.py](scripts/query_hub.py) for deterministic paginated queries — it handles paging and returns the full result set.
- Reference data endpoints (`/api/reference/aliases`, `/api/reference/conversions`, `/api/reference/fx`) may or may not be paginated. Check response structure and page if needed.
- When using collection-specific endpoints like `/api/contacts`, supply the `collection_id` query parameter.

## Audit Patterns

### Contact Reconciliation

See [references/contact-rules.md](references/contact-rules.md) for the full deduplication, survivor selection, and readiness rules.

1. Load all contact rows from the certified snapshot.
2. Cluster into canonical people: match on normalized email (NFKC lowercase, trimmed), phone digits, and name similarity. The `master_hint` field indicates pre-grouped clusters when populated.
3. Select a survivor (master) row per cluster by source-system precedence and recency. Determine canonical field values by field-level source-system precedence.
4. Quarantine rows with no usable contact channel (null/empty email AND null/empty phone).
5. Compute readiness: an entity is eligible if `record_status = 'ACTIVE'` AND has at least one usable email or phone; a channel is ready only when `consent_status = 'GRANTED'`.
6. Apply control codes per [references/codes.md](references/codes.md).

### Transaction Audit (Fuel & Freight)

See [references/aliases.md](references/aliases.md) for alias lookup and classification rules.

1. Load all transactions/charges from the certified snapshot.
2. Load reference aliases for the relevant domain (`fuel` or `freight`), filtered by transaction dates against `valid_from`/`valid_to`.
3. Load unit conversions and FX rates for normalization.
4. For each row, resolve the recognized category by matching `purchased_description` / `description` against aliases (case-insensitive, trimmed). See [references/aliases.md](references/aliases.md) for the matching strategy.
5. Classification outcomes:
   - **Valid match**: Exactly one recognized canonical value.
   - **Unrecognized**: No matching alias.
   - **Ambiguous**: Multiple distinct canonical values match.
   - **Mismatch**: Valid match whose canonical value differs from `expected_fuel_type` / `expected_service_class`.
6. **Quarantine**: Unrecognized, ambiguous, non-positive quantity/weight/distance. Do NOT include quarantined rows in normalized totals.
7. **Mismatch rows** are valid (included in normalized totals) but tracked separately.
8. Normalize amounts to USD using the effective FX rate for each row's currency on or before the row's date, preferring `rate_status = 'final'`. Normalize quantities to canonical units (L for fuel, KG and KM for freight) using conversions.
9. For ranking: follow the ranking policy in `case_scope.json` (typically exception counts descending, then ID ascending as tiebreak).

### Maintenance Integrity

1. Load all maintenance events — from ALL snapshots for duplicate detection, from the certified snapshot for the authoritative data.
2. For each row, detect issues:
   - `missing_timestamp`: `event_time_raw` is null or empty.
   - `invalid_timestamp`: `event_time_raw` cannot be parsed as a UTC timestamp.
   - `invalid_odometer`: `odometer_value` is null or outside [0, 999999].
   - `negative_labor`: `labor_hours` < 0.
   - `extreme_labor`: `labor_hours` > 24.
   - `odometer_regression`: within an asset, events ordered by parsed `event_time` where `odometer_value` decreases (after converting to km). Check only among valid (non-rejected) events within the certified snapshot.
3. **invalid_event_ids**: Rows rejected for missing/invalid timestamp, invalid odometer, negative labor, or extreme labor. Odometer regression events are NOT rejected — they stay valid but are flagged in `corrected_metrics`.
4. Duplicates: same `event_id` across snapshots, retain certified.
5. Calculate corrected distance: sum across assets of (last valid odometer - first valid odometer), converting all odometer readings to km.
6. Asset risk ranking: per ranking policy in `case_scope.json`.
7. Apply decision codes per [references/codes.md](references/codes.md).

### Certification Decision

1. Compute the exception/quarantine rate as specified by the task (usually quarantined / canonical entities, or exception transactions / total logical count).
2. Compare against thresholds in `case_scope.json`:
   - If rate <= `pass_max_quarantine_rate` -> `PASS` / `RELEASE`.
   - If rate <= `pass_with_exceptions_max_quarantine_rate` -> `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`.
   - Otherwise -> `HOLD` / `BLOCK_AND_REMEDIATE`.
   - Some cases use hard gates (e.g., odometer regression always -> `HOLD` regardless of rate).
3. Apply the status/action mapping from `case_scope.json` or the `certification_gate` in the case scope.

## Resources

### scripts/
- [query_hub.py](scripts/query_hub.py) — Deterministic helper that executes paginated SQL queries against the hub and returns full result sets.

### references/
- [codes.md](references/codes.md) — Control/policy/decision code catalog and assignment rules.
- [aliases.md](references/aliases.md) — Alias domains, canonical categories, and lookup strategy.
- [contact-rules.md](references/contact-rules.md) — Contact deduplication, survivor selection, and channel readiness.

