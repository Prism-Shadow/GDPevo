# Domain map — known collection families

Each Asteria audit targets one collection family. The family determines the domain view, the reference data used, the control-code families to infer, the focus / ranking shape, and the certification source. Match the task's collection to a family below; if none match, fall back to the universal procedure (read schema + case_scope + answer_template).

Concrete collection IDs and ID prefixes below are illustrative patterns — always use the actual IDs from the staged case_scope and the patterns from the answer_template.

## Fuel purchases (collection_id like `fuel_purchases_<YYYY_MM>`)
- View: `v_fuel_transactions`. GET `/api/transactions/fuel`.
- Reference: `v_reference_aliases` (fuel description → fuel_type), `v_unit_conversions` (volume → L), `v_fx_rates` (→ USD).
- Canonical fuel types: per the template enum (e.g. BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED).
- Mismatch: expected fuel_type vs alias-recognized fuel_type. Unrecognized = 0 alias matches; Ambiguous = >1. invalid_quantity = nonpositive / invalid volume.
- Focus: `focus_assets` (by asset_id ASC) — logical / valid / mismatch / quarantine / exception counts + volume_l + spend_usd.
- Ranking: top merchants by `exception_count` DESC then `merchant_id` ASC (limit = `merchant_ranking_limit`).
- Control-code panels (infer; not in task materials):
  - `reference_decisions` (reference IDs, e.g. `FUA-###`) → `reference_policy_code` ∈ {RB-17, RB-42, RB-83}.
  - `transaction_decisions` (transaction IDs, e.g. `FT-######-######`) → `source_basis_code` ∈ {SB-24, SB-61, SB-79} AND `ledger_disposition_code` ∈ {LD-14, LD-31, LD-53, LD-72, LD-88}.
- Certification: `reconciliation_status` {status, action}.

## Freight charges (collection_id like `freight_charges_<YYYY_MM>`)
- View: `v_freight_charges`. GET `/api/transactions/freight`.
- Reference: `v_reference_aliases` (service-class alias → service_class), `v_unit_conversions` (weight → KG, distance → KM), `v_fx_rates` (→ USD).
- Canonical service classes: per the template enum (e.g. EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD).
- Mismatch: expected vs recognized service_class. Quarantine reasons reported in `quarantine_reason_counts`: `unrecognized_alias`, `ambiguous_alias`, `invalid_weight`, `invalid_distance`.
- duplicate_groups: charge_id, raw_occurrence_count, snapshot_ids (lex), retained_snapshot_id; by charge_id ASC.
- Ranking: `carrier_ranking` — by `mismatch_spend_usd` DESC (USD on valid class-mismatch charges) then `carrier_id` ASC; fields mismatch_count, mismatch_spend_usd, quarantine_count, exception_count; rank 1..`carrier_ranking_limit`.
- Control-code panels:
  - `reference_rows` (alias IDs `FRA-###`) → RB-{17,42,83}.
  - `source_retention` (charge IDs) → SB-{24,61,79}.
  - `ledger_routing` (charge IDs) → LD-{14,31,53,72,88}.
- Certification: `close_status` {status, routing}.

## Maintenance events (collection_id like `maintenance_events_<YYYY>_q1`)
- View: `v_maintenance_events`. GET `/api/maintenance/events`. **Collection is larger than one page — paginate fully.**
- Reference: `v_unit_conversions` (distance → KM). Source snapshots resolve cross-snapshot duplicates.
- issue_counts: missing_timestamp, invalid_timestamp, invalid_odometer, negative_labor, extreme_labor, odometer_regression.
- `invalid_event_ids`: rejected for missing / unparsable time, invalid odometer range, or invalid labor range. **Sequence-only odometer regressions go in `corrected_metrics`, NOT `invalid_event_ids`.**
- duplicate_groups: logical_event_id, snapshot_ids (lex), retained_event_id, retained_snapshot_id; by logical_event_id ASC.
- corrected_metrics: valid_event_count, `total_distance_km` (2 dp; sum per asset of last − first reliable odometer reading in the reconstructed history), regression_asset_ids (lex), regression_event_ids (lex).
- Ranking: `asset_risk_ranking` — `rejected_event_count` DESC, `regression_event_count` DESC, `asset_id` ASC; rank ASC; limit from case_scope.
- Control-code panel: `event_decision_panel` (event IDs `ME-Q1-######`) → `maintenance_source_code` ∈ {MS-12, MS-47, MS-86} AND `history_route_code` ∈ {HR-19, HR-33, HR-74}; by event_id ASC.
- Certification: `certification_status` {status, action}; case_scope may give an explicit `certification_gate` (e.g. odometer_regression_status / action).

## Contacts — partner onboarding (collection_id like `partner_onboarding_<YYYY>w<WW>`)
- View: `v_contacts`. GET `/api/contacts`. Source systems (precedence per field): CRM, Compliance Master, Partner Portal.
- quality_summary: raw_row_count, canonical_entity_count, readiness_eligible_entity_count, duplicate_cluster_count, quarantine_rate (4 dp).
- focus_clusters: per cluster_id ASC — member_row_ids (dedup lex), survivor_row_id, canonical_email (lowercase), canonical_phone_digits, canonical_city, city_source_system.
- quarantine_row_ids: complete dedup lex set.
- channel_readiness: both / email_only / phone_only / not_ready over readiness-eligible (active + ≥1 usable channel; channel ready only if consent GRANTED).
- region_rollup: canonical_entity_count per region (regions = the template's region enum), by region ASC.
- Control codes (`control_codes` block): `focus_decisions` (IC + FP), `anchored_cases` (IC + OR + FP), `quarantine_result` (IC + OR + FP), `readiness_partition` (4× OR), `inactive_exclusion` (OR). Families: IC ∈ {IC-25, IC-40, IC-70, IC-90}, OR ∈ {OR-15, OR-35, OR-60, OR-80}, FP ∈ {FP-20, FP-55, FP-75}.
- Certification: `certification_status` {status, next_action} via status_action_map + thresholds (`pass_max_quarantine_rate`, `pass_with_exceptions_max_quarantine_rate`).

## Contacts — field-service roster (collection_id like `field_service_roster_<YYYY>w<WW>`)
- View: `v_contacts`. GET `/api/contacts`. Source systems (field-level precedence; report name / contact / depot / consent_source_system): HR Directory, Dispatch, Identity Registry.
- merge_summary: raw_row_count, canonical_person_count (incl. quarantined), merged_duplicate_cluster_count, quarantine_row_count, contested_identifier_cluster_count, dispatchable_person_count.
- focus_people (by focus_person_id ASC): full canonicalization + 4 source_system fields + `resolution_outcome` ∈ {FIELD_LEVEL_PRECEDENCE_APPLIED, SINGLE_SOURCE, CONTESTED_NO_AUTOMERGE, NO_USABLE_CONTACT}.
- contested_cluster_ids: watchlist identifier cases that remain contested (lex).
- dispatchable_master_ids: lexicographic.
- readiness_by_depot (by depot_code = region ASC): total / dispatchable / blocked_consent / blocked_no_contact / blocked_inactive (4 dispositions sum to total).
- policy_control_cases (by control_case_id ASC): `control_family` ∈ {FIELD_PROVENANCE, IDENTITY, OUTREACH} → `control_code` (FP / IC / OR per family, same enums as partner onboarding).
- release_decision: {status, action}. Numeric: all counts are exact integers; no floating-point fields.

## Control-code inference method (all domains)
The opaque codes (RB / SB / LD / FP / IC / OR / MS / HR) are intentionally NOT expanded in the task materials. Infer each from the shared records + the reconciled audit:
1. Read the relevant reference / snapshot / domain rows and the answer_template's allowed enum for that panel.
2. Tie each public ID to the evidence row(s) the case_scope anchors it to (`seed_row_id` / `source_row_anchor` / `evidence_row_ids`).
3. Derive the code from the evidence's audit outcome — e.g. reference_status, snapshot retention, mismatch / quarantine class, source-system precedence, field-level provenance. The code **family** is fixed per domain (above); only the specific enum member varies with the evidence.
4. Emit only contract-allowed enum values. When evidence is genuinely ambiguous, choose the outcome consistent with the rest of the reconciled audit rather than guessing randomly.
