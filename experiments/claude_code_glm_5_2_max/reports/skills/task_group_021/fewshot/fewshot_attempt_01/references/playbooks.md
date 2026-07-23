# Per-family playbooks

Each playbook lists the case-scope inputs, the contract's output sections, and
the family-specific reconciliation rules. Counts/IDs/codes are derived from live
records — none are stated here.

## A. Fuel purchases (`family: fuel`)

**Case-scope inputs:** `collection_id`, `cutoff_at`, `base_currency` (USD),
`canonical_volume_unit` (L), `focus_asset_ids[]`, `merchant_ranking_limit`,
`reference_decision_ids[]`, `transaction_decision_ids[]`.

**Logical key:** `transaction_id`. **Business date:** `purchased_at`.

**Quarantine conditions** (exclude from normalized totals):
- Description cannot be assigned to **exactly one** recognized fuel category via
  `/api/reference/aliases` — zero match (unrecognized) **or** >1 match
  (ambiguous). Report these in `unrecognized_transaction_ids` (zero + ambiguous
  together).
- Invalid quantity (nonpositive `quantity`).

**Mismatch:** recognized fuel type (from alias resolution of
`purchased_description`) ≠ `expected_fuel_type` on the record, and recognized is
exactly one. Mismatches are **valid** — included in normalized totals and in
merchant exception exposure.

**Outputs:** `audit_summary` (collection_id, cutoff_at, authoritative_snapshot_id,
raw/logical/duplicate/valid/mismatch/unrecognized/ambiguous/invalid_quantity/
exception counts, `exception_merchant_ranking`), `mismatch_transaction_ids`,
`unrecognized_transaction_ids`, `normalized_totals` (valid count, total_volume_l,
total_spend_usd, `fuel_type_totals` one row per fuel_type), `focus_assets` (one
per requested asset: logical/valid/mismatch/quarantine/exception counts + volume_l
+ spend_usd), `policy_decision_panel` (`reference_decisions` with `RB-*`, 6 per
`case_scope` order? — use `reference_decision_ids`, sorted; `transaction_decisions`
with `SB-*` + `LD-*`, per `transaction_decision_ids`, sorted), `reconciliation_status`.

**Ranking:** `exception_merchant_ranking` = top `merchant_ranking_limit` merchants
by `exception_count DESC, merchant_id ASC`; each row has merchant_id,
exception_count, mismatch_count, quarantine_count.

## B. Freight charges (`family: freight`)

**Case-scope inputs:** `collection_id`, `cutoff_at`, `base_currency`,
`canonical_weight_unit` (KG), `canonical_distance_unit` (KM),
`carrier_ranking_limit`, `reference_decision_alias_ids[]`,
`source_decision_charge_ids[]`, `ledger_decision_charge_ids[]`.

**Logical key:** `charge_id`. **Business date:** charge date field.

**Quarantine reasons** (report counts in `quarantine_reason_counts`):
`unrecognized_alias`, `ambiguous_alias` (alias cannot resolve to exactly one
service class), `invalid_weight` (nonpositive), `invalid_distance` (nonpositive).

**Mismatch:** recognized service class (from alias) ≠ expected service class,
recognized is exactly one. Valid mismatches enter normalized totals **and**
carrier exposure.

**Outputs:** `audit_summary` (incl. `quarantine_reason_counts` with the four
reason keys), `class_mismatch_charge_ids`, `quarantine_charge_ids`,
`duplicate_groups` (one per charge_id with >1 raw occurrence; charge_id,
raw_occurrence_count, snapshot_ids sorted, retained_snapshot_id),
`decision_panels` (`reference_rows` `RB-*` per alias_id; `source_retention`
`SB-*` per source_decision charge_id; `ledger_routing` `LD-*` per
ledger_decision charge_id — all sorted by id ascending, exact counts from
case_scope), `normalized_totals` (valid_charge_count, total_billed_weight_kg,
total_distance_km, total_spend_usd, `service_class_totals` one row per class),
`carrier_ranking`, `close_status`.

**Carrier ranking:** per carrier — `mismatch_count`, `mismatch_spend_usd`
(normalized USD on **valid** class-mismatch charges), `quarantine_count`,
`exception_count` (distinct retained charges that mismatch or are quarantined).
Order by `mismatch_spend_usd DESC, carrier_id ASC`, limit
`carrier_ranking_limit`; include 1-based `rank`.

## C. Maintenance events (`family: maintenance`)

**Case-scope inputs:** `case_id`, `collection_id`, `as_of`, `business_period`
(start/end), `event_decision_panel.event_ids[]` (+ ordering),
`corrected_distance_metric` (definition/unit/precision), `asset_risk_ranking`
(limit + sort: rejected_event_count DESC, regression_event_count DESC,
asset_id ASC), `certification_gate` (often a fixed odometer-regression
HOLD/BLOCK_AND_REMEDIATE).

**Logical key:** `event_id`. **Dedup:** across snapshots; retain authoritative.

**Issue categories** (report counts in `issue_counts`): `missing_timestamp`,
`invalid_timestamp`, `invalid_odometer`, `negative_labor`, `extreme_labor`,
`odometer_regression`.

**Invalid events** (`invalid_event_ids`): rejected for missing/unparseable time,
invalid odometer range, or invalid labor range. **Sequence-only odometer
regressions are NOT here** — they go in `corrected_metrics.regression_event_ids`.

**`corrected_metrics`:** `valid_event_count`; `total_distance_km` = sum across
assets of (last reliable odometer − first reliable odometer) in the reconstructed
history, rounded to the case-scope precision (2 dp); `regression_asset_ids`;
`regression_event_ids` (sequence-only regressions). Both id lists sorted
lexicographically.

**`duplicate_groups`:** one per `logical_event_id` appearing in ≥2 snapshots;
fields logical_event_id, snapshot_ids (sorted), retained_event_id,
retained_snapshot_id (authoritative).

**`event_decision_panel`:** one row per scoped `event_id` (sorted ascending) with
`MS-*` (maintenance_source) + `HR-*` (history_route) inferred from the event's
reconciled state.

**`source_decision`:** collection_id, as_of, authoritative_snapshot_id,
snapshot_status, authoritative_row_count (CERTIFIED snapshot row_count),
scoped_raw_row_count (all in-scope raw rows).

**`asset_risk_ranking`:** top assets per the case-scope sort, 1-based rank,
fields rank/asset_id/rejected_event_count/regression_event_count.

**Certification:** apply `certification_gate` (fixed gate overrides computed
thresholds).

## D. Contacts — partner-onboarding certification (`family: contacts`)

**Case-scope inputs:** `business_cutoff`, `case_id`, `collection_id`,
`control_case_anchors[]` (case_id + seed_row_ids), `focus_clusters[]`
(cluster_id + seed_row_id), `status_action_map`, `status_thresholds`
(`pass_max_quarantine_rate`, `pass_with_exceptions_max_quarantine_rate`).

**Logical identity:** cluster contact rows into canonical entities (by
identity/seed). Each cluster → one canonical entity with `survivor_row_id`
(the retained master row), `member_row_ids` (deduped, sorted),
`canonical_email` (lowercase), `canonical_phone_digits` (digits only),
`canonical_city` + `city_source_system` (source system that supplied the
surviving city).

**Quarantine** (`quarantine_row_ids`): contacts with **no usable email and no
usable phone**. Sorted lexicographically.

**Readiness:** an entity is **eligible** when active (`record_status` ACTIVE)
**and** has ≥1 usable email or phone. A channel is **ready** only when consent
is granted. `channel_readiness` partitions eligible entities into
both / email_only / phone_only / not_ready.

**Outputs:** `quality_summary` (raw_row_count, canonical_entity_count,
readiness_eligible_entity_count, duplicate_cluster_count, quarantine_rate =
quarantined ÷ canonical, 4 dp), `focus_clusters` (one per case-scope cluster,
sorted by cluster_id), `quarantine_row_ids`, `channel_readiness`,
`control_codes` (`focus_decisions` IC+FP per cluster; `anchored_cases`
IC+OR+FP per PC-ASTERIA case; `quarantine_result` IC+OR+FP;
`readiness_partition` OR per partition; `inactive_exclusion` OR),
`region_rollup` (canonical entities per region, sorted, all represented regions),
`certification_status` (status + next_action via thresholds + status_action_map).

## E. Contacts — field-service roster readiness (`family: contacts`)

**Case-scope inputs:** `case_id`, `collection_id`, `business_cutoff`,
`population_scope`, `depot_key_field` (region), `focus_people[]`
(focus_person_id + source_row_anchor), `identifier_watchlist[]`
(identifier_case_id + source_row_anchor), `policy_control_cases[]`
(control_case_id + control_family + evidence_row_ids).

**Sources:** HR Directory, Dispatch, Identity Registry. Merge into canonical
people with **field-level precedence**: for each canonical field, take the value
from the highest-precedence source system that supplies a usable value (derive
precedence from `verified_flag` / source reliability, not a hardcoded order),
and record that source system per field (`name_source_system`,
`contact_source_system`, `depot_source_system`, `consent_source_system`).
`master_id` = the surviving public row id used as the stable master.

**Canonical field rules:** `canonical_email` = trimmed Unicode NFKC lowercase;
`canonical_phone_digits` = digits only; `canonical_name` = Unicode-preserving;
`depot_code` = canonical value of the public region field.

**`resolution_outcome`** per focus person: `FIELD_LEVEL_PRECEDENCE_APPLIED` /
`SINGLE_SOURCE` / `CONTESTED_NO_AUTOMERGE` / `NO_USABLE_CONTACT`.

**`contested_cluster_ids`:** identifier-watchlist cases that remain contested
(from the allowed watchlist ids), sorted lexicographically.

**`dispatchable_master_ids`:** master ids of people who are active, have a usable
channel, **and** have consent granted. Sorted lexicographically, unique.

**`readiness_by_depot`:** per depot (region) — total_person_count,
dispatchable_person_count, blocked_consent_count (active + usable channel but
non-granted consent), blocked_no_contact_count (no usable channel),
blocked_inactive_count (inactive + usable channel). The four disposition counts
sum to total_person_count. Sorted by depot_code.

**`policy_control_cases`:** one per case-scope control case (sorted by
control_case_id), with control_family (IDENTITY/OUTREACH/FIELD_PROVENANCE),
evidence_row_ids (as supplied, sorted), and `control_code` from the matching
family prefix (IC/OR/FP) inferred from the evidence rows.

**`release_decision`:** status (PASS/PASS_WITH_EXCEPTIONS/HOLD) + action
(RELEASE/REVIEW_EXCEPTIONS/BLOCK_AND_REMEDIATE).

## Common contact readiness rules (both D and E)

- **Eligible** = active (`record_status` ACTIVE) **and** ≥1 usable email or
  phone.
- **Channel ready** only when consent is granted.
- **Quarantine / no-usable-contact** = no usable email and no usable phone.
- Inactive records with a usable channel are excluded from dispatch/readiness
  but tracked separately (inactive exclusion / blocked_inactive).
