# Restricted liquor-license staff package

One application at one location. Output keys (exact names/vocab from the template):
`application_id`, `recommended_posture`, `same_premises_basis_applies`,
`covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`,
`location_specific_control_codes`, `first_90_day_plan`, `escalation_trigger_codes`.
Templates differ in casing and code sets (e.g. one uses `SAME_PREMISES`/`PUBLIC_SAFETY`,
another `PATIO_BOUNDARY`/`CAMERA_COVERAGE`) — **map every finding onto this template's
`allowed_values`, deduplicate, and honor its ordering** (some sort ascending, some
accept any order / operational sequence).

## Step 1 — pull the location's records (SQL by `location_id`)

- `liquor_applications` (the target app; note `license_class`, `requested_posture`).
- `liquor_settlements WHERE location_id=<LOC>` — each has `basis_code`, `settlement_type`,
  `source_name`, `effective_date`, and `controls_json`
  (`{active, controls[], expires, review_required}`).
- `liquor_incidents WHERE location_id=<LOC>` — `risk_code`, `severity`, `status`.
- `liquor_site_evidence WHERE location_id=<LOC>` — `evidence_code`, `status`, `notes`.
- `GET /api/liquor/privileges` for the application's `license_class`.
- `GET /api/policies` (family `liquor`: `POL-LIQ-001` same-premises/control review,
  `POL-LIQ-002` incident severity → board review).

## Step 2 — the two "obligation" lists (most mechanical; do these first)

- `standard_obligation_codes` = privileges for this `license_class` with
  `standard_required == 1` (the ordinary obligations of the class).
- `location_specific_control_codes` = the union of `controls` from **settlements whose
  `controls_json.active == true`** (the currently active, location-tied controls). If no
  settlement is active, this is empty.

## Step 3 — `same_premises_basis_applies`

True if any settlement in the location's history has `basis_code == "SAME_PREMISES"`
(active or historical). `POL-LIQ-001` sets `same_premises_history_matters=true`.

## Step 4 — `covered_risk_codes` (risks addressed by current controls)

Build from the **active settlement(s)**, then corroborate:
- Add the active settlement's `basis_code` (mapped to the template's risk vocab).
- Add the risk each **active control** addresses, via this control→risk mapping
  (map to the template's actual codes; some templates split camera coverage vs assault):
  `HOURS`→after-hours, `SECURITY`/`CCTV`→assault / camera-coverage,
  `ID_CHECK`→minor-sale / sale-to-minor / id-check, `FOOD_SERVICE`→food-service,
  `NOISE`→noise, `PATIO`→patio-boundary.
- Additionally add a risk that is **corroborated by both** a settlement `basis_code`
  **and** a non-dismissed incident `risk_code` (the same underlying concern appears in
  the settlement history *and* an incident), even if that settlement is now inactive.
- Exclude risks evidenced only by a dismissed incident, or only by a stale/inactive
  settlement with no corroboration.

## Step 5 — `verification_gap_codes` (what still needs verifying)

Derive from site-evidence status and open items, mapped to the template's gap vocab:
- Evidence row with `status == "conflicting"` → `<TYPE>_CONFLICTING` /
  `<type>_conflicting` (e.g. control-signage, police-memo, floor-plan).
- Evidence row with `status == "missing"` for the current packet →
  `<TYPE>_CURRENT_MISSING` / `<type>_evidence_missing`.
- A required evidence type with **no record at all** (the template expects it, e.g.
  camera/CCTV or food-service) → its `*_missing` gap code.
- An `open` or `referred` incident → an open-incident-follow-up gap; an `open`
  `TAX_HOLD` incident → the tax-hold-unresolved gap.
- A late-night / after-hours-sensitive venue with hours concerns → the
  late-night-monitoring-needed gap when the template offers it.
- A `verified` evidence row is **not** a gap (even with an odd note like "Old location
  name"), unless the template has a specific note code that clearly applies.

## Step 6 — `recommended_posture`

- `request_follow_up` when the same-premises/history basis supports eventual restricted
  issuance **but** verification gaps or open/referred incidents remain (the common case).
- `issue_restricted` only when controls are active/verified and there are no gaps.
- `deny` only for a disqualifying condition (e.g. a major unresolved blocking incident
  with the basis failing).

## Step 7 — `first_90_day_plan`

One `{check_code, timing}` per gap or key control, using the template's `check_code`
enum. Timing guidance:
- `first_30_days`: verifying missing/conflicting evidence and the key active controls
  (signage recheck, camera/export test, id-check observation, police-memo follow-up,
  security/CCTV walkthrough, food-service check).
- `days_31_60`: monitoring visits (after-hours / late-night closing visit).
- `days_61_90`: boundary/environmental checks (noise / patio boundary).

Order the list as the template says (sort by `check_code` ascending if it requires a
sort; otherwise keep the operational sequence first_30 → days_31_60 → days_61_90).

## Step 8 — `escalation_trigger_codes`

Map the location's active controls and material risks/gaps onto the template's
escalation enum: each active control → its "control failure/breach" trigger
(security/CCTV failure, noise/patio breach); after-hours/late-night exposure →
after-hours trigger; a high-severity ("major") incident → major-incident trigger
(`POL-LIQ-002`); a referred minor-sale incident → its unresolved trigger; missing camera
/ footage-not-produced and food-service-not-available → the corresponding triggers; an
open tax hold → tax-hold trigger. Include only codes in `allowed_values`; deduplicate.
