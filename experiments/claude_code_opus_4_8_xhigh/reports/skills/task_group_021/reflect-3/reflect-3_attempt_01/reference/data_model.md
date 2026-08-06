# Data model & per-family field notes

Discover the exact catalog/schema at run time; this is the recurring shape.

## Source snapshots (`v_source_snapshots`)
- One collection = several snapshots, one per `source_system`.
- `snapshot_status` ∈ {CERTIFIED, PROVISIONAL, STALE}. The **authoritative** snapshot is the
  CERTIFIED one valid as of the cutoff. PROVISIONAL rows are still part of the raw population
  but never win survivorship and are never the authority. Ignore STALE.
- `business_cutoff` on the snapshot should match the case cutoff; `row_count` gives
  `authoritative_row_count` for the certified snapshot.

## Reference tables (validity-scoped — always filter)
- `v_reference_aliases(domain, alias_text, canonical_value, valid_from, valid_to, reference_status)`
  — apply only ACTIVE aliases whose window contains the row's business date. INACTIVE,
  expired, provisional, or future-effective aliases do not apply (common trap: a "priority"
  alias that only becomes effective next month, plus an expired duplicate).
- `v_unit_conversions(kind, from_unit, to_unit, factor, valid_from, valid_to, precision)`
  — kind ∈ volume/weight/distance/odometer. Multiply source value by `factor` → canonical unit.
- `v_fx_rates(rate_date, currency, usd_per_unit, rate_status)` — pick the row's business date;
  prefer CERTIFIED over PROVISIONAL; USD = 1.0.

## Contacts family (`v_contacts`) — MDM / identity resolution
- No cross-source stable id. Match key = **normalized email**; each usable row without an email
  falls back to being unmergeable (its own record). Unusable (no email AND no phone) →
  quarantined, one record each.
- Sources typically: one identity/compliance "master" (carries `master_hint`, CERTIFIED),
  an HR/roster source (CERTIFIED), and a dispatch/CRM source (PROVISIONAL, often a decoy city).
- `master_hint` values: `MH-####` marks the golden row of a clean multi-source cluster;
  `SHARED-HELPDESK` marks a phone shared by many identities (a contested identifier, never a
  merge); `NOISY-*` marks intentionally noisy singletons.
- Field-level precedence (report each field's winning `*_source_system`):
  name → the accent-preserving certified source, Title-Cased; email/phone → the identity
  master (clean digits); city/region(depot) → the HR/roster source; consent + record_status →
  the identity master.
- `canonical_*_count` **includes** quarantined people. Region/depot rollups cover the full
  canonical set. Readiness/dispatchable: dispatchable = ACTIVE ∧ usable canonical channel ∧
  consent GRANTED; buckets (dispatchable / blocked_consent / blocked_no_contact /
  blocked_inactive) partition the depot total.

## Fuel & freight families (`v_fuel_transactions`, `v_freight_charges`) — transaction audit
- Cross-snapshot duplicates share a stable id (`transaction_id`; `charge_id`, which equals
  `invoice_id`+`invoice_line_no`). `logical_count` = distinct id; `duplicate_raw_count` =
  raw − logical; retain the CERTIFIED occurrence.
- Category/class from free-text description via `v_reference_aliases` (word boundary +
  maximal span, active+in-window). recognized(1) / unrecognized(0) / ambiguous(>1).
- Quarantine = unresolved class (unrecognized ∪ ambiguous) ∪ non-positive/nan physical measure
  (quantity; or billed_weight and distance). Report per-reason counts (they usually partition).
- Valid = recognized-unique ∧ valid measures. Valid class mismatches (recognized ≠ expected)
  ARE valid and enter totals under the **recognized** category. Quarantined never enter totals.
- Normalize: volume/weight/distance via conversions; amount → USD via FX on the row's date.
- `record_status` REVIEW rows are usually already the bad-data rows (they still count in raw
  and are quarantined by class/measure); REVIEW itself is not a separate quarantine reason.
- Rankings (merchant/carrier): by exposure/exception then id ascending; exception = valid
  mismatch ∨ quarantined.

## Maintenance family (`v_maintenance_events`) — history integrity
- Certified (ERP) + provisional (mobile) snapshots; dedup logical events by `event_id`,
  retain certified. Report duplicate groups.
- Issue detection over the **deduped/retained** events (raw counting scored worse):
  missing_timestamp (null/empty), invalid_timestamp (present but unparsable, e.g. impossible
  date), invalid_odometer (null/negative), negative_labor (<0), extreme_labor (clear high
  outlier band, e.g. all far above the normal max), odometer_regression (reading below the
  running max within an asset's time-ordered valid history).
- `invalid_event_ids` = the hard rejects (NOT regressions — those go in corrected_metrics).
- `total_distance_km` = Σ over assets of (last − first reliable odometer) in time order,
  converted to km. Ranking: rejected_event_count DESC, regression_event_count DESC, asset_id ASC.
- Certification gate from case_scope (e.g. any regression → HOLD/BLOCK_AND_REMEDIATE).
