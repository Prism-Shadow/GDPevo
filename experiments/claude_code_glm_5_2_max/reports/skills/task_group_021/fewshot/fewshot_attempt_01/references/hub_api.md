# Hub API reference

All access details (base URL, bearer token, allowed-endpoint allowlist) come
from `environment_access.md` at runtime — do not hardcode them. Send
`Authorization: Bearer <token>` on every request. The base URL resolves the
prompt's `<TASK_ENV_BASE_URL>` placeholder.

## Endpoint behavior (verified against the live hub)

### `GET /api/catalog/collections`
Returns `{"items":[...]}`. Each collection has: `collection_id`, `family`
(`fuel` / `freight` / `maintenance` / `contacts` / `quote` / …), `description`,
`source_systems[]`, `time_start`, `time_end`, `approximate_record_count`.
Use it to confirm the case-scope `collection_id` exists and to learn the
`family` (drives which playbook applies) and source systems.

### `GET /api/catalog/schema`
Returns `{"views":[{name, fields:[{name, meaning, type}]}]}`. Known views:

- `v_fuel_transactions`
- `v_freight_charges`
- `v_maintenance_events`
- `v_contacts`
- `v_reference_aliases`
- `v_unit_conversions`
- `v_fx_rates`
- `v_source_snapshots`

Read the relevant view's fields/meanings before interpreting rows. Field names
in rows match the view's `name` values; `meaning` explains each source field.

### `GET /api/source-snapshots?collection=<id>`
**Filter param is `collection`** (not `collection_id`). Returns
`{"items":[...], "limit", "offset", "total"}`. Each snapshot has:
`snapshot_id`, `snapshot_status` (`CERTIFIED` | `PROVISIONAL` | `STALE`),
`collection_id`, `source_system`, `business_cutoff`, `created_at`,
`ingested_at`, `row_count`, `checksum`.

- **Authoritative snapshot** = the one with `snapshot_status` CERTIFIED and
  `business_cutoff` matching the case-scope cutoff. Its `snapshot_id` is the
  `authoritative_snapshot_id` you report.
- `authoritative_row_count` (where the contract asks for it) = the CERTIFIED
  snapshot's `row_count`.
- `scoped_raw_row_count` / `raw_row_count` = sum of `row_count` across all
  in-scope snapshots (within cutoff), i.e. all raw rows you actually page.
- PROVISIONAL/STALE snapshots carry overlapping rows to be deduplicated against
  the authoritative one.

Snapshot-id naming varies by family: transactional families use
`<collection_id>-certified` / `-provisional`; some contact families use
`-s01` / `-s02`. Always key off `snapshot_status`, never the suffix.

### Data endpoints (paginated)
`GET /api/transactions/fuel`, `GET /api/transactions/freight`,
`GET /api/maintenance/events`, `GET /api/contacts` — all accept
`?collection=<id>&limit=<n>&offset=<n>` and return
`{"items":[...], "limit", "offset", "total"}`.

**Page until you have collected `total` items** (`offset += limit`). Each row
carries its own `snapshot_id`, `source_system`, `collection_id`, and the
family's logical id (`transaction_id` / `charge_id` / `event_id` / `row_id`),
plus a business-date field for cutoff filtering.

Confirmed row field sets (verify against the live schema each run):

- **`v_fuel_transactions`**: `transaction_id`, `collection_id`, `snapshot_id`,
  `source_system`, `asset_id`, `merchant_id`, `purchased_at`,
  `purchased_description`, `expected_fuel_type`, `quantity`, `quantity_unit`,
  `amount`, `currency`, `record_status`, `business_updated_at`, `ingested_at`.
  Note: `quantity` can be negative/nonpositive → invalid-quantity quarantine.
- **`v_contacts`**: `row_id`, `collection_id`, `snapshot_id`, `source_system`,
  `source_record_id`, `person_or_org_name`, `email`, `phone`, `city`, `region`,
  `country`, `consent_status`, `record_status`, `verified_flag`,
  `business_updated_at`, `ingested_at`, `master_hint`.

### `GET /api/reference/aliases`
Alias → canonical category/class maps (fuel types, freight service classes).
Used to resolve a free-text description / alias to exactly one recognized
canonical value. Read the response shape at runtime. Resolution outcomes:
**exactly one** recognized (usable), **zero** recognized (unrecognized), or
**more than one** recognized (ambiguous). Unrecognized and ambiguous both fail
"assign to exactly one recognized category".

### `GET /api/reference/conversions`
Unit conversion factors (e.g. gallons↔liters, lb↔kg, miles↔km). Use to convert
each record's `quantity_unit`/weight/distance unit to the canonical unit named
in `case_scope` (`L`, `KG`, `KM`).

### `GET /api/reference/fx`
FX rates to the base currency (`USD` in `case_scope`). Convert each record's
`amount`/`currency` to USD.

### `POST /api/query`
Authenticated ad-hoc query layer over the views. Its exact request-body
contract is not pinned by the staged materials; if you need server-side
filtered joins, discover the body shape by probing (it returns
`{"error":"invalid request"}` for malformed bodies). For all standard audit
work the GET endpoints above are sufficient — prefer them.
