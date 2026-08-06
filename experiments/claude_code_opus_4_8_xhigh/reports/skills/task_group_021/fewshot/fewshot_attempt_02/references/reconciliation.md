# Reconciliation playbook

The same pipeline underlies every task; only the family-specific validity rules
and the requested outputs change. Work in SQL against the logical views.

## 0. Scope
From `case_scope.json` take the `collection_id` and the business cutoff
(`business_cutoff` / `cutoff_at` / `as_of` / `business_period`). Everything is
filtered to that `collection_id`. List the collection's snapshots
(`/api/source-snapshots?collection=<id>`): typically one CERTIFIED and one or
more PROVISIONAL, each from a different `source_system`.

`raw_row_count` = total rows across all in-scope snapshots for the collection
(the sum of snapshot `row_count`s). Confirm with
`SELECT COUNT(*) FROM <view> WHERE collection_id='<id>'`.

## 1. De-duplicate into logical records
- **Fuel / freight / maintenance**: the business key (`transaction_id`,
  `charge_id`, `event_id`) is shared across snapshots. A key present in more than
  one snapshot is one *logical* record with duplicate raw rows.
  `logical_count = COUNT(DISTINCT key)`; `duplicate_raw_count = raw_row_count −
  logical_count`. **Retain the CERTIFIED copy** (snapshot precedence
  CERTIFIED > PROVISIONAL). A key found only in a provisional snapshot is still a
  valid logical record (retained from provisional).
- **Contacts**: each `row_id` is unique to its snapshot; there is no shared key.
  Duplicates are found by **matching normalized identifiers** — lowercase/trim
  email, digits-only phone (and name) — grouping matching rows into a cluster
  ("duplicate cluster"). Non-matching rows stand alone.

The `snapshot_id` provenance you compute here drives the `SB-*` / `MS-*` codes
(certified-only / both / provisional-only).

## 2. Validate → classify → quarantine
Apply the family's integrity rules to each logical record.

- **Fuel**: recognize `purchased_description` via `v_reference_aliases`
  (domain=fuel). *unrecognized* = matches no active alias; *ambiguous* = matches
  ≥2 distinct canonical values; *invalid_quantity* = quantity ≤ 0 or missing.
  Any of these → quarantine. A *mismatch* is a **valid** row whose recognized
  fuel type differs from `expected_fuel_type`.
- **Freight**: same idea on `description` (domain=freight) plus
  *invalid_weight* (billed_weight ≤ 0/missing) and *invalid_distance* (distance
  ≤ 0/missing). A *class mismatch* is a valid charge whose recognized service
  class differs from `expected_service_class`.
- **Maintenance**: integrity checks over `missing_timestamp`,
  `invalid_timestamp`, `invalid_odometer`, `negative_labor`, `extreme_labor`;
  plus `odometer_regression` (odometer decreases vs the asset's prior reliable
  reading, ordered by time). Rejected events are excluded from the corrected
  history.
- **Contacts**: a row/cluster with no usable email **and** no usable phone is
  quarantined (unusable). Inactive records are excluded from readiness.

`quarantine_rate` (where requested) = quarantined rows ÷ canonical entities,
rounded to the precision the template states.

## 3. Normalize (exclude quarantined records)
Convert to canonical units via `v_unit_conversions` (volume→L, weight→KG,
distance/odometer→KM) using the row's own `*_unit`. Convert money to USD via
`v_fx_rates` — `rate_status='CERTIFIED'`, keyed on the transaction/service
**business date** and `currency`; `usd = amount * usd_per_unit`. Sum only
valid (non-quarantined) records. Round to the precision declared in the
`answer_template` / `case_scope`. Group totals by recognized class where asked.

## 4. Canonicalize entities (contacts)
For each cluster pick the master record and build canonical field values with
**field-level precedence**: each output field (name, email, phone, city,
region/depot, consent, status) is taken from the source system that is
authoritative for that field, then normalized (email lowercased+trimmed; phone
digits-only). The `master_hint` column flags a designated master when present;
otherwise resolve by source precedence and recency (`business_updated_at`). The
answer records which `source_system` each canonical field came from
(`*_source_system`). Region/depot rollups count canonical entities per region.

## 5. Rank / roll up
Rankings (merchant / carrier / asset risk) use the primary sort and tie-breaks
spelled out in `case_scope.json` (e.g. exposure DESC, then ID ASC). "Exception"
and "exposure" definitions are given in the prompt — read them literally
(e.g. carrier exposure = normalized USD on **valid** class-mismatch charges;
quarantined charges never enter normalized totals but may count as exceptions).

## 6. Status / certification decision
Apply the thresholds and action map in `case_scope.json`. Example gate:
`quarantine_rate == 0` → PASS; `≤ pass_with_exceptions_max_quarantine_rate` →
PASS_WITH_EXCEPTIONS; else HOLD — then map status → next_action via
`status_action_map`. Some tasks instead gate on a single condition (e.g. any
odometer regression present → HOLD/BLOCK_AND_REMEDIATE). Use the scope's own
field names for `status`/`action`/`routing`/`next_action`.

## 7. Ordering, precision, output discipline
- Sort every stable-ID list and ranked array exactly as the template/scope says
  (usually lexicographic ASC for ID lists; the stated sort for rankings).
  Deduplicate sets; honour `uniqueItems`.
- Match numeric precision (`multipleOf`, `precision_decimal_places`) and keep
  fields typed as the schema declares (e.g. phone digits as a **string**).
- Emit exactly the object `answer_template.json` describes with
  `additionalProperties:false` — every required key, no extras, **JSON only**,
  no Markdown or commentary.
- Validate your JSON against the template (enums, patterns, min/max array
  lengths) before returning.
