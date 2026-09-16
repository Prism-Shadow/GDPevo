# Liquor License Staff Package Reference

## Join Keys

Every record type joins on `location_id` unless noted otherwise:

| Record type | Join field | Notes |
|-------------|-----------|-------|
| applications | `application_id` (prompt target) | Has `location_id` which links to location-level records |
| settlements | `location_id` | Multiple settlements per location |
| incidents | `location_id` | Multiple incidents per location |
| site-evidence | `location_id` | Multiple evidence records per location |
| privileges | `license_class` | Joins via `applications[].license_class` = `privileges[].license_class` |
| policies | (family = "liquor") | Policy rules apply globally |

## Two Liquor Template Vocabularies

There are two different liquor answer template styles. The prompt and answer
template tell you which one applies:

**Style A (train_002 style):** UPPER_SNAKE_CASE codes throughout.
`covered_risk_codes` use values like `AFTER_HOURS`, `ASSAULT`, `MINOR_SALE`,
`SALE_TO_MINOR`, `SAME_PREMISES`, etc. `verification_gap_codes` use values
like `CONTROL_SIGNAGE_CONFLICTING`, `OPEN_INCIDENT_FOLLOW_UP`, etc.

**Style B (train_005 style, hotel/lounge):** snake_case codes throughout.
`covered_risk_codes` use values like `NOISE`, `PATIO_BOUNDARY`, `AFTER_HOURS`,
etc. `verification_gap_codes` use values like `camera_evidence_missing`,
`food_service_evidence_missing`, `floor_plan_conflicting`, etc.

Always use exactly the codes from the current template.

## Recommended Posture

The `recommended_posture` is a three-way decision:

- **`deny`**: The application has a hard block. This happens when:
  - The sole active settlement at the location has `settlement_type` =
    "historic refusal" AND the settlement controls_json shows active=false.
  - An open incident with severity "high" exists at the location.
  - The same-premises basis does NOT apply AND there are unresolved
    high-severity incidents.

- **`issue_restricted`**: All risks are covered by current active controls,
  there are no unresolved verification gaps, and the same-premises basis
  applies.

- **`request_follow_up`**: The case between the two extremes. Any of:
  - Same-premises basis applies but there are unresolved verification gaps
    or open incidents.
  - Risks exist that are partially but not fully covered by controls.
  - Evidence is missing or conflicting for some controls.

The most common posture in escalated reviews is `request_follow_up` — the
review exists because something needs follow-up.

## Same-Premises Basis

`same_premises_basis_applies` is `true` when:

- The location has at least one settlement whose `basis_code` is
  `SAME_PREMISES` AND the settlement's `controls_json` (parse the JSON string)
  shows `active: true`.

It is `false` when:

- No SAME_PREMISES settlement exists at the location, OR
- A SAME_PREMISES settlement exists but its controls are not active
  (`active: false`), OR
- The settlement has expired (check `expires` against current date).

## Covered Risk Codes

Derive `covered_risk_codes` by collecting risk codes that are addressed by
active controls or settlements:

1. For each active settlement at the location (parse `controls_json`,
   check `active: true`), include the settlement's `basis_code` (e.g.,
   `SAME_PREMISES`, `NOISE`, `SALE_TO_MINOR`).

2. For each incident at the location with `status` = "closed", include its
   `risk_code` if the incident was resolved through a settlement that is
   still active.

3. For each incident at the location, include its `risk_code` when there is
   an active settlement with a matching `basis_code`.

Only include codes that exist in the template's `covered_risk_codes` enum.
Remove duplicates and sort ascending.

## Verification Gap Codes

Derive `verification_gap_codes` from site-evidence records and unresolved
incidents:

1. For each site-evidence record at the location:
   - `status` = "missing" → map evidence_code to gap code:
     `CONTROL_SIGNAGE` → `CONTROL_SIGNAGE_CURRENT_MISSING` (Style A) or
     `control_signage_missing` (Style B)
     `NEIGHBOR_NOTICE` → `NEIGHBOR_NOTICE_MISSING` or
     `neighbor_notice_missing`
     `SITE_PHOTO` → `SITE_PHOTO_MISSING` or `site_photo_missing`
     `TAX_CLEARANCE` → `TAX_CLEARANCE_MISSING` or `tax_hold_unresolved`
     `FLOOR_PLAN` → `FLOOR_PLAN_STALE` or `floor_plan_conflicting`
   - `status` = "conflicting" → map evidence_code:
     `CONTROL_SIGNAGE` → `CONTROL_SIGNAGE_CONFLICTING`
     `FLOOR_PLAN` → `FLOOR_PLAN_CONFLICTING` or `floor_plan_conflicting`
   - `status` = "stale" → `FLOOR_PLAN_STALE` or `floor_plan_conflicting`
   - `notes` mentioning "Conflicts with settlement order" → corresponding
     conflicting gap code

2. For open incidents at the location (`status` = "open"):
   - Include `OPEN_INCIDENT_FOLLOW_UP` (Style A) or map to specific gap codes
     based on risk_code (Style B).

3. For evidence referenced in settlements but missing or conflicting:
   - Camera-related evidence missing → `camera_evidence_missing` (Style B)
   - Food service evidence missing → `food_service_evidence_missing` (Style B)
   - Late-night monitoring gaps → `late_night_monitoring_needed` (Style B)

4. For police memos that conflict with settlement records:
   - `POLICE_MEMO_CONFLICTING` (Style A) or `police_memo_identity_note`
     (Style B)

Only include codes in the template's enum. Sort ascending and deduplicate.

## Standard Obligation Codes

Derive from the privileges endpoint, filtered by the application's
`license_class`:

- Include every `obligation_code` where `standard_required` = 1 for the
  matching `license_class`.

This means a Tavern license always has `ID_CHECK`, `HOURS`, `FOOD_SERVICE`
(those three are standard-required for Tavern). A Restaurant license has
`ID_CHECK`, `HOURS`, `FOOD_SERVICE`. Other license classes vary.

Only include codes in the template's enum. Sort ascending.

## Location-Specific Control Codes

Derive from active settlement controls at the location:

1. For each settlement at the location, parse `controls_json`.
2. If `active: true`, collect all codes in the `controls` array.
3. Deduplicate across settlements.

Include only codes that are in the template's
`location_specific_control_codes` enum.

Note: Some codes can appear in both standard obligations and
location-specific controls — that is normal. Standard obligations are
license-class requirements; location-specific controls are extra measures
imposed by settlements for this particular location.

## First 90-Day Plan

Build a monitoring plan covering the first 90 days after issuance. Each
entry has a `check_code` and `timing`. Derive checks from verification gaps
and uncovered risks:

1. For each verification gap, select a corresponding check:
   - Missing/conflicting control signage → `control_signage_recheck` or
     `control_signage_review` (first_30_days)
   - Missing camera evidence / CCTV gaps → `security_cctv_walkthrough` or
     `camera_export_test` (first_30_days)
   - Open incident follow-up → `police_memo_follow_up` (first_30_days)
   - ID check concerns → `id_check_observation` (first_30_days)
   - After-hours risk → `after_hours_visit` (days_31_60)
   - Food service gaps → `food_service_check` or
     `food_service_service_area_check` (first_30_days)
   - Late-night monitoring → `late_night_closing_visit` (days_31_60)
   - Noise/patio → `noise_log_review` or `noise_patio_boundary_check`
     (days_61_90)
   - Tax clearance → `tax_clearance_check` (first_30_days)

2. For risks not fully covered by existing controls, add a check:
   - Each uncovered risk code maps to a monitoring check with timing
     appropriate to the risk.

3. Order entries in operational sequence: earlier timing windows first,
   then by check_code.

Use only check_code and timing values from the template's enum. Each
(check_code, timing) pair must be unique.

## Escalation Trigger Codes

Define conditions that would escalate the license back to board review:

1. For each covered risk code, define the corresponding escalation trigger:
   - `AFTER_HOURS` → `AFTER_HOURS_VIOLATION` (Style A) or
     `after_hours_service` (Style B)
   - `MINOR_SALE` / `SALE_TO_MINOR` → `REFERRED_MINOR_SALE_UNRESOLVED`
     (Style A) or `minor_sale` (Style B)

2. For each verification gap, define the trigger:
   - Control signage gap → `CONTROL_SIGNAGE_NOT_VERIFIED`
   - CCTV/camera gap → `SECURITY_CCTV_CONTROL_FAILURE` (Style A) or
     `missing_camera_coverage` / `footage_not_produced` (Style B)
   - Food service gap → `food_service_not_available` (Style B)
   - Noise/patio gap → `noise_or_patio_breach` / `patio_boundary_failure`
     (Style B)
   - Tax hold → `TAX_HOLD_REOPENED` (Style A) or `open_tax_hold_uncleared`
     (Style B)

3. Include `MAJOR_INCIDENT_REPORTED` (Style A) or
   `unreported_violent_incident` (Style B) for any high-severity risk.

4. Include `BOARD_ORDER_CONFLICT` (Style A) if there are conflicting
   settlement records or board orders.

Use only codes from the template's enum. Sort ascending and deduplicate.

## Policy Routing

Two liquor policies apply:

- **POL-LIQ-001** (LIQ-SETTLEMENT-CONTROLS): `current_site_evidence_required:
  true`, `same_premises_history_matters: true`,
  `standard_privileges_separate_from_controls: true`. This drives the
  requirement for site evidence and the separation of standard obligations
  from location-specific controls.

- **POL-LIQ-002** (LIQ-RISK-MATRIX): `major_incidents_trigger_board_review:
  true`. A major (high-severity) incident triggers board review.

These policies define the framework. The actual decisions derive from the
records, not the policy metadata directly.
