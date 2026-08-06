# Per-family reconciliation

## Common skeleton
raw rows (across snapshots, ≤ cutoff) → pick authoritative snapshot → dedup to logical records → classify each → normalize units + FX → aggregate (exclude quarantined; include valid mismatches) → rank → code → certify.

Authoritative snapshot selection: prefer `snapshot_status` CERTIFIED > PROVISIONAL > STALE; tie-break by newest `created_at` then `ingested_at`. The retained occurrence of any duplicate logical record is the one from the authoritative snapshot.

---

## Fuel (family: `fuel`) — view `v_fuel_transactions`
- Canonical fuel types come from the template enum (e.g. BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED).
- Map `purchased_description` → canonical fuel_type via `v_reference_aliases` `domain=fuel` (`alias_text` → `canonical_value`). Outcomes: recognized (1 match), unrecognized (0), ambiguous (>1).
- **Mismatch**: recognized canonical ≠ `expected_fuel_type`. Valid — counts in totals.
- **Quarantine**: invalid quantity (≤ 0 or unconvertible unit). Excluded from totals.
- Normalize `quantity` → L (`conversions kind=volume`), `amount` → USD (`fx`).
- Rollups: per focus asset (logical/valid/mismatch/quarantine/exception counts + `volume_l` + `spend_usd`); top-N merchants by `exception_count` (a logical transaction that is a mismatch OR quarantined) DESC, `merchant_id` ASC. `mismatch_count` and `quarantine_count` are reported per merchant.
- `unrecognized_transaction_ids` includes zero-match AND ambiguous cases (one combined list).
- Code panels: reference_policy (`RB-*`) for reference IDs, source_basis (`SB-*`) and ledger_disposition (`LD-*`) for transaction IDs.

---

## Freight (family: `freight`) — view `v_freight_charges`
- Canonical service classes from the template enum (e.g. EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD).
- Map `description` → service class via aliases `domain=freight` (`FRA-*` alias IDs).
- **Mismatch**: recognized class ≠ `expected_service_class`. Valid — counts in totals, and its spend counts toward carrier mismatch exposure.
- **Quarantine**: unrecognized/ambiguous class, nonpositive `billed_weight`, or nonpositive `distance`. Excluded from totals. `quarantine_reason_counts` partitions these into `ambiguous_alias`, `invalid_distance`, `invalid_weight`, `unrecognized_alias`.
- Normalize `billed_weight` → KG (`kind=weight`), `distance` → KM (`kind=distance`), `amount` → USD (`fx`).
- Duplicate groups: one object per `charge_id` with multiple raw occurrences; `snapshot_ids` sorted; `retained_snapshot_id` = authoritative.
- Carrier ranking: by `mismatch_spend_usd` (USD on valid class mismatches) DESC, `carrier_id` ASC; include `mismatch_count`, `quarantine_count`, `exception_count` (distinct retained charges that are a valid mismatch or quarantined). `rank` 1-indexed, length = `carrier_ranking_limit`.
- Code panels: `reference_rows` (`RB-*`) for alias IDs, `source_retention` (`SB-*`) and `ledger_routing` (`LD-*`) for charge IDs.

---

## Contacts (family: `contacts`) — view `v_contacts`
Two variants share the same mechanics: partner-onboarding contact-master certification and field-service roster contact-readiness.

- Merge duplicate clusters (same person across `source_systems`). Survivor / `master_id` = chosen row ID (prefer authoritative snapshot; respect `master_hint`, `verified_flag`, and source-system precedence).
- Canonical fields:
  - `canonical_email` = trimmed, Unicode NFKC, lowercase.
  - `canonical_phone_digits` = digits only (string).
  - `canonical_name` = Unicode-preserving display name.
  - `canonical_city` / depot (`region`) per source-system precedence; record the supplying `*_source_system`.
- `member_row_ids` = all rows resolved to the person, sorted lexicographically.
- **No-usable-contact / quarantine**: a row/person with no usable email AND no usable phone.
- **Channel readiness**: an entity is eligible only when `record_status` = ACTIVE and it retains ≥ 1 usable email or phone; a channel is ready only when `consent_status` = GRANTED. Partitions: `both` / `email_only` / `phone_only` / `not_ready` (mutually exclusive across readiness-eligible canonical entities).
- **Contested identifiers**: watchlist cases that cannot auto-merge → `CONTESTED_NO_AUTOMERGE`; list the contested case IDs.
- **Inactive exclusion**: inactive entities are excluded from readiness-eligible counts (record the applicable outreach/exclusion code if the template requires it).
- Rollups:
  - By region: `canonical_entity_count` per region.
  - By depot/region: `total_person_count` split into `dispatchable_person_count`, `blocked_consent_count` (active + usable channel + non-granted consent), `blocked_no_contact_count` (no usable channel), `blocked_inactive_count` (inactive + usable channel); the four dispositions sum to total.
- `resolution_outcome` per focus person: `FIELD_LEVEL_PRECEDENCE_APPLIED` | `SINGLE_SOURCE` | `CONTESTED_NO_AUTOMERGE` | `NO_USABLE_CONTACT`.
- Code panels: identity (`IC-*`), outreach (`OR-*`), field_provenance (`FP-*`) — assigned per focus cluster / control case / readiness partition / quarantine result / inactive exclusion exactly as the template requires.
- Certification: `quarantine_rate = quarantined / canonical_entities`; map through the scope's `status_thresholds` (e.g. `pass_max_quarantine_rate`, `pass_with_exceptions_max_quarantine_rate`) to PASS / PASS_WITH_EXCEPTIONS / HOLD, then `status_action_map` → action.

---

## Maintenance (family: `maintenance`) — view `v_maintenance_events`
- Integrity issue counts: `missing_timestamp`, `invalid_timestamp`, `invalid_odometer`, `negative_labor`, `extreme_labor`, `odometer_regression`.
- **`invalid_event_ids`**: events rejected for missing/unparsable time, invalid odometer range, or invalid labor range. Sequence-only odometer regressions are NOT listed here — they appear in `corrected_metrics`.
- Dedup across snapshots → `duplicate_groups`: `logical_event_id`, `snapshot_ids` (unique, sorted), `retained_event_id`, `retained_snapshot_id` (authoritative). Sort by `logical_event_id` ascending.
- **`corrected_metrics`**:
  - `valid_event_count`.
  - `total_distance_km` = Σ over assets of (last reliable odometer reading − first reliable odometer reading) in the reconstructed history, converted to KM, rounded to exactly the scope's precision (typically 2 dp).
  - `regression_asset_ids`, `regression_event_ids` (unique, lexicographically sorted).
- Convert odometer to KM via `conversions kind=distance`. A "reliable" reading excludes invalid-odometer and invalid-timestamp events; regressions are excluded from the distance sum but reported as regressions.
- Asset risk ranking: per the scope policy (e.g. `rejected_event_count` DESC, then `regression_event_count` DESC, then `asset_id` ASC); top `limit` (e.g. 5); `rank` 1-indexed.
- Code panels: `maintenance_source` (`MS-*`) and `history_route` (`HR-*`) per scoped `event_id`, sorted by `event_id` ascending.
- Certification gate: often hard-coded in the scope (e.g. any odometer regression ⇒ status HOLD ⇒ action BLOCK_AND_REMEDIATE); apply `certification_gate` from the scope rather than recomputing a rate.
