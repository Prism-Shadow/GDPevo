# Decision Rules

This reference captures reusable decision patterns for the licensing environment. Do not copy any prior task's final answer values. Always let the prompt, template, and live endpoint records determine the current answer.

## Data Handling

- Treat the prompt's target identifiers as the scope. Many endpoints contain distractors.
- For records linked by multiple fields, check common variants: `application_id`, `related_application_id`, `license_id`, `related_license_id`, `location_id`, `license_no`, and successor fields.
- Parse JSON stored as strings, especially policy `details_json` and settlement `controls_json`.
- When the template provides enum values, use only those values. If a natural finding has no enum in the template, omit it instead of inventing a code.
- When there are multiple records for the same requirement, use the current target-linked record: active/current financial records, unresolved enforcement records, current site evidence, and records known on or before a release boundary.

## Contractor Application Batches

Use these steps for contractor eligibility, licensing examiner, or State Contractors Licensing Board batch prompts.

1. Match each application to the current contractor policy by `trade` and `requested_class`. Parse policy thresholds such as minimum bond, minimum insurance, minimum years of experience, required endorsement, and whether serious open violations block issuance.
2. Evaluate financial coverage against the review date from the prompt. If no explicit date is given, use the date implied by the batch context and the record dates; do not use the chat session date blindly.
3. Bond findings:
   - No active bond or only cancelled/expired bonds maps to the template's no-active-bond code, such as `bond_cancelled` or `no_active_bond`.
   - An active bond below the policy minimum maps to `bond_shortfall`.
   - Use the paired action in the template, such as obtaining or filing a current bond, or increasing the bond amount.
4. Insurance findings:
   - Pending insurance is not fully current. Use `insurance_pending` when the template provides it; otherwise use a general not-current code.
   - Expired insurance, or an expiration date before the review date, maps to the template's expired or not-current code.
   - Active current insurance below the policy minimum maps to `insurance_shortfall`.
   - Use the paired action in the template, such as verifying binding, providing or renewing current insurance, or increasing coverage.
5. Endorsement findings:
   - If the current policy requires an endorsement and application status is missing, map to a missing/not-verified endorsement code.
   - If the status is pending, map to pending/not-verified and require verification.
   - `verified` and `not_required` clear the finding, unless the policy requires an endorsement and the record conflicts.
6. Experience findings:
   - Years of experience below the policy minimum maps to `experience_shortfall` or the template's equivalent, with an action to document or submit evidence.
7. Prior license and enforcement findings:
   - A linked prior license with `suspended` status is an active-suspension deficiency, high risk, and usually a denial or board-review posture.
   - Open serious violations or unresolved serious complaints are high-risk blocking findings.
   - Open minor violations usually create a hold and a review/resolve action when the template supports a minor-violation code.
   - Resolved or dismissed violations normally do not create deficiencies, but may explain stale correspondence or historical context if the template asks.
8. Inspection findings:
   - Failed or conditional document-gap inspections map to inspection document gap codes when those codes are available.
   - Failed safety rechecks map to safety-recheck codes. Passed inspections normally do not create a deficiency.
9. Correspondence summary:
   - For `stale_or_unverified_correspondence_ids`, include target-linked correspondence that is not agency verified or that explicitly says stale, unverified, conflicting, or registry-conflicting.
   - Sort summary IDs as the template requests.
10. Determination and risk:
   - Deny when there is an active suspension or open serious/unresolved serious enforcement blocker.
   - Hold when there are curable deficiencies but no denial-level blocker.
   - Approve only when no deficiency or action remains.
   - Use high risk for denial-level blockers, medium for ordinary holds, and low for clean approvals unless the template defines a different risk model.
11. Policy impact:
   - Set the policy impact flag only when a current policy standard creates a material deficiency or flag that would not have applied under the prior baseline.
   - Compare against any legacy policy record that states how to perform the prior-baseline comparison. Common examples are stricter current thresholds or newly required endorsements.

## Restricted Liquor-License Staff Packages

Use these steps for restricted liquor transfer, renewal-with-controls, hotel lounge, restaurant, package, or premises-control prompts.

1. Load the application, policies, settlements, privileges, incidents, and site evidence for the target application/location.
2. Determine standard obligations from the privileges for the application's `license_class` where `standard_required` is true. Keep these separate from location-specific controls.
3. Determine location-specific controls from active settlement records. Parse `controls_json`; include only active controls that appear in the output template.
4. Same-premises basis applies when settlement or historical records for the target location include a same-premises basis and the policy says same-premises history matters, even if an older control set is no longer active.
5. Covered risks:
   - Include risks that are actually addressed by current active controls or ordinary obligations.
   - Include same-premises risk when the same-premises basis applies and the template has that code.
   - Do not treat dismissed incidents as uncovered risk unless the prompt asks for history.
6. Verification gaps:
   - Missing or conflicting current control signage maps to the template's control-signage gap code.
   - Conflicting or stale floor plans map to floor-plan gap codes.
   - Conflicting police memoranda or open incident follow-up map to their corresponding template codes.
   - Open tax holds map to the template's tax-hold gap code.
   - If the prompt emphasizes camera coverage, CCTV, food service, hotel lounge controls, or late-night monitoring, verify that current evidence exists; otherwise add the matching camera, food-service, or late-night gap code when available.
7. Recommended posture:
   - `issue_restricted` is appropriate only when controls and current evidence cover the risks and no verification gaps remain.
   - `request_follow_up` is appropriate for curable verification gaps, open follow-up, missing evidence, conflicting site evidence, or monitoring needs.
   - `deny` is reserved for non-curable or severe unresolved conditions when the template and facts support denial.
8. First-90-day plan:
   - Map each gap or active control to an operational check code in the template.
   - Put current-evidence checks in the first 30 days, operational observations in the first 30 or days 31-60, and follow-up boundary/noise reviews later when the template uses an operational sequence.
   - Deduplicate by check code and timing; sort if the template specifies sorting.
9. Escalation triggers:
   - Add triggers for failure of active controls, unresolved referred minor sales, after-hours service, missing or unavailable camera footage, unavailable food service, noise/patio breaches, open tax holds, and major incident reporting when those findings exist and the enum supports the trigger.

## Alcohol Renewal Manual-Review Queues

Use these steps for renewal pre-release screens and ranked manual-review queues.

1. Read the release boundary from the prompt or the matching renewal rule. Include only violations known on or before that date.
2. Record post-boundary violation IDs separately when the template asks for excluded IDs.
3. Match violations to active target licensees by exact `license_no`. If the licensee has a `successor_to` value, include predecessor violations only when the predecessor/address relationship supports the match; mark confidence as `close_address` or `uncertain` rather than `exact`.
4. For each queued license:
   - Count matched pre-boundary violations.
   - Use the latest matched violation date as `most_recent_violation_date`.
   - Sort matched violation IDs by violation date ascending, then violation ID ascending.
   - Preserve the active target license number and facility name, not the predecessor's identity.
5. Risk tier:
   - High risk usually comes from serious open or pending violations, repeated violations, high unpaid fine balances, severe alert patterns, or close/uncertain predecessor matches.
   - Medium risk usually covers lower-severity alert or fine patterns without high-risk triggers.
   - Low risk is uncommon in a manual-review queue and should be justified by the template/rules.
6. Next-step labels:
   - Use board review for severe, high-risk, or close/uncertain successor cases.
   - Use manual fine check when unpaid or nonzero fine balances drive the review.
   - Use manual ALERT check when alert flags drive the review without a stronger fine or board-review basis.
   - Use additional record check when the match is uncertain or more records are needed and the template supports it.
7. Ranking:
   - Rank only the target queue size.
   - Prioritize board-review cases first, then manual fine checks, then alert checks, then additional record checks unless the prompt/rules say otherwise.
   - Within each group, compare seriousness/open status, fine balance, violation count, alert flags, match confidence, and most recent violation date. Recheck the final order against the template's rank requirements.
8. Summary:
   - `queue_size` equals the number of queue entries.
   - Boundary date matches the prompt/rule.
   - Close or uncertain match license numbers and board-review license numbers are sorted as requested.
