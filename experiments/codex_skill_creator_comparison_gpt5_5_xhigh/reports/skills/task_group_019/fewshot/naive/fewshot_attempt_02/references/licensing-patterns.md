# Licensing Patterns

Use this reference after identifying the task family from the prompt and endpoints.

## Contractor Eligibility Batches

Fetch contractor policies plus applications, bonds, insurance, license history, violations, correspondence, and inspections for the target application IDs.

Policy matching:

- Match the application trade/class to the current contractor policy and parse `details_json`.
- Compare against `minimum_bond`, `minimum_insurance`, `minimum_years_experience`, `required_endorsement`, and `serious_open_violation_blocks`.
- Use the legacy contractor policy only for `policy_impacted`: mark true when a current policy standard creates a material deficiency that would not apply under the prior baseline, such as a new specialty endorsement requirement or a threshold that exceeds the prior reduced bond baseline.

Application-level review:

- Experience: if `years_experience` is below the policy minimum, use the template's experience-shortfall code and action.
- Endorsement: if a policy requires an endorsement, `verified` clears it; `missing`, `pending`, or similarly unverified states create the matching template code/action.
- Bond: choose the current active bond as of the review date. If none exists, use a cancelled/no-active-bond code if allowed. If active amount is below the policy minimum, use the shortfall code/action.
- Insurance: require current active/bound coverage through the review date and amount at or above the policy minimum. Map pending, expired/not-current, and amount shortfall to the closest allowed template codes.
- Prior license history: active or unresolved suspension is a blocking condition.
- Violations/complaints: open serious violations or unresolved serious complaints are blocking conditions; open minor violations are hold-level issues only when the template supports them.
- Inspections: map documented finding codes such as document gaps or safety rechecks only when the answer template has corresponding allowed codes.

Determination and risk:

- `DENY` for blocking conditions such as active suspension or unresolved serious violation/complaint.
- `HOLD` for nonblocking deficiencies requiring applicant or agency follow-up.
- `APPROVE` only when no applicable deficiency remains.
- Risk is normally `high` for denial/blocking conditions, `medium` for holds, and `low` for approvals.

Summary:

- Counts must equal the number of item decisions by determination.
- High-risk and policy-impacted ID lists come directly from item fields.
- Include correspondence IDs that are not agency-verified or are explicitly stale. Sort IDs lexically.

## Restricted Liquor-License Staff Packages

Fetch policies, the target liquor application, settlements for the target location, privileges for the application license class, incidents for the location, and site evidence for the location.

Core derivations:

- `same_premises_basis_applies` is true when policy says same-premises history matters and the location has any same-premises settlement history, even if the particular control set is no longer active.
- `standard_obligation_codes` come from privilege rows for the license class where `standard_required` is true, limited to template-allowed codes.
- `location_specific_control_codes` are the union of active controls in settlement `controls_json`, limited to template-allowed codes. Keep these separate from standard obligations even when codes overlap.
- `covered_risk_codes` are risks actually covered by active controls or applicable same-premises history. Common mappings are `HOURS` to after-hours risk, `SECURITY`/`CCTV` to public-safety or assault risk, `ID_CHECK` to minor-sale risk, `FOOD_SERVICE` to food-service risk, `NOISE` to noise risk, and `PATIO` to patio-boundary risk. Use the exact risk code names available in the template.
- `verification_gap_codes` come from missing, conflicting, stale, or absent required evidence; unresolved/open/referral incidents; tax holds; and prompt-specific required evidence such as camera, food-service, signage, police memo, floor plan, neighbor notice, or site photos.

Posture, monitoring, and escalation:

- Use `request_follow_up` when verification gaps remain or unresolved incidents need staff review.
- Use `issue_restricted` when current controls cover the relevant risks and no material verification gap remains.
- Reserve `deny` for a disqualifying unresolved issue supported by policy and the template.
- Build `first_90_day_plan` from gaps and active controls using only allowed check codes. Put early verification checks in the first 30 days, operational visits in days 31-60, and longer monitoring checks in days 61-90 unless the template states a different order.
- Escalation triggers should mirror the risks that would defeat the restricted posture, such as missing camera coverage, failure to produce footage, after-hours service, food service not available, open tax hold, unreported violent incident, minor sale, patio/noise breach, or control signage failure.

## Alcohol Renewal Manual-Review Queues

Fetch licensees, violations, renewal rules, and policies. Use the boundary date and queue size from the prompt, and confirm the matching renewal rule when available.

Matching:

- Match violations exactly by `license_no` first.
- Include predecessor/successor records when the licensee has `successor_to` or the rule calls for successor matching. Mark confidence `close_address` when predecessor rows match by address/facility but not current license number; use `uncertain` for weaker identity evidence.
- Exclude every violation after the release boundary from queue calculations, and list those excluded IDs in the summary when the template asks for them.

Queue fields:

- `matched_violation_ids`: sort by violation date ascending, then violation ID ascending.
- `violation_count`: count only matched pre-boundary violations.
- `most_recent_violation_date`: maximum matched pre-boundary date.
- `match_confidence`: exact, close address, or uncertain based on the weakest included match.
- `risk_tier`: high for serious/open, successor-linked, high-fine, high-count, or repeated alert cases; medium for lower-severity repeated cases; low for minimal manual-review evidence.
- `next_step_label`: prioritize `board_review` for serious unresolved, successor-linked, or sale-to-minor/public-safety patterns requiring board attention; otherwise use `manual_fine_check` for unpaid-fine or material fine-balance issues; otherwise use `manual_ALERT_check` for alert-flag review; use `additional_record_check` for weak identity matches or incomplete records.

Ranking:

- Rank only target current licenses requested by the prompt.
- Sort primarily by next-step priority: board review, fine check, alert check, additional record check.
- Within the same priority, sort by higher risk, newer most-recent violation date, larger matched count, and then stable license number.
- Assign contiguous integer ranks beginning at 1 and cap the queue at the requested size.

Summary:

- `queue_size` must equal the queue length.
- `boundary_date` must equal the prompt/rule boundary.
- Sort post-boundary excluded violation IDs lexically.
- Sort close/uncertain match license numbers and board-review license numbers lexically.
