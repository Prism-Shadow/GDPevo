# API Query Guide

## Base URL and Auth

From `environment_access.md`:
- Base URL: `http://task-env:9021/`
- Authorization: `Bearer asteria-read-021`
- Header: `Authorization: Bearer asteria-read-021`

## Allowed Endpoints

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/catalog/collections` | GET | Lists all collections with family, source_systems, time range, record count |
| `/api/catalog/schema` | GET | Describes all logical views and their fields |
| `/api/contacts` | GET | Contact rows (requires collection_id filter) |
| `/api/transactions/fuel` | GET | Fuel transaction rows |
| `/api/transactions/freight` | GET | Freight charge rows |
| `/api/maintenance/events` | GET | Maintenance event rows |
| `/api/reference/aliases` | GET | Reference aliases for domain matching |
| `/api/reference/conversions` | GET | Unit conversion factors |
| `/api/reference/fx` | GET | Foreign exchange rates |
| `/api/source-snapshots` | GET | Snapshot metadata per collection |
| `/api/query` | POST | SQL query interface (primary data access method) |

## Primary Query Method: POST /api/query

The `/api/query` endpoint accepts SQL queries:

```json
POST /api/query
Content-Type: application/json
Authorization: Bearer asteria-read-021

{"query": "SELECT * FROM v_contacts WHERE collection_id = 'partner_onboarding_2026w03' LIMIT 500 OFFSET 0"}
```

### Response Format
```json
{
  "columns": ["collection_id", "row_id", "snapshot_id", ...],
  "row_count": 500,
  "rows": [
    ["partner_onboarding_2026w03", "PAR-C00001", "partner_onboarding_2026w03-s01", ...],
    ...
  ],
  "truncated": false
}
```

### Pagination
- Use `LIMIT 500 OFFSET n` for pagination
- Keep incrementing offset until fewer than 500 rows returned
- `truncated: false` with < 500 rows means all data fetched

### Available Views

| View | Key Fields | Description |
|------|-----------|-------------|
| `v_contacts` | row_id, snapshot_id, source_system, person_or_org_name, email, phone, city, region, consent_status, record_status, verified_flag, master_hint | Contact records from multiple source systems |
| `v_fuel_transactions` | transaction_id, snapshot_id, asset_id, merchant_id, purchased_at, expected_fuel_type, purchased_description, quantity, quantity_unit, currency, amount | Fuel purchase records |
| `v_freight_charges` | charge_id, snapshot_id, carrier_id, lane_id, service_date, expected_service_class, description, billed_weight, weight_unit, distance, distance_unit, currency, amount | Freight charge lines |
| `v_maintenance_events` | event_id, snapshot_id, asset_id, event_type, event_time_raw, odometer_value, odometer_unit, labor_hours, parts_cost, currency, technician_id, event_status | Maintenance log entries |
| `v_reference_aliases` | domain, alias_id, alias_text, canonical_value, valid_from, valid_to, reference_status | Alias-to-canonical mapping |
| `v_source_snapshots` | collection_id, snapshot_id, source_system, snapshot_status, business_cutoff, created_at, row_count, checksum | Snapshot metadata |
| `v_unit_conversions` | kind, from_unit, to_unit, factor, valid_from, valid_to, precision | Unit conversion factors |
| `v_fx_rates` | rate_date, currency, usd_per_unit, rate_status, published_at | FX rates to USD |

## Critical Patterns

### Snapshot Priority
CERTIFIED > PROVISIONAL > STALE. Within same status, prefer earliest `created_at` or lowest `snapshot_id`.

### Source System Authority (Contacts)
Compliance Master > Partner Portal > CRM (for most fields)
Identity Registry > HR Directory > Dispatch (for roster tasks)

### FX Rate Selection
- Prefer CERTIFIED rates over PROVISIONAL
- Use rate_date ≤ transaction date, latest available
- For USD base currency, rate = 1.0 (ignore API value ~1.005)

### Unit Conversion
Apply `factor` to convert from `from_unit` to `to_unit`:
- Volume: US_GAL → L (×3.785411784), IMP_GAL → L (×4.54609)
- Distance: MI → KM (×1.60934)
- Weight: LB → KG (×0.453592)

### Direct GET Endpoints
The direct GET endpoints (`/api/contacts`, `/api/transactions/fuel`, etc.) appear to require specific filter parameters that are not documented. Use `/api/query` with SQL instead as the primary access method.
