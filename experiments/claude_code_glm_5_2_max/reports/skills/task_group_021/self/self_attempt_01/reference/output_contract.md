# Output contract rules & pre-emit self-check

The `answer_template` is the contract. The rules below apply universally; the template may add domain-specific ones. The template always wins.

## Shape
- Exactly one JSON object. No commentary, no Markdown, no trailing text.
- `additionalProperties:false` at every level — include every required key, no extra keys, nowhere.
- Types & enums are strict: use only the enum values the template lists; integers are integers; numbers carry the declared precision.

## Ordering (defaults — the template's description / x-ordering_rules / field_contract.ordering overrides)
- ID sets: deduplicated, lexicographically ascending.
- Per-ID panels (reference_decisions, transaction_decisions, event_decision_panel, policy_control_cases, focus_clusters, focus_people, etc.): one row per scoped ID, sorted by that ID ascending.
- "Exactly one per X" arrays (fuel_type_totals, service_class_totals, region_rollup, readiness_by_depot): sorted by the category / region / depot ascending.
- Ranked arrays (exception_merchant_ranking, carrier_ranking, asset_risk_ranking): follow the case_scope sort policy — primary sort DESC, tie-breaks as declared (usually id ascending), with a `rank` field ascending 1..N.
- duplicate_groups: sorted by logical / charge id ascending; inner `snapshot_ids` lexicographically ascending.
- focus_assets / focus_people: sorted by asset_id / focus_person_id ascending.

## Numeric precision
- Liters, kilograms, kilometers, USD: round to exactly 2 decimal places.
- quarantine_rate: 4 decimal places (`multipleOf 0.0001`).
- total_distance_km: `multipleOf 0.01` (2 dp).
- All counts: exact integers — no floating-point fields for counts.
- Keep full precision through aggregation; round only at output.

## Count / partition integrity
- channel_readiness: `both + email_only + phone_only + not_ready` = readiness_eligible_entity_count (mutually exclusive).
- readiness_by_depot: `blocked_consent + blocked_no_contact + blocked_inactive + dispatchable` = total_person_count, per depot.
- audit_summary: `logical = raw − duplicate_raw`; `valid = logical − quarantined`; `exception = distinct(mismatch ∪ quarantine)`.
- normalized_totals.valid_*_count must equal audit_summary.valid_*_count.

## Completeness
- Every ID listed in case_scope (focus IDs, decision-panel IDs, control-case anchors, watchlist cases) must appear in the output.
- Array lengths must match the template's minItems/maxItems and the case_scope requested counts (e.g. focus_assets = len(focus_asset_ids); exception_merchant_ranking = merchant_ranking_limit).

## Pre-emit self-check checklist
1. JSON parses; exactly one top-level object; no commentary.
2. Every required key present at every level; no extra keys.
3. Every enum value is contract-allowed.
4. Every array within minItems/maxItems; every "exactly N" array is exactly N.
5. Every ID list deduplicated and sorted per the contract.
6. Numeric fields at the declared precision; counts are integers.
7. Partition sums hold (channel_readiness, readiness_by_depot, audit_summary relationships).
8. Every case_scope decision-panel / focus ID is present in the output.
9. Certification status→action matches the case_scope map and thresholds.
10. Quarantined items excluded from normalized totals; valid mismatches included.

If a JSON-Schema (draft 2020-12) validator is available, validate the JSON against `answer_template.json` before emitting. Many templates are already valid JSON Schemas; the field_contract-style templates (object with `field_contract` / `required_top_level_keys`) are not — for those, check the rules above manually.
