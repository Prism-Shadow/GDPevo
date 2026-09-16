# Licensing Review Workflows

Use this reference after reading the prompt, local payload templates, and current environment records.

## Shared Conventions

- Prefer current, active source records over stale, cancelled, expired, dismissed, or superseded records.
- Compare dates as ISO `YYYY-MM-DD` strings only after confirming the task's operative date. Use the prompt's review date or release boundary when provided.
- Keep schema variants separate. Similar tasks may rename the same concept; emit the exact code allowed by the active `answer_template.json`.
- When a code has no allowed equivalent in the active template, omit that code rather than inventing a new key or enum value.
- Parse policy `details_json` and settlement `controls_json` into objects before using thresholds or controls.
- Include distractor records only when they are explicitly linked to a target record by the same stable ID field, a stated predecessor/successor relationship, or a clear location/address match required by the rules.

## Contractor Eligibility Batches

Fetch the contractor policy and record endpoints named by the prompt:

- `/api/policies`
- `/api/contractor/applications`
- `/api/contractor/bonds`
- `/api/contractor/insurance`
- `/api/contractor/license-history`
- `/api/contractor/violations`
- `/api/contractor/correspondence`
- `/api/contractor/inspections`

Select only the target application IDs from the prompt. For each application, map the requested trade and class to the current contractor policy whose `rule_code` and title match that trade/class. Use the policy thresholds and endorsement requirement from `details_json`.

### Application Checks

Apply these checks independently, then sort deficiency and action code arrays as the template directs:

- Bond: use the best current bond with `status == "active"` and no cancellation. If none exists, emit the template's no-current-bond code. If an active bond is below the policy minimum, emit the bond shortfall code.
- Insurance: use the best current policy record. A record is not current if its status is not active or its expiration date is before the review date. If the template distinguishes pending from expired, use pending for `status == "pending"` with a future expiration and expired for lapsed coverage. If the template has only a broader currentness code, use that. If active/current coverage is below the policy minimum, emit the insurance shortfall code.
- Experience: if `years_experience` is below the policy minimum, emit the experience shortfall code.
- Endorsement: if the policy requires an endorsement, treat missing as missing/not verified and pending as pending/not verified according to the template's available codes. Do not flag endorsements when policy `required_endorsement` is null.
- License history: if the matched prior license is suspended or notes indicate an active suspension, emit the active suspension code and the template's suspension/board-review actions.
- Violations: open serious violations create a blocking serious-complaint/serious-violation deficiency. Open minor violations create a minor-review deficiency only when the template offers one. Ignore resolved or dismissed violations for deficiency purposes unless the prompt asks for history.
- Inspections: failed or conditional `DOC_GAP` records map to document-gap codes when the template offers them. Failed or conditional `SAFETY_RECHECK` records map to safety-recheck codes when offered. Passing inspections and `NONE` findings do not create deficiencies.

### Contractor Determination And Risk

- `DENY`: use when an active suspension or unresolved open serious complaint/violation is present.
- `HOLD`: use when any deficiency remains but no denial-level issue is present.
- `APPROVE`: use only when no deficiencies remain.
- `high` risk: denial-level issues.
- `medium` risk: held applications without denial-level issues.
- `low` risk: approved applications.

### Contractor Policy Impact

Set `policy_impacted` from the current policy analysis, not from the final determination alone. Mark true when a deficiency is created by a current policy requirement that would not be purely ordinary record-currentness or discipline, especially:

- required endorsement missing or not verified;
- active bond amount below the current minimum;
- active insurance amount below the current minimum.

Do not mark true solely because coverage is expired/pending, no current bond exists, experience is short, a suspension exists, an inspection is adverse, or a violation is open.

### Contractor Summary

After item decisions are complete:

- Count approvals, holds, and denials from `determination`.
- List high-risk application IDs from item `risk_tier`.
- List policy-impacted IDs from item `policy_impacted`.
- For stale or unverified correspondence, include correspondence linked to target applications when `verified_by_agency` is false/zero or `received_date` predates the application `submitted_date`. Include linked distractor correspondence if its `related_application_id` is a target application.

## Restricted Liquor-License Staff Packages

Fetch the liquor endpoints named by the prompt:

- `/api/policies`
- `/api/liquor/applications`
- `/api/liquor/settlements`
- `/api/liquor/privileges`
- `/api/liquor/incidents`
- `/api/liquor/site-evidence`

Select the target application and target location from the prompt. Use the application `license_class` to identify ordinary standard obligations from privileges where `standard_required` is true. Keep standard obligations separate from active location-specific settlement controls.

### Same-Premises Basis

Set `same_premises_basis_applies` true when the location has any same-premises settlement/history that the current policy says matters. The same-premises basis can matter even if an older settlement control set has expired; active controls still determine `location_specific_control_codes`.

### Controls, Covered Risks, And Gaps

- `location_specific_control_codes`: union of active settlement controls for the location.
- `standard_obligation_codes`: standard-required privilege obligation codes for the application license class.
- `covered_risk_codes`: risks reasonably addressed by active controls or ordinary required obligations. For example, ID checks cover minor-sale risks; hours controls cover after-hours risks; security/CCTV controls cover assault or major safety risks; noise/patio controls cover noise and patio-boundary risks; active same-premises restrictions cover same-premises risk when the schema offers such a code.
- `verification_gap_codes`: derive from current site evidence and open records. Missing or conflicting current evidence creates the matching gap code. Open/referred incidents create follow-up gaps when the schema offers them. Open tax holds create tax-clearance/tax-hold gaps. Do not treat dismissed incidents as active risk.

### Posture

- Use `issue_restricted` when current controls and required evidence are adequate and no material follow-up remains.
- Use `request_follow_up` when controls can support restricted issuance but current evidence, open incident follow-up, tax clearance, or monitoring gaps remain.
- Use `deny` only for unresolved blocking facts that controls and follow-up cannot cure under the prompt and policy.

### First-90-Day Plan And Escalation

Build the plan from the active controls, standard obligations, and unresolved gaps. Use the template's check codes exactly.

- Put evidence checks that must exist before stable operation in `first_30_days`, such as control signage, camera walkthrough/export, food-service availability, police-memo follow-up, ID-check observation, and tax clearance.
- Put late-night operational visits in `days_31_60` unless the prompt gives a different sequence.
- Put noise/patio boundary checks after initial evidence checks, often `days_61_90`, unless they are the immediate unresolved issue.
- Escalation triggers should mirror the unresolved risks: after-hours service, missing or unavailable camera footage, food service not available, unresolved tax hold, major or violent incident, minor sale, ID-check failure, and noise/patio boundary breach.

## Alcohol Renewal Manual-Review Queues

Fetch:

- `/api/alcohol/licensees`
- `/api/alcohol/violations`
- `/api/renewal/rules`
- `/api/policies` when the prompt references policies

Select the target active licenses from the prompt. Use the prompt's boundary date or the matching renewal rule's `release_boundary`.

### Matching And Exclusions

- Include violations with `violation_date` on or before the boundary.
- Exclude violations after the boundary and list excluded IDs in the summary when requested.
- Match exact current `license_no` first.
- If a target license has `successor_to`, also match predecessor rows by predecessor license number and same address/location context; mark the queue entry `close_address` unless the template requires a different confidence label.
- Use `uncertain` only for successor/address/name matches that are plausible but not clean.
- Sort `matched_violation_ids` by violation date ascending, then violation ID ascending.

### Risk, Labels, And Ranking

Compute one queue entry per target license with at least one matched pre-boundary violation unless the template requires every target license.

- `violation_count`: number of matched pre-boundary violations.
- `most_recent_violation_date`: latest matched pre-boundary date.
- `risk_tier`: high for unresolved serious violations, high fine balances, repeated pre-boundary violations with serious themes, or successor/predecessor matches that require board attention; medium for repeated alert/fine issues without denial-level severity; low only for isolated low-risk records.
- `next_step_label` priority:
  1. `board_review` for serious unresolved patterns, high-severity current issues, close-address/successor serious matches, or dense recent violation histories.
  2. `manual_fine_check` for unpaid or positive-balance fine issues that do not require board review.
  3. `manual_ALERT_check` for alert-flagged records without stronger fine or board-review handling.
  4. `additional_record_check` for residual uncertain matches or incomplete data.

Rank the queue by next-step priority in the order above, then by most recent matched violation date descending, then by violation count descending, then by license number ascending. Assign consecutive ranks starting at 1 and trim to the requested queue size.

### Renewal Summary

- `queue_size`: length of the emitted queue.
- `boundary_date`: boundary used for inclusion.
- `post_boundary_violation_ids_excluded`: all target-linked violations excluded because they were after the boundary, sorted by ID unless the template says otherwise.
- `close_or_uncertain_match_license_numbers`: target licenses whose match confidence is not exact.
- `board_review_license_numbers`: target licenses whose next step is board review.
