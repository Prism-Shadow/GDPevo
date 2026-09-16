---
name: licensing-data-review
description: Use this skill for state licensing or regulatory review tasks that require querying a task environment and returning strict JSON decisions, staff packages, or manual-review queues. It is especially relevant for contractor application eligibility batches, restricted liquor-license transfer or renewal packages, and alcohol renewal release queues involving policies, applications, bonds, insurance, license history, violations, correspondence, settlements, privileges, incidents, site evidence, or renewal rules.
---

# Licensing Data Review

Use this skill when the user asks for a structured licensing decision or review package from a task environment. The important pattern is not memo writing; it is careful source-data reconciliation followed by schema-faithful JSON.

## Core Workflow

1. Read the prompt and the answer template before fetching data.
   - Extract the target IDs, target location, release boundary, review date, queue size, and listed endpoints.
   - Treat the template as the output contract. Use exactly its keys, enum values, ordering rules, and empty-array conventions.
2. Fetch policy records first, then the domain records.
   - Prefer SQL only if the environment explicitly provides working SQL access. Otherwise use the HTTP endpoints.
   - Large endpoints may be paginated or capped. Add a generous `?limit=1000` or query per target ID when possible.
   - Parse nested JSON fields such as `details_json` and `controls_json`.
3. Build a compact evidence table before deciding.
   - For each target, collect every directly related record and any predecessor/successor record that the source data links.
   - Keep distractor rows out of the decision, especially rows after a stated boundary date.
4. Apply the domain rules below.
5. Validate the final object against the template.
   - Return JSON only: no markdown, prose, comments, citations, or extra keys.
   - Sort arrays exactly as the template requires. Use empty arrays when no codes apply.
   - Recompute summaries from the item-level decisions so counts and ID lists cannot drift.

Optional helper: `scripts/fetch_licensing_records.py` fetches and filters the common endpoint sets. It does not make final decisions; use it to avoid missing related rows.

```bash
python scripts/fetch_licensing_records.py --base-url "$TASK_ENV_BASE_URL" contractor --ids C-ABC-001,C-ABC-002
python scripts/fetch_licensing_records.py --base-url "$TASK_ENV_BASE_URL" liquor --application-id L-ABC-001 --location-id LOC-ABC
python scripts/fetch_licensing_records.py --base-url "$TASK_ENV_BASE_URL" renewal --licenses AL-ABC-001,AL-ABC-002 --boundary YYYY-MM-DD
```

## Contractor Application Batches

Join `applications`, `bonds`, `insurance`, `license-history`, `violations`, `correspondence`, `inspections`, and contractor policies. Match the current policy by trade and requested class, using the policy `details_json` for minimum bond, minimum insurance, minimum years of experience, required endorsement, and serious-violation blocking.

For each target application:

- Experience: if `years_experience` is below the current policy minimum, add the template's experience deficiency and experience-documentation action.
- Endorsement: if the policy has a `required_endorsement`, then `missing` and `pending` endorsement statuses are deficiencies. Use the template's specific missing/pending codes when they exist; otherwise use its generic not-verified code. Add the matching obtain/verify action.
- Bond: use only current active bonds. A current bond normally has `status: active` and no cancellation. If there is no active bond, add the no-active/cancelled-bond code. If the active amount is below the current policy minimum, add the bond-shortfall code and increase-bond action.
- Insurance: use active, verified, unexpired insurance for current coverage. If the prompt supplies a review date, compare expiration to that date. Pending insurance is not current unless the template has a separate pending/binding code. If the active current amount is below the minimum, add the insurance-shortfall code.
- License history: a linked prior license with `status: suspended` is an active-suspension blocker. Add the suspension deficiency, board-review/clear-suspension action, high risk, and a denial determination if the template supports denial.
- Violations and complaints: open serious violations block or require denial/board review. Open minor violations are hold-level deficiencies when the template includes a minor/open-violation code. Resolved or dismissed rows are not blockers.
- Inspections: add document-gap or safety-recheck deficiencies only when the template exposes those codes and the inspection result/finding shows a live gap or failed recheck. Passing inspections do not create deficiencies.
- Correspondence summary: include target-related correspondence IDs that are unverified, explicitly stale, or explicitly conflicting. Do not treat every pre-application record as stale unless the record says so or the template calls for that broader rule.

Determination and risk:

- `DENY`: active suspension, open serious violation/complaint, or another explicit blocker in policy/template.
- `HOLD`: at least one non-blocking deficiency remains.
- `APPROVE`: no deficiencies remain.
- Risk is usually `high` for denial blockers, `medium` for holds, and `low` for approvals unless the template or policy gives a more specific risk rule.

`policy_impacted` means the current policy standard materially changed the analysis. Mark it true for deficiencies created by current-policy requirements such as required endorsements or stricter bond thresholds compared with the legacy baseline. Do not mark it true for generic currentness problems, cancelled documents, active suspensions, or open violations unless a policy record specifically says the current policy changes that issue.

Common contractor code mapping:

- Missing or pending endorsement -> `endorsement_missing`, `endorsement_pending`, or `endorsement_not_verified`.
- No active/cancelled bond -> `bond_cancelled` or `no_active_bond`.
- Low bond -> `bond_shortfall`.
- Pending, expired, or non-current insurance -> `insurance_pending`, `insurance_expired`, or `insurance_not_current`.
- Low insurance -> `insurance_shortfall`.
- Open serious issue -> `open_serious_violation` or `unresolved_serious_complaint`.
- Actions should be the template's paired remediation codes, not invented prose.

## Restricted Liquor-License Packages

Join `liquor/applications`, `settlements`, `privileges`, `incidents`, `site-evidence`, and liquor policies. Use the target application and location from the prompt.

Separate three concepts:

- Standard obligations come from `privileges` for the application license class where `standard_required` is true.
- Location-specific controls come from active settlement `controls_json.controls` for the target location.
- Covered risks are the risk bases and incident risks currently addressed by active controls; they are not the same list as standard obligations.

Decision rules:

- `same_premises_basis_applies` is true when the location has any same-premises settlement/history and policy says same-premises history matters, even if that settlement is not the currently active control.
- Ignore dismissed incidents for live gaps. Open, referred, or unresolved incidents can create verification gaps and monitoring or escalation items.
- Treat active controls as covering related risks:
  - `HOURS` covers after-hours risk.
  - `ID_CHECK` covers minor-sale or sale-to-minor risk.
  - `SECURITY` and `CCTV` cover assault/public-safety and camera-control risks.
  - `FOOD_SERVICE` covers food-service-gap risk.
  - `NOISE` and `PATIO` cover noise, patio-boundary, and adjacent-neighborhood risks.
- Site evidence creates verification gaps when it is missing, conflicting, stale, or identity-conflicted. Map the evidence code and status into the exact template vocabulary, for example current-missing control signage, conflicting floor plan, police memo conflict, missing camera evidence, missing food-service evidence, unresolved tax hold, or late-night monitoring needed.
- `recommended_posture` is usually `request_follow_up` when verification gaps or open/referred incidents remain, `issue_restricted` when risks are covered and evidence is current, and `deny` only for an explicit blocker or severe unresolved condition.

First-90-day plan:

- Put evidence verification and document follow-up in the first 30 days.
- Put after-hours or late-night closing checks in days 31-60 unless the prompt says otherwise.
- Put noise/patio boundary checks later in the first 90 days when active controls cover those risks.
- Add observation/walkthrough checks for active controls that need field confirmation, such as ID checks, CCTV/security, food service, signage, and police memo follow-up.

Escalation triggers should mirror the live residual risks and controls: after-hours violations, unverified control signage, unresolved minor sale, security/CCTV failure, missing camera coverage or footage, food-service unavailability, noise/patio breach, open tax hold, and major or violent incidents when the template includes those codes.

## Alcohol Renewal Manual-Review Queues

Join `alcohol/licensees`, `alcohol/violations`, `renewal/rules`, and renewal policies.

Build the queue as follows:

- Use the release boundary from the prompt or matching renewal rule. Include only violations known on or before that boundary.
- Exclude post-boundary violations from queue matching, but list their IDs in the summary field when requested.
- Start from the active target licenses. Add predecessor records when a target license has `successor_to`; match predecessor violations by old license number and close address/facility evidence.
- Set `match_confidence` to `exact` for direct license matches, `close_address` for successor/predecessor matches with the same or clearly close address, and `uncertain` when the match is plausible but weak.
- For each queue entry, count matched pre-boundary violations, set the most recent matched date, and sort matched violation IDs by violation date ascending, then violation ID ascending.

Classify and rank:

- `board_review`: use for serious or repeated public-safety problems, sale-to-minor issues, unresolved successor/predecessor serious issues, or other rule-specified board triggers.
- `manual_fine_check`: use for positive fine balances, unpaid-fine themes, tax-hold/fine issues, or non-board cases where money status must be reviewed.
- `manual_ALERT_check`: use for alert-flagged records that do not need board review or fine review.
- `additional_record_check`: use for weak matches, missing evidence, or records that need more identity work before a substantive review.
- Risk is `high` for board-review cases, repeated violations, serious unresolved matters, or high fine exposure; `medium` for lower-severity alert/fine cases; `low` only when the template still requires a queue item but the evidence is minor.
- Rank first by next-step severity (`board_review`, then `manual_fine_check`, then `manual_ALERT_check`, then `additional_record_check`), then by most recent matched violation date descending, then violation count descending, then license number ascending unless the prompt or renewal rule gives a different priority.

The summary must echo the queue size and boundary date, list excluded post-boundary violation IDs, list close/uncertain match license numbers, and list board-review license numbers when those fields exist.

## Final Checks

Before answering:

- Confirm every requested target ID appears exactly once, or the queue has exactly the requested size and rank sequence.
- Confirm every enum value appears in the template.
- Confirm all required action lists and summary counts are derived from the final item decisions.
- Confirm there are no citations, markdown fences, explanatory text, or extra keys outside the JSON object.
