# Restricted liquor-license staff package

Output: a single JSON object for one `application_id` at one `location_id`, with
these keys (exact names/enums come from the template):
`application_id`, `recommended_posture`, `same_premises_basis_applies`,
`covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`,
`location_specific_control_codes`, `first_90_day_plan`, `escalation_trigger_codes`.

Templates for this family use **different code vocabularies** for the same
conditions (e.g. `PATIO` vs `PATIO_BOUNDARY`; uppercase `TAX_HOLD` vs
`tax_hold_unresolved`). Detect the real conditions below, then emit only codes the
current template's `allowed_values` provide.

## Data to pull (by location_id / license_class)

- `liquor_applications` (the target) — `license_class`, `requested_posture`.
- `liquor_settlements` for the `location_id` — each has `basis_code`,
  `settlement_type`, `effective_date`, and `controls_json` (parse it: `active`
  bool, `controls` list, `review_required` bool, `expires`).
- `liquor_incidents` for the `location_id` — `risk_code`, `severity`, `status`.
- `liquor_site_evidence` for the `location_id` — `evidence_code`, `status`
  (`verified` / `conflicting` / `missing`), `notes`.
- `liquor_privileges` for the `license_class` — `obligation_code`,
  `standard_required`.

## Deterministic fields (validated)

**`application_id`** — the target application id from the prompt.

**`same_premises_basis_applies`** — `true` if any settlement for the location has
`basis_code == "SAME_PREMISES"` (same-premises history matters, active or not).

**`standard_obligation_codes`** — the `obligation_code`s where
`liquor_privileges.license_class == this class` **and** `standard_required == 1`.
De-duplicate; sort per the template.

**`location_specific_control_codes`** — the `controls` list of the **active**
settlement(s) (rows whose `controls_json.active == true`). De-duplicate; sort per
the template. (These are the currently-in-force, location-specific controls.)

## `covered_risk_codes`

The risks that the location's **active controls** address, restricted to codes the
template lists. Derive one covered risk per active control using this observed
control→risk correspondence, then add `SAME_PREMISES` if the active settlement's
`basis_code` is `SAME_PREMISES`:

| Active control | Covered risk(s) |
| --- | --- |
| `HOURS` | AFTER_HOURS |
| `SECURITY` | ASSAULT (public-safety) |
| `CCTV` | MINOR_SALE, SALE_TO_MINOR |
| `NOISE` | NOISE |
| `PATIO` | PATIO_BOUNDARY (or `PATIO`) |
| `FOOD_SERVICE` | FOOD_SERVICE_GAP coverage |
| `ID_CHECK` | MINOR_SALE / SALE_TO_MINOR / ID_CHECK |

Only emit codes present in the template's `covered_risk_codes` enum; cross-check
against the location's on-record incidents/settlement bases. A risk that is *not*
addressed by an active control is a gap (below), not a covered risk.

## `verification_gap_codes`

From `liquor_site_evidence` and open incidents, emit codes the template provides:
- Evidence row with `status == "conflicting"` → `<EVIDENCE>_CONFLICTING`
  (e.g. `POLICE_MEMO`→`POLICE_MEMO_CONFLICTING`,
  `CONTROL_SIGNAGE`→`CONTROL_SIGNAGE_CONFLICTING`,
  `FLOOR_PLAN`→`FLOOR_PLAN_CONFLICTING`).
- Evidence row with `status == "missing"` → the "current missing" code
  (e.g. `CONTROL_SIGNAGE_CURRENT_MISSING`).
- An **expected** evidence type with **no** row at all → the corresponding
  `*_missing` code, for evidence types relevant to this review (camera/CCTV,
  food-service, control-signage, site-photo, neighbor-notice, tax-clearance,
  floor-plan) — especially those the prompt emphasizes or that back a standard
  obligation (e.g. missing camera/CCTV → `camera_evidence_missing`, missing
  food-service → `food_service_evidence_missing`).
- An **open / unresolved incident** (`status` open or `referred`) →
  `OPEN_INCIDENT_FOLLOW_UP`, or a risk-specific unresolved code when the template
  has one (e.g. open `TAX_HOLD` incident → `tax_hold_unresolved`).
- A late-night-sensitive premises where `HOURS`/after-hours control is a standard
  obligation but is **not** among the active location controls →
  `late_night_monitoring_needed` (if in the enum).
- `verified` evidence → no gap.

## `first_90_day_plan`

An array of `{check_code, timing}` — one check per major gap / active control /
standard obligation, using the template's `check_code` enum. Assign `timing`
by urgency:
- Verification gaps and missing/conflicting evidence, control-signage, police-memo,
  camera export, food-service, id-check checks → `first_30_days`.
- After-hours / late-night closing monitoring → `days_31_60`.
- Noise/patio boundary and ongoing/standard checks → `days_61_90` (or
  `days_31_60`).

Order per the template: some templates sort by `check_code` ascending and
de-duplicate `check_code`/`timing` pairs; others want the intended operational
sequence (soonest first). Follow the template's stated `ordering`.

## `escalation_trigger_codes`

Field-staff triggers derived from the covered risks, verification gaps, active
controls, and open incidents — emit codes from the template's enum. Typical
correspondences:

| Condition | Escalation trigger |
| --- | --- |
| after-hours / HOURS concern | `AFTER_HOURS_VIOLATION` / `after_hours_service` |
| control-signage gap | `CONTROL_SIGNAGE_NOT_VERIFIED` |
| high-severity / major incident on record | `MAJOR_INCIDENT_REPORTED` / `unreported_violent_incident` |
| referred / unresolved minor-sale incident | `REFERRED_MINOR_SALE_UNRESOLVED` / `minor_sale` |
| SECURITY/CCTV active controls | `SECURITY_CCTV_CONTROL_FAILURE` / `footage_not_produced` / `missing_camera_coverage` |
| food-service obligation/gap | `food_service_not_available` |
| NOISE/PATIO controls | `noise_or_patio_breach` / `patio_boundary_failure` |
| open TAX_HOLD | `open_tax_hold_uncleared` / `TAX_HOLD_REOPENED` |

## `recommended_posture`

- `deny` — an active blocking condition: an open, high-severity/major incident
  that remains unresolved, or a board-order/settlement that prohibits issuance.
- `issue_restricted` — same-premises basis applies, active controls are in place,
  and there are **no** verification gaps or open incidents.
- `request_follow_up` — otherwise: verification gaps and/or open incidents remain
  to be resolved (the common outcome for a restricted-premises review).
