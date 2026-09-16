# Decision Patterns

Use these patterns as reusable guidance. Always let the current prompt, current endpoint records, and current `answer_template.json` decide the final field names and allowed values.

## API Handling

- Fetch policies/rules first; policy rows often contain JSON-encoded thresholds or control rules.
- Use targeted filters or a high `limit` on GET endpoints. Default endpoint responses can omit later records.
- Do not rely on SQL. Try it only if credentials are available; a token error means use GET endpoints.
- Join by the stable IDs named in the prompt:
  - Contractor: `application_id`, and `prior_license_id` for history/violations.
  - Liquor: `application_id`, `location_id`, and `license_class`.
  - Renewal: `license_no`, predecessor/successor license numbers, address, and boundary date.
- Treat dismissed/resolved/expired/inactive records as historical context unless the template or rule says they create a current flag.
- Parse stringified JSON fields before applying rules.

## Contractor Eligibility Batches

1. Match each application to the current contractor policy by trade and requested class. Use the policy's minimum bond, minimum insurance, minimum experience, required endorsement, and serious-open-violation rule.
2. Financial coverage:
   - A current bond normally requires `status` active, no cancellation, and amount at or above the policy minimum.
   - A cancelled/expired/no-current bond creates the template's active-bond deficiency/action. If an active bond exists but is below the minimum, use the shortfall deficiency/action.
   - Current insurance normally requires active status, expiration after the review date, and amount at or above the policy minimum. Use the review date in the prompt; if absent, infer the batch's operative date from policy/rule context instead of using today's date blindly.
   - Pending insurance is a current-verification problem; expired insurance is a currency problem; insufficient amount is a shortfall problem. Choose the exact enum names supplied by the template.
3. Endorsement and experience:
   - If the policy has no required endorsement, ignore `not_required`.
   - If the template distinguishes missing vs pending endorsements, preserve that distinction; otherwise use the template's generic unverified-endorsement code.
   - Years below the policy minimum create the template's experience deficiency/action.
4. History, violations, and inspections:
   - A suspended prior license is an active-suspension deficiency and normally a deny/high-risk trigger.
   - An open serious violation or complaint is a deny/high-risk trigger. An open minor violation is usually a hold/medium-risk trigger.
   - Resolved or dismissed violations do not create current violation deficiencies.
   - Failed or conditional inspection findings create inspection codes only when the template includes matching allowed values. Ignore passed findings.
5. Correspondence summary:
   - Include correspondence IDs in stale/unverified summaries when the record is not agency verified, is explicitly stale, predates the application while purporting to update the application, or conflicts with registry/agency records.
   - Sort summary ID arrays as required by the template.
6. Determination and risk:
   - `DENY`: active suspension or open serious violation/complaint.
   - `HOLD`: one or more curable deficiencies and no deny trigger.
   - `APPROVE`: no deficiencies.
   - High risk follows deny triggers; medium risk follows curable deficiencies; low risk follows approval.
7. `policy_impacted` means a current policy standard materially changes the eligibility analysis. Compare current policy thresholds/endorsement rules with any legacy baseline policy. Do not mark true for mere stale correspondence, record-status problems, resolved historical events, or ordinary experience shortfalls unless the policy baseline itself changed that requirement.

## Restricted Liquor-License Staff Packages

1. Fetch the target application, all settlements for the location, all incidents for the location, site evidence for the location, and privilege rows for the application's `license_class`.
2. Separate the fields:
   - `standard_obligation_codes`: privilege rows for the license class where `standard_required` is true.
   - `location_specific_control_codes`: active controls from active/current settlement `controls_json`.
   - `covered_risk_codes`: risks actually covered by active location controls or applicable standard obligations.
3. `same_premises_basis_applies` is true when same-premises history exists for the location and policy says same-premises history matters, even if the older settlement controls have expired.
4. Verification gaps come from current missing/conflicting/stale site evidence, open/referred incidents needing follow-up, unresolved tax holds, missing camera or food-service evidence when those controls are required, and explicit identity/signage/floor-plan conflicts. Map evidence codes to the exact enum casing in the template.
5. Recommended posture:
   - `issue_restricted` only when active controls cover the material risks and no material verification gaps remain.
   - `request_follow_up` when controls may support issuance but evidence, incident follow-up, tax, camera, food-service, signage, floor-plan, or late-night monitoring gaps remain.
   - `deny` only when current records show unresolved blocking risk that cannot be cured through follow-up.
6. First-90-day plan:
   - Add checks that correspond to unresolved gaps and material active controls.
   - Put urgent evidence checks in `first_30_days`, operational late-night/security checks in `days_31_60`, and ongoing noise/patio follow-up in `days_61_90` unless the template or prompt gives a different order.
   - If the template requires sorting by `check_code`, sort by that key; otherwise keep intended operational sequence.
7. Escalation triggers should mirror the unresolved gaps and most material covered risks. Do not add trigger codes unsupported by the current records.

## Alcohol Renewal Manual-Review Queues

1. Extract the target license range, queue size, and release boundary. Use the boundary from the prompt/rule; do not infer it from today's date.
2. Fetch target active licensees and violations. For licensees with `successor_to`, also fetch predecessor license records and predecessor violations when the address or facility clearly matches.
3. Include matched violations with `violation_date` on or before the boundary. Exclude later rows and place their IDs in the post-boundary exclusion summary.
4. Match confidence:
   - `exact`: violations are on the target license number.
   - `close_address`: predecessor/successor or address-matched rows are included with strong location evidence.
   - `uncertain`: rows are relevant but identity/location evidence is incomplete.
5. For each queue entry:
   - `matched_violation_ids`: sort by violation date ascending, then violation ID ascending.
   - `violation_count`: count matched pre-boundary violations.
   - `most_recent_violation_date`: latest matched pre-boundary violation date.
6. Risk and next step:
   - `board_review`: unresolved sale-to-minor/major public-safety patterns, strong predecessor/successor matches with serious records, or the highest-risk records designated by the renewal rules.
   - `manual_fine_check`: unpaid or fine-bearing records are the main issue, especially high fine balances or warning/settlement rows requiring staff review.
   - `manual_ALERT_check`: alert flags or open records require review but board/fine criteria are not stronger.
   - `additional_record_check`: identity or match confidence is too weak for the other labels.
   - High risk follows board-review criteria, unresolved serious records, or high fine exposure. Medium risk covers material alert/open activity without a high-risk trigger. Low risk is rare in a manual-review queue.
7. Ranking:
   - Prefer explicit priority fields or scoring in the renewal rules if present.
   - Otherwise order by next-step severity (`board_review`, then `manual_fine_check`, then `manual_ALERT_check`, then `additional_record_check`), then most recent matched violation date descending, then matched violation count descending, then license number ascending.
   - Assign ranks `1..N` with no gaps and trim to the target queue size.
8. Summary:
   - `queue_size` must equal the number of queue entries.
   - Boundary date must match the prompt/rule.
   - Close/uncertain match license numbers come from non-exact match confidence.
   - Board-review license numbers come from entries whose next step is board review.
