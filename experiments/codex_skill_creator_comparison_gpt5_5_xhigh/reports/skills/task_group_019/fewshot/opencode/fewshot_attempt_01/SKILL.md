---
name: licensing-record-json-review
description: Use this skill for licensing-environment tasks that ask Codex to produce strict JSON decisions from contractor, liquor, alcohol renewal, policy, incident, financial coverage, correspondence, inspection, settlement, privilege, or site-evidence records. Trigger for State Contractors Licensing Board eligibility batches, restricted liquor-license staff packages, alcohol renewal manual-review queues, and similar prompts that reference TASK_ENV_BASE_URL endpoints and an answer_template.json schema.
---

# Licensing Record JSON Review

Use this skill to solve structured licensing review tasks against a task environment. The usual failure modes are incomplete endpoint reads, mixing distractor records into the target set, treating schema enums loosely, and writing prose outside the required JSON.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before fetching data.
2. Extract the target identifiers, review date or release boundary, required output keys, enum values, list ordering rules, and any target queue size.
3. Resolve `<TASK_ENV_BASE_URL>` from the prompt or environment instructions.
4. Fetch `GET /api/policies` and every domain endpoint named in the prompt.
5. Filter every dataset to the prompt targets. Prefer endpoint query parameters such as `?application_id=...`, `?location_id=...`, `?license_no=...`, and `?license_class=...` when available; unfiltered endpoints may be paged and may include many distractors.
6. Use SQL only when the environment gives a valid token or clear access instructions. Keep SQL target-restricted.
7. Build an intermediate worksheet per target: source records, applied policy thresholds, derived codes, and exclusions. Use it for reasoning, not final output.
8. Emit only JSON matching the template. Do not include citations, comments, markdown, or extra keys.
9. Validate before final: exact top-level keys, allowed enum values only, required lengths, sorted arrays when specified, summary counts derived from item decisions, and empty arrays instead of omitted fields.

Use current records over older records when statuses conflict. Treat `related_application_id` as an application link for contractor correspondence, inspections, and violations. For financial endpoints, fetch by each target `application_id`; unfiltered responses may not include every target row.

## Contractor Batch Reviews

Use this section when the prompt references contractor applications, bonds, insurance, license history, violations, correspondence, inspections, or State Contractors Licensing Board policies.

Fetch:

- `/api/policies`, filtered to `family == "contractor"`
- `/api/contractor/applications`
- `/api/contractor/bonds?application_id=<id>` for each target
- `/api/contractor/insurance?application_id=<id>` for each target
- `/api/contractor/license-history`, joined by `prior_license_id`, applicant name, or target-linked history
- `/api/contractor/violations`, joined by `related_application_id` and prior license IDs
- `/api/contractor/correspondence`, joined by `related_application_id`
- `/api/contractor/inspections`, joined by `related_application_id`

### Apply Contractor Policies

Map each application to the current contractor policy by trade and requested class. Use `details_json` for minimum bond, minimum insurance, minimum years of experience, required endorsement, and whether serious open violations block.

For each target application:

- Bond:
  - Use the active, uncancelled current bond.
  - If no active current bond exists, use the template's no-current-bond code (`no_active_bond`, `bond_cancelled`, or equivalent) and its action.
  - If an active bond exists but `amount < minimum_bond`, add the template's bond-shortfall code and increase-bond action.
- Insurance:
  - Treat status `pending` as not current or pending, using the enum available in the template.
  - Treat status `expired`, an expiration before the review date, or no current record as expired/not current.
  - If insurance is current but `amount < minimum_insurance`, add the insurance-shortfall code and increase-insurance action.
- Endorsement:
  - If the policy has a required endorsement and application endorsement status is `missing`, add the missing/not-verified endorsement code.
  - If status is `pending`, use a pending code when the template distinguishes it; otherwise use the generic not-verified code.
  - Do not add endorsement deficiencies when the policy `required_endorsement` is null or the application says not required.
- Experience:
  - If `years_experience < minimum_years_experience`, add experience-shortfall and documentation action codes.
- License history:
  - Active `suspended` history means active suspension, board review, and clearance action.
- Violations and complaints:
  - Open serious violations or unresolved serious complaints block issuance: add the serious/open code, resolution action, and board review when available.
  - Open minor violations create a hold/review action when the template supports minor-violation codes.
  - Resolved or dismissed records do not create deficiency codes.
- Inspections:
  - If the template has inspection codes, map failing or conditional `DOC_GAP` to document-gap action and failing `SAFETY_RECHECK` to safety-recheck action.
  - Passing inspections do not create deficiencies.
- Correspondence summary:
  - Add stale or unverified correspondence IDs when `verified_by_agency` is false, or when notes/assertion values indicate stale, unverified, conflicting, or superseded evidence.
  - Sort correspondence IDs lexically in the summary.

### Contractor Determination

Use the template's exact enum names:

- `DENY` when an active suspension, open serious violation, or unresolved serious complaint blocks approval.
- `HOLD` when any nonblocking deficiency remains.
- `APPROVE` only when no deficiency code remains.

Use `high` risk for deny/board-review cases, `medium` for holds, and `low` for approvals unless the prompt or template gives a stricter risk rule.

Set `policy_impacted` when a current 2025 policy standard materially creates the deficiency or review flag compared with the prior baseline, especially raised bond/insurance thresholds or newly required trade/class endorsements. Do not mark it just because a record is expired, pending, suspended, or unresolved unless the current policy itself caused that result.

Sort `deficiency_codes` and `required_actions` lexically unless the template says otherwise. Summary counts must equal the per-application determinations.

## Restricted Liquor Staff Packages

Use this section when the prompt references liquor applications, settlements, privileges, incidents, site evidence, restricted issuance, controls, or first-90-day monitoring.

Fetch:

- `/api/policies`, filtered to `family == "liquor"`
- `/api/liquor/applications?application_id=<target>`
- `/api/liquor/settlements?location_id=<location>`
- `/api/liquor/privileges?license_class=<license_class>`
- `/api/liquor/incidents?location_id=<location>`
- `/api/liquor/site-evidence?location_id=<location>`

Parse each settlement `controls_json`. Standard obligations come from privilege rows where `standard_required` is true. Location-specific controls come from active settlement controls, even if some overlap with standard obligations.

### Liquor Derived Fields

- `same_premises_basis_applies`: true when settlement history includes `SAME_PREMISES` and policy says same-premises history matters, even if the historic settlement is no longer active.
- `standard_obligation_codes`: class-level required privilege codes only.
- `location_specific_control_codes`: active current controls tied to the location.
- `covered_risk_codes`: include risks currently addressed by active controls or standard obligations, not every historical incident. Common mappings:
  - `HOURS` covers `AFTER_HOURS`.
  - `ID_CHECK` covers `MINOR_SALE`, `SALE_TO_MINOR`, and `ID_CHECK`.
  - `FOOD_SERVICE` covers `FOOD_SERVICE_GAP`.
  - `CCTV` covers `CAMERA_COVERAGE`; together with `SECURITY` it can cover assault/public-safety concerns.
  - `NOISE` covers `NOISE`.
  - `PATIO` covers patio-boundary risk.
  - Active `SAME_PREMISES` basis covers `SAME_PREMISES`.
  - Ignore dismissed incidents as covered risks unless the prompt says dismissed history still matters.
- `verification_gap_codes`: derive from missing/conflicting/stale site evidence, unresolved incidents, and prompt-specific concerns. Map using the template's enum spelling:
  - Conflicting or missing current control signage -> control-signage codes.
  - Conflicting or stale floor plans -> floor-plan codes.
  - Conflicting police memo or an open/referred incident needing staff follow-up -> police-memo or open-incident code.
  - Required or prompted camera evidence with no current verified evidence -> camera evidence missing.
  - Required food service evidence with no current verified evidence -> food service evidence missing.
  - Open tax holds -> tax-hold unresolved/missing clearance.
  - Late-night risk without verified controls -> late-night monitoring needed.

### Liquor Posture, Plan, and Triggers

Recommend `request_follow_up` when verification gaps, unresolved incidents, tax holds, or unverified controls remain. Recommend `issue_restricted` only when required obligations and location controls are current and no follow-up gap remains. Recommend `deny` only for a blocking board-order, unresolved major incident, or explicit disqualifier.

Build `first_90_day_plan` from gaps and active controls:

- signage/control verification -> first 30 days
- police memo or open incident follow-up -> first 30 days
- ID/minor-sale concerns -> first 30 days
- CCTV/security/camera checks -> first 30 days
- food-service checks -> first 30 days
- after-hours or late-night visit -> days 31-60 unless the template says otherwise
- noise/patio boundary checks -> days 61-90 unless the prompt prioritizes immediate action

Use the template's ordering rule. Some templates require check-code sorting; others expect operational sequence.

Set escalation triggers from unresolved risks and control failures using the template spellings: after-hours service/violation, missing or unverified camera/CCTV, footage not produced, food service unavailable, noise or patio breach, open tax hold, unresolved referred minor sale, major or violent incident, control-signage failure, and ID-check failure.

## Alcohol Renewal Manual-Review Queues

Use this section when the prompt asks for a ranked alcohol renewal queue with licensees, violations, release boundary, match confidence, risk tier, and next-step labels.

Fetch:

- `/api/alcohol/licensees`, filtered to active target license numbers from the prompt
- `/api/alcohol/violations?license_no=<license_no>` for each current target
- `/api/alcohol/violations?license_no=<successor_to>` when a target license has a predecessor/successor relationship
- `/api/renewal/rules`, selecting the rule matching the prompt's release boundary

### Match and Exclude Violations

- Include violations known on or before the prompt boundary date.
- Exclude later violations and collect their IDs in the summary.
- Prefer exact current-license matches.
- Include predecessor/successor violations only when `successor_to` links the target and the address is the same or close enough to establish continuity. Mark `match_confidence` as `close_address` for these included predecessor rows; use `uncertain` when the link is plausible but address/name evidence is weak.
- Use `exact` when all matched violations are on the current target license.
- Sort `matched_violation_ids` by violation date ascending, then violation ID ascending.

### Queue Fields

For each target:

- `violation_count`: number of included pre-boundary matched violations.
- `most_recent_violation_date`: latest included pre-boundary violation date.
- `risk_tier`:
  - `high` for board-review cases, unpaid-fine hold cases, or unresolved/pending serious violations.
  - `medium` for alert-only or lower-severity unresolved rows.
  - `low` only when records are clean or low-priority under the selected rule.
- `next_step_label`, in priority order:
  1. `board_review` for unresolved sale-to-minor concerns, serious successor/predecessor concerns, or other board-level triggers in the selected rule.
  2. `manual_fine_check` when unpaid or positive fine balances require hold review and board review does not apply.
  3. `manual_ALERT_check` when alert flags require review and neither board nor fine-check priority applies.
  4. `additional_record_check` for remaining close, uncertain, or incomplete records.

Rank the queue by next-step priority first (`board_review`, then `manual_fine_check`, then `manual_ALERT_check`, then `additional_record_check`), then by most recent included violation date descending, then by violation count descending, then license number ascending. Assign ranks from 1 with no gaps and truncate or include to the prompt's target queue size.

Summary:

- `queue_size`: actual number of queue entries returned.
- `boundary_date`: prompt boundary date.
- `post_boundary_violation_ids_excluded`: all excluded target post-boundary IDs, sorted by violation ID.
- `close_or_uncertain_match_license_numbers`: licenses whose match confidence is not exact, sorted.
- `board_review_license_numbers`: licenses assigned board review, sorted.

## Final JSON Check

Before answering:

- Re-read the template and remove any key not allowed there.
- Convert booleans to JSON booleans, not strings or integers.
- Sort arrays exactly as required by each field.
- Deduplicate codes.
- Ensure counts and summary ID lists are derived from the final item list, not from earlier scratch notes.
- Return only the JSON object.
