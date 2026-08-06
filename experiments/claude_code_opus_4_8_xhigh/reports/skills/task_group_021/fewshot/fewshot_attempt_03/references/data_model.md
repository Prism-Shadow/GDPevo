# Data model — logical views (from `GET /api/catalog/schema`)

The hub exposes one SQL view per family plus reference views. All are queryable via
`POST /api/query`. `collection_id` scopes a business dataset; `snapshot_id` identifies
the source snapshot a raw row came from. The same logical record (same business key)
can appear in more than one snapshot — that is the overlap you must reconcile.

## v_contacts  (family: contacts — partner_onboarding, field_service_roster, dealer_contacts, warranty_contacts, ...)
`collection_id, row_id, snapshot_id, source_system, source_record_id,
person_or_org_name, email, phone, city, region, country, consent_status,
record_status, verified_flag, business_updated_at, ingested_at, master_hint`
- Business key for identity resolution: the **person** (match on normalized
  email / phone / name), NOT `row_id`. `row_id` is the public stable ID (e.g. `PAR-C00001`).
- `master_hint`: non-null on the designated golden/master row of a cluster (e.g. `MH-0000`).
  A shared value like `SHARED-HELPDESK` instead signals a *contested/shared identifier*.
- `consent_status ∈ {GRANTED, PENDING, DENIED, UNKNOWN}`; `record_status ∈ {ACTIVE, INACTIVE}`.
- Typical snapshots: three source systems, e.g. s01 CERTIFIED, s02 PROVISIONAL, s03 CERTIFIED.

## v_fuel_transactions  (family: fuel)
`collection_id, transaction_id, snapshot_id, asset_id, merchant_id, purchased_at,
expected_fuel_type, purchased_description, quantity, quantity_unit, currency, amount,
record_status, business_updated_at, ingested_at`
- Business key: `transaction_id` (e.g. `FT-202601-000001`).
- Recognized fuel categories: BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED.
- `quantity_unit ∈ {L, US_GAL, IMP_GAL}` → normalize to L. `currency` → normalize to USD.

## v_freight_charges  (family: freight)
`collection_id, charge_id, snapshot_id, invoice_id, invoice_line_no, carrier_id,
lane_id, service_date, expected_service_class, description, billed_weight, weight_unit,
distance, distance_unit, currency, amount, record_status, business_updated_at, ingested_at`
- Business key: `charge_id` (e.g. `FC-202602-000001`).
- Recognized service classes: EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD.
- `weight_unit ∈ {KG, LB}` → KG; `distance_unit ∈ {KM, MI}` → KM; `currency` → USD.

## v_maintenance_events  (family: maintenance)
`collection_id, snapshot_id, event_id, work_order_id, asset_id, event_type,
event_time_raw, odometer_value, odometer_unit, labor_hours, parts_cost, currency,
technician_id, event_status, business_updated_at, ingested_at`
- Business key: `event_id` (e.g. `ME-Q1-000001`). **No `source_system` column** — snapshot
  origin comes from joining to `v_source_snapshots` on `snapshot_id`.
- `odometer_unit ∈ {KM, MI}` → normalize with conversions `kind='odometer'`.
- `event_time_raw` may be NULL or unparsable (a data-quality defect).

## v_source_snapshots
`collection_id, snapshot_id, source_system, snapshot_status, business_cutoff,
created_at, ingested_at, row_count, checksum`
- `snapshot_status ∈ {CERTIFIED, PROVISIONAL}`. The **authoritative** snapshot for a
  collection is the CERTIFIED one, whose id is `<collection_id>-certified`
  (report it as `authoritative_snapshot_id`).

## v_reference_aliases
`domain, alias_id, alias_text, canonical_value, valid_from, valid_to,
reference_status, published_at`
- `reference_status ∈ {ACTIVE, INACTIVE, PROVISIONAL}`. Maps a free-text token
  (`alias_text`) to a `canonical_value`. See `reconciliation.md` for as-of filtering.

## v_unit_conversions
`kind, from_unit, to_unit, factor, valid_from, valid_to, precision`
- `factor` multiplies source unit → canonical (`to_unit`). Kinds: `volume`→L, `weight`→KG,
  `distance`→KM, `odometer`→KM. Identity rows (e.g. L→L) have factor 1.0.
- Known factors: US_GAL→L 3.785411784, IMP_GAL→L 4.54609, LB→KG 0.45359237, MI→KM 1.609344.

## v_fx_rates
`rate_date, currency, usd_per_unit, rate_status, published_at`
- `rate_status ∈ {CERTIFIED, PROVISIONAL}`. `usd_per_unit` = USD value of one unit of
  `currency` on `rate_date`. **USD itself has a rate that is not exactly 1.0** — always
  look it up; never assume USD==1. Use the CERTIFIED rate for the record's business date.
