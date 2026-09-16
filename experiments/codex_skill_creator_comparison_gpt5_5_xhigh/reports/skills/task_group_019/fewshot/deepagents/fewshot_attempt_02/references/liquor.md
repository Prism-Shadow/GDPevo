# Restricted Liquor-License Staff Packages

Use this reference for restricted liquor-license transfer, renewal-with-controls, hotel-lounge, or settlement-review packages.

## Data Assembly

Fetch policies, liquor applications, settlements, privileges, incidents, and site evidence. Identify the target application and location from the prompt. Join:

- Application by `application_id`.
- Settlements, incidents, and site evidence by `location_id`.
- Standard obligations by `license_class` in the privileges endpoint.

Parse `controls_json` on settlement rows. Treat a control as active only when the parsed `active` flag is true and the row is not expired under the review context. Keep historical settlements for basis analysis even when their controls are inactive.

## Core Fields

- `application_id`: copy the target application ID.
- `same_premises_basis_applies`: true when any settlement history for the location has `basis_code == "SAME_PREMISES"`. This is a history/basis question, not limited to active controls.
- `standard_obligation_codes`: privilege rows for the application `license_class` where `standard_required` is true. Keep these separate from location controls.
- `location_specific_control_codes`: union of controls from active settlement rows at the location only.

## Risk And Gap Classification

Covered risks come from active settlement bases and risks mitigated by active controls or standard obligations. Use template-allowed code spelling:

- `HOURS` controls cover after-hours risk.
- `ID_CHECK` controls or standard obligations cover minor-sale and sale-to-minor risk.
- `SECURITY` and `CCTV` controls cover assault, public-safety, and camera/security risk.
- `FOOD_SERVICE` covers food-service gaps.
- `NOISE` covers noise risk.
- `PATIO` covers patio-boundary risk.
- `SAME_PREMISES` is covered when same-premises history is an applicable settlement basis.

Do not include dismissed incidents as active risks. Open, referred, or pending incidents create follow-up gaps and may still be covered by current controls.

Verification gaps come from current site-evidence requirements, conflicting or missing evidence, and unresolved incident status:

- Control-signage missing/conflicting -> `CONTROL_SIGNAGE_CURRENT_MISSING`, `CONTROL_SIGNAGE_CONFLICTING`, or `control_signage_missing`.
- Floor-plan conflicting/stale -> `FLOOR_PLAN_CONFLICTING`, `FLOOR_PLAN_STALE`, or `floor_plan_conflicting`.
- Police memo conflicting/identity note -> `POLICE_MEMO_CONFLICTING` or `police_memo_identity_note`.
- Open/referred incident -> `OPEN_INCIDENT_FOLLOW_UP`.
- Missing current camera/CCTV proof -> `camera_evidence_missing`.
- Missing food-service proof where food service is a standard obligation or prompt focus -> `food_service_evidence_missing`.
- Late-night risk without verified hours/security monitoring -> `late_night_monitoring_needed`.
- Open tax-hold incident -> `TAX_CLEARANCE_MISSING`, `tax_hold_unresolved`, or equivalent allowed code.
- Missing neighbor notice or site photo -> the corresponding allowed missing code.

When multiple evidence rows exist, consider the latest current packet first, but keep unresolved conflicting rows if the record says follow-up is needed.

## Recommended Posture

- `deny`: use only for an unresolved disqualifying condition that cannot be cured by restriction or follow-up under the prompt.
- `request_follow_up`: use when verification gaps, open/referred incidents, conflicting evidence, or unresolved tax/major-incident issues remain.
- `issue_restricted`: use when applicable risks are covered by active controls and no material verification gaps remain.

## First 90-Day Plan

Build monitoring checks from the risks and gaps, then order as the template requires:

- Control-signage gap -> signage recheck in the first 30 days.
- Police memo conflict or open incident follow-up -> police memo or incident follow-up in the first 30 days.
- Minor-sale or ID-check risk -> ID-check observation in the first 30 days.
- Active security/CCTV controls or camera evidence gap -> CCTV/security walkthrough or camera export test in the first 30 days.
- Food-service evidence gap -> food-service check in the first 30 days.
- After-hours or late-night monitoring risk -> after-hours/late-night visit in days 31-60 unless the template says otherwise.
- Noise or patio controls -> noise/patio boundary check, often days 61-90 after initial controls are in place.
- Tax-clearance gap -> tax-clearance check when the template or prompt asks for tax follow-up.

## Escalation Triggers

Choose triggers directly tied to active gaps and material risks:

- After-hours risk -> after-hours violation/service trigger.
- Major assault or safety incident -> major incident or unreported violent incident trigger.
- Referred minor sale -> unresolved minor-sale trigger.
- Security/CCTV controls or camera gaps -> security/CCTV failure, missing camera coverage, or footage-not-produced trigger.
- Control-signage gap -> control-signage-not-verified trigger.
- Food-service gap -> food-service-not-available trigger.
- Noise/patio controls -> noise or patio breach trigger.
- Tax hold -> tax-hold reopened/open tax hold uncleared trigger.

Sort/dedupe coded arrays unless the template says that operational sequence matters.
