# Restricted liquor-license staff package

For one target application at one location, produce: `recommended_posture`,
`same_premises_basis_applies`, `covered_risk_codes`, `verification_gap_codes`,
`standard_obligation_codes`, `location_specific_control_codes`, a `first_90_day_plan`, and
`escalation_trigger_codes`. Vocabularies differ between templates (a general set and a
hotel-lounge set that adds camera / food-service / late-night codes) — bind to *this* template's enums.

## Datasets (liquor family)

- `policies` (family `liquor`): flags such as `current_site_evidence_required`,
  `same_premises_history_matters`, `standard_privileges_separate_from_controls`,
  `major_incidents_trigger_board_review`.
- `liquor_applications`: `application_id`, `location_id`, `license_class`, `requested_posture`.
- `liquor_privileges`: `(license_class, obligation_code, standard_required 0/1)`. Obligation vocab:
  CCTV, DELIVERY, FOOD_SERVICE, HOURS, ID_CHECK, NOISE, PATIO, SECURITY.
- `liquor_settlements`: `location_id`, `basis_code` (NOISE / SAME_PREMISES / PUBLIC_SAFETY /
  SALE_TO_MINOR), `settlement_type`, `source_name`, `effective_date`,
  `controls_json` = `{active: bool, controls: [...], expires, review_required}`.
- `liquor_incidents`: `location_id`, `risk_code`, `severity`, `status`
  (open / referred / dismissed / closed), `incident_date`.
- `liquor_site_evidence`: `location_id`, `evidence_code` (CONTROL_SIGNAGE / FLOOR_PLAN /
  NEIGHBOR_NOTICE / POLICE_MEMO / SITE_PHOTO / TAX_CLEARANCE), `status`
  (verified / conflicting / missing / stale), `evidence_date`, `notes`.

## Field derivations (well-supported)

- **`application_id`** = the target id from the prompt.
- **`standard_obligation_codes`** = obligation codes for the application's `license_class` where
  `standard_required = 1`. (These are the class defaults, independent of the location.)
- **`location_specific_control_codes`** = the `controls` of the location's **active** settlements
  (`controls_json.active == true`; active also implies `expires` is in the future).
  **Do not subtract codes that also appear as standard obligations** — list active controls as-is.
- **`same_premises_basis_applies`** = true iff there is an **active** settlement with
  `basis_code = SAME_PREMISES`. An inactive/expired same-premises settlement does not count.
- **`verification_gap_codes`**: for each `evidence_code` at the location, take the **latest** record
  and map `(evidence_code, current status)` to its gap code — e.g. CONTROL_SIGNAGE+missing →
  current-missing, CONTROL_SIGNAGE/POLICE_MEMO/FLOOR_PLAN+conflicting → the matching conflicting code,
  FLOOR_PLAN+stale → stale, NEIGHBOR_NOTICE/SITE_PHOTO/TAX_CLEARANCE+missing → the matching missing
  code. A POLICE_MEMO whose note flags an identity/name issue → the police-memo identity/conflict code.
  **Plus** any incident with `status` in {open, referred} → an open-incident-follow-up code. A
  `verified` current record is not a gap; the mere *absence* of an evidence type is not a gap (a gap
  needs a record whose status is missing/conflicting/stale). Only the latest record per code matters.
- **`recommended_posture`**: `request_follow_up` when verification gaps / open incidents remain but
  there is no hard blocker; `deny` for a hard blocker (e.g. an unresolved major public-safety matter or
  a failed same-premises basis); `issue_restricted` only when controls are in place and gaps are
  cleared. A first-90-day monitoring plan can accompany `request_follow_up` — its presence does **not**
  imply issuance.

## Field derivations (judgment — keep minimal, do not pad)

- **`covered_risk_codes`** = risks addressed by the location's currently **active** controls/settlement
  (map active control → the risk it mitigates, and include an active settlement's basis risk). Do not
  add every historical incident risk; over-inclusion is penalized.
- **`escalation_trigger_codes`**: conservative — key off **current unresolved conditions** (e.g. a
  referred/unresolved minor-sale, control signage not verified, an open tax hold, a control that is
  active-but-unverified). Adding general risk-history triggers that are not currently active lowers
  the score.
- **`first_90_day_plan`**: one `{check_code, timing}` per relevant active control / open gap /
  standard obligation actually present at the location; keep the set tight. Order per the template
  (some sort ascending by `check_code`; the hotel-lounge variant asks for intended operational
  sequence, i.e. earliest-timing first). Timing buckets: `first_30_days`, `days_31_60`, `days_61_90`.

## Notes

- `standard_privileges_separate_from_controls` means the two lists are reported separately, **not**
  that overlapping codes are removed from the controls list.
- The hotel-lounge template's camera / food-service / late-night gap and escalation codes are driven
  by the prompt's emphasis and by missing camera/food-service evidence for a lounge class; still
  include only codes a record or an actual required control supports, and prefer placing
  camera/food/late-night items in the plan and escalation fields rather than padding
  `verification_gap_codes`.
