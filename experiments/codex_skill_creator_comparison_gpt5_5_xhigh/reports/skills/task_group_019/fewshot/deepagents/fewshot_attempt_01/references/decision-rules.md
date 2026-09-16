# Licensing Decision Rules

## Contents

- [Contractor Eligibility](#contractor-eligibility)
- [Restricted Liquor Review](#restricted-liquor-review)
- [Alcohol Renewal Queue](#alcohol-renewal-queue)
- [Schema Adaptation](#schema-adaptation)

## Contractor Eligibility

Build a target-indexed record set:

- Application by `application_id`.
- Current policy by trade and requested class. Parse policy `details_json`.
- Bonds and insurance by `application_id`.
- License history by the application's `prior_license_id` when present.
- Violations, correspondence, and inspections by `related_application_id`.

Use the prompt's review date for current-coverage checks. If no explicit review date is given, treat the environment snapshot as the review context and still require non-expired active coverage when expiration dates are present.

Apply policy standards:

- Bond deficiency:
  - No usable active bond when all current records are cancelled, expired, or absent.
  - Bond shortfall when the best active bond amount is below policy `minimum_bond`.
- Insurance deficiency:
  - Pending or otherwise not-current status is a current-insurance deficiency.
  - Active coverage with `expiration_date` before the review date is expired.
  - Active current coverage below policy `minimum_insurance` is an insurance shortfall.
- Experience shortfall when `years_experience` is below policy `minimum_years_experience`.
- Endorsement deficiency when policy `required_endorsement` is present and application `endorsement_status` is `missing` or `pending`.
- Active suspension when license history status is `suspended`.
- Open serious complaint or violation when a related violation has `status` open and `severity` serious.
- Open minor violation when the template supports a minor-violation code and a related violation has open minor severity.
- Inspection document gap or safety recheck only when the template supports inspection codes and the relevant inspection finding is adverse or conditional, not when it passed.

Map each deficiency to the closest code/action names allowed by the template:

| Condition | Common deficiency codes | Common action codes |
|---|---|---|
| No active/current bond | `bond_cancelled`, `no_active_bond` | `obtain_current_bond`, `file_active_bond` |
| Bond below policy minimum | `bond_shortfall` | `increase_bond_amount`, `increase_bond` |
| Insurance pending or not current | `insurance_pending`, `insurance_not_current` | `verify_insurance_binding`, `provide_current_insurance` |
| Insurance expired | `insurance_expired` | `provide_current_insurance`, `renew_insurance` |
| Insurance amount below minimum | `insurance_shortfall` | `increase_insurance_amount`, `increase_insurance` |
| Missing endorsement | `endorsement_missing`, `endorsement_not_verified` | `obtain_required_endorsement`, `verify_endorsement` |
| Pending endorsement | `endorsement_pending`, `endorsement_not_verified` | `verify_pending_endorsement`, `verify_endorsement` |
| Experience below minimum | `experience_shortfall` | `submit_experience_evidence`, `document_experience` |
| Active suspension | `active_suspension` | `board_review_suspension`, `clear_suspension`, `board_review` |
| Open serious violation or complaint | `open_serious_violation`, `unresolved_serious_complaint` | `resolve_serious_violation`, `resolve_complaint`, `board_review` |
| Open minor violation | `open_minor_violation` | `resolve_minor_violation_review` |
| Inspection document gap | `inspection_doc_gap` | `clear_document_gap` |
| Inspection safety recheck | `inspection_safety_recheck` | `complete_safety_recheck` |

Determination and risk:

- `DENY` when active suspension or open serious violation/complaint applies.
- `HOLD` when any deficiency remains but denial is not required.
- `APPROVE` only when no deficiency remains.
- Use `high` for denials, `medium` for holds, and `low` for approvals unless the template or prompt gives a stricter risk rule.

Policy impact:

- Compare current policy standards against any legacy policy details marked for prior-rule comparison.
- Mark `policy_impacted` when a current-policy deficiency would not have existed under the legacy baseline, such as a bond amount that meets the reduced legacy minimum but not the current minimum, or an endorsement requirement newly applied by current policy.
- Do not mark policy impact merely because the application has unrelated stale correspondence or a deficiency that would also fail under the legacy baseline.

Contractor summaries:

- Counts must match determinations.
- High-risk IDs are the item IDs with `risk_tier` high.
- Policy-impacted IDs are item IDs with `policy_impacted` true.
- Stale or unverified correspondence includes records with `verified_by_agency` false, plus records whose notes or values explicitly indicate stale, conflicting, or unverified support.

## Restricted Liquor Review

Build the record set from the application, then use its `location_id` and `license_class`:

- Settlements, incidents, and site evidence by `location_id`.
- Privileges by `license_class`.
- Policies with family `liquor`.

Separate standard obligations from location-specific controls:

- `standard_obligation_codes` come from privilege records where `standard_required` is true.
- `location_specific_control_codes` come from active settlement `controls_json.controls`.
- Do not put ordinary class obligations into location-specific controls unless an active settlement also imposes them.

Same-premises basis:

- Set the same-premises boolean when any relevant settlement/history has basis `SAME_PREMISES` and the policy says same-premises history matters.
- Active same-premises controls strengthen the basis, but historical same-premises records can still make the basis apply when the policy says history matters.

Risk and gap handling:

- Parse settlement `controls_json`; active controls cover the settlement basis and the risks naturally addressed by those controls.
- Ignore dismissed incidents for risk and gap purposes.
- Referred or open incidents can create verification gaps or escalation triggers when they are not already resolved by current controls.
- Current site evidence is required when policy says so. Missing, conflicting, or stale evidence creates verification gaps.
- Keep code casing from the answer template. Some liquor templates use uppercase business codes; others use lowercase operational codes.

Common liquor mappings:

| Record signal | Covered risk or gap | Monitoring or escalation |
|---|---|---|
| Active same-premises settlement | `SAME_PREMISES`; same-premises boolean true | Controls from the active settlement |
| Active hours/security/CCTV controls addressing after-hours or safety history | `AFTER_HOURS`, `ASSAULT`, `PUBLIC_SAFETY` when allowed | after-hours visit; security/CCTV walkthrough; major incident trigger |
| Active ID-check or minor-sale controls, or referred minor-sale incident | `MINOR_SALE`, `SALE_TO_MINOR` when allowed | ID-check observation; unresolved minor-sale trigger |
| Active noise or patio controls | `NOISE`, `PATIO_BOUNDARY` when allowed | noise/patio boundary check; noise or patio breach trigger |
| Tax hold not cleared | `TAX_HOLD` when asked as risk, otherwise tax verification gap | tax clearance review or open-tax-hold trigger |
| Control signage missing/conflicting | signage verification gap | control-signage recheck or not-verified trigger |
| Floor plan missing/stale/conflicting | floor-plan verification gap | site or boundary check |
| Police memo conflicting or identity note | police-memo verification gap | police memo follow-up |
| Required food service but no current evidence | food-service evidence gap | food-service check or food-service-not-available trigger |
| Camera/CCTV required or specifically requested but evidence missing | camera evidence gap | camera export test; missing coverage or footage trigger |
| Late-night service concern | late-night monitoring gap | late-night closing visit or after-hours trigger |

Recommended posture:

- Use `issue_restricted` when risks are covered and required evidence is current.
- Use `request_follow_up` when controls may support issuance but verification gaps, open follow-up, missing current evidence, or monitoring needs remain.
- Use `deny` only when the prompt, policy, or unresolved blocking record supports denial.

First-90-day plans should contain operational checks for remaining gaps and active controls. Use the template's ordering instruction; if it says intended operational sequence, put immediate verification checks in `first_30_days`, follow-up visits in `days_31_60`, and later boundary/noise reviews in `days_61_90`.

## Alcohol Renewal Queue

Build the queue from the prompt's target license numbers and release boundary:

- Fetch licensee records by `license_no`.
- Fetch violation records for each target `license_no`.
- If a licensee has `successor_to`, fetch violations for that old license too. Count successor rows when address or facility identity is a close match to the target licensee.
- Exclude every violation after the boundary date from matching. Record excluded target-license late rows in the summary when the template asks for them.

Matched violation fields:

- `violation_count` is the number of matched pre-boundary rows.
- `most_recent_violation_date` is the latest date among matched rows.
- `matched_violation_ids` are sorted by violation date ascending, then violation ID ascending.
- `match_confidence` is `exact` for target-license rows only, `close_address` when successor rows match by address or close facility identity, and `uncertain` when a successor or identity match needs manual confirmation.

Risk tier:

- High risk when matched rows include an unresolved serious violation, substantial unpaid fine balance, sale-to-minor or after-hours themes with open or pending status, or multiple serious/alert conditions.
- Medium risk for remaining licenses that still require manual review due to alerts, open/pending rows, or smaller unpaid balances.
- Low risk only when the template allows it and the record set has no meaningful manual-review driver.

Next-step label priority:

1. `board_review` for serious unresolved matters, successor/identity complications with serious rows, or severe minor-sale/after-hours patterns.
2. `manual_fine_check` for unpaid fine balances or fine/hold cleanup not requiring immediate board review.
3. `manual_ALERT_check` for alert-flag review when board and fine checks do not dominate.
4. `additional_record_check` for uncertain matches or residual low-signal records.

Ranking:

- Rank by next-step priority first: board review before fine check before alert check before additional record check.
- Within the same priority, sort by most recent matched violation date descending.
- Use violation count descending and license number ascending as tie-breakers unless the prompt or renewal rules specify another order.
- Return exactly the requested queue size with ranks `1..N`.

Renewal summaries:

- `queue_size` equals the number of queue entries returned.
- `boundary_date` equals the prompt boundary.
- `post_boundary_violation_ids_excluded` contains excluded post-boundary IDs sorted by ID.
- `close_or_uncertain_match_license_numbers` contains queue licenses whose confidence is not exact, sorted ascending.
- `board_review_license_numbers` contains queue licenses whose next step is `board_review`, sorted ascending.

## Schema Adaptation

Never emit a code that is not allowed by the current template. When the rule name differs from the template, choose the closest allowed synonym. If two possible signals map to one allowed code, de-duplicate it. If the template says lexical ordering, sort strings alphabetically after mapping to final code names.
