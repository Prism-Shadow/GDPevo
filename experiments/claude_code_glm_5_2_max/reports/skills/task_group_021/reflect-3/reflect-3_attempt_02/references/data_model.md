# Hub data model reference

Confirm all view names and fields against the live catalog/schema endpoint at solve time (the schema is the source of truth). The views below are the hub's standard shape.

## v_source_snapshots
One row per source snapshot of a collection.

| field | meaning |
|---|---|
| `collection_id` | business collection identifier |
| `snapshot_id` | stable snapshot identifier |
| `source_system` | originating business system |
| `snapshot_status` | `CERTIFIED` / `PROVISIONAL` / `STALE` |
| `business_cutoff` | cutoff the snapshot was published against |
| `created_at` | snapshot creation time |
| `ingested_at` | time the snapshot entered the hub |
| `row_count` | row count reported by the snapshot |
| `checksum` | source checksum |

**Authoritative snapshot = the `CERTIFIED` one.** Retain its occurrence when a logical record appears in multiple snapshots.

## v_contacts
Raw contact records (partner onboarding, field-service roster, dealer/warranty contacts, etc.).

| field | meaning |
|---|---|
| `collection_id`, `row_id`, `snapshot_id`, `source_system` | identity / provenance |
| `source_record_id` | source-side record id |
| `person_or_org_name` | name (case/diacritics vary by source) |
| `email`, `phone` | contact channels (formatting and sentinels vary by source) |
| `city`, `region`, `country` | location (city can conflict across sources; region is usually consistent) |
| `consent_status` | `GRANTED` / `PENDING` / `DENIED` / `UNKNOWN` |
| `record_status` | `ACTIVE` / `INACTIVE` |
| `verified_flag` | source-verified flag (0/1) |
| `business_updated_at`, `ingested_at` | timestamps |
| `master_hint` | hint identifying the master/survivor row in a merged cluster (`MH-xxxx`) or a shared-identifier marker (e.g. `SHARED-HELPDESK`) |

## v_fuel_transactions / v_freight_charges
Raw transactional charge/line rows.

Common fields: `collection_id`, `<transaction_id|charge_id>`, `snapshot_id`, `record_status`, `business_updated_at`, `ingested_at`, plus:
- identity: `asset_id` / `merchant_id` (fuel) or `carrier_id` / `lane_id` / `invoice_id` / `invoice_line_no` (freight)
- `service_date` / `purchased_at` — business date (drives FX rate selection)
- `expected_fuel_type` / `expected_service_class` — expected canonical category
- `description` / `purchased_description` — free text to resolve via aliases
- measures: `quantity`+`quantity_unit` (fuel volume) or `billed_weight`+`weight_unit` and `distance`+`distance_unit` (freight)
- `currency`, `amount`

## v_maintenance_events
Raw maintenance log rows.

Fields: `collection_id`, `snapshot_id`, `event_id`, `work_order_id`, `asset_id`, `event_type`, `event_time_raw` (raw timestamp string — may be missing or unparseable), `odometer_value`+`odometer_unit`, `labor_hours`, `parts_cost`, `currency`, `technician_id`, `event_status`, `business_updated_at`, `ingested_at`.

## v_reference_aliases
Maps free-text descriptions to canonical categories. `domain` is `fuel` or `freight`.

| field | meaning |
|---|---|
| `domain` | `fuel` / `freight` |
| `alias_id` | stable alias id (e.g. `FUA-003`, `FRA-002`) |
| `alias_text` | the text to match inside a description |
| `canonical_value` | the canonical category the text maps to |
| `valid_from`, `valid_to` | temporal validity window (valid_to null = unbounded) |
| `reference_status` | `ACTIVE` / `INACTIVE` / `PROVISIONAL` |
| `published_at` | publication time |

Watch for: the **same `alias_text` redefined over time** (two rows, different `canonical_value`, different validity windows and statuses) and `PROVISIONAL`/`INACTIVE` rows. Resolve using the row that is `ACTIVE` and temporally valid on the record's business date.

## v_unit_conversions
`kind` ∈ {`volume`, `weight`, `distance`, `odometer`}; `from_unit`→`to_unit` with `factor`; temporally bounded; `precision`. Use the factor from this table (do not hardcode). Canonical targets: volume→`L`, weight→`KG`, distance→`KM`, odometer→`KM`.

## v_fx_rates
`rate_date`, `currency`, `usd_per_unit` (USD value of one unit of `currency`), `rate_status` (`CERTIFIED`/`PROVISIONAL`), `published_at`. Per-date, per-currency; both statuses can exist for a date. Use the **CERTIFIED** rate for the record's business date; fall back to PROVISIONAL only if no CERTIFIED rate exists. USD rows exist and hover near 1.0 — apply them like any other currency.
