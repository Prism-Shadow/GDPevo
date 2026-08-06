---
name: licensing-review-json
description: Use when producing strict JSON decisions, staff packages, or manual-review queues from a licensing data environment for contractor, restricted liquor, or alcohol-renewal review tasks.
---

# Licensing Review JSON

Use this skill for licensing tasks that provide a base URL, REST endpoints or SQL access, and an `input/payloads/answer_template.json` schema. The job is to derive structured review results from the data service and return only the JSON object required by the template.

## Core Workflow

1. Read the user prompt and the answer template before querying data. Extract target IDs, review date or boundary date, queue size, required top-level keys, allowed enum codes, and ordering rules.
2. Resolve `<TASK_ENV_BASE_URL>` only from the environment access instructions provided with the task. If SQL is allowed, include the required token/header from those instructions.
3. Fetch `/api/policies` and the task's listed business endpoints. Prefer SQL for complete target-specific record pulls when it is available, because public GET lists may be capped or ordered so target records are missing.
4. Parse embedded JSON fields such as `details_json` and `controls_json`.
5. Build an intermediate worksheet keyed by the stable target ID. Keep notes internally, but the final response must be only JSON matching the template. Never include markdown, citations, comments, or extra keys.
6. Normalize output to the template: use only allowed enum values, empty arrays when no values apply, de-duplicate arrays, and apply every ordering rule exactly.

## SQL Patterns

Use table names that mirror endpoint names, for example `policies`, `contractor_applications`, `contractor_bonds`, `contractor_insurance`, `contractor_license_history`, `contractor_violations`, `contractor_correspondence`, `contractor_inspections`, `liquor_applications`, `liquor_settlements`, `liquor_privileges`, `liquor_incidents`, `liquor_site_evidence`, `alcohol_licensees`, `alcohol_violations`, and `renewal_rules`.

Issue focused queries for the target IDs or locations, not broad table dumps. If a SQL endpoint returns `truncated: true`, add narrower `where` clauses.

## Contractor Batch Decisions

Use this workflow when the schema has `application_decisions` and contractor deficiency/action fields.

Data joins:

- Target applications come from the prompt and template.
- Match current contractor policies by `family = contractor`, trade, and requested class. Use the latest effective policy on or before the review date. Use legacy contractor policy only for `policy_impacted`.
- Join bonds, insurance, correspondence, and inspections by `application_id`.
- Join license history by `prior_license_id`.
- Join violations by `related_application_id`; also include rows for the prior license when that relationship is material.

Deficiency rules:

- Bond: active only means `status = active` and no cancellation before the review date. If no active bond exists, use the template's no-active-bond code such as `no_active_bond` or `bond_cancelled`. If an active bond exists but its amount is below policy minimum, use the template's bond-shortfall code.
- Insurance: require an active policy, amount at least the policy minimum, and expiration on or after the review date. Pending insurance is not current; use `insurance_pending` when available, otherwise `insurance_not_current`. Expired active insurance uses `insurance_expired` when available. Low active coverage uses an insurance-shortfall code.
- Endorsement: if the current policy requires an endorsement, `missing` and `pending` statuses are deficiencies. Use exact codes such as `endorsement_missing` or `endorsement_pending` when available; otherwise use the template's not-verified code.
- Experience: years of experience below policy minimum is an experience-shortfall deficiency.
- License history: a suspended prior license is an `active_suspension` deficiency.
- Violations: open serious violations or complaints block approval and use the template's serious/open complaint code. Open minor violations are only output when the template has an open-minor code. Dismissed or resolved rows do not create application deficiencies.
- Inspections: failed or conditional `DOC_GAP` findings create an inspection document-gap deficiency when the template supports it. Failed `SAFETY_RECHECK` findings create a safety-recheck deficiency when supported. Passed findings are not deficiencies.

Required actions should follow the deficiency using the action vocabulary available in the template. Typical pairings are:

- bond shortfall: increase bond amount.
- no active or cancelled bond: file or obtain a current bond.
- insurance expired or not current: provide or renew current insurance.
- insurance pending: verify insurance binding.
- insurance shortfall: increase insurance amount.
- endorsement missing: obtain required endorsement.
- endorsement pending or not verified: verify endorsement.
- experience shortfall: submit or document experience evidence.
- active suspension: board review and clear or review the suspension.
- open serious violation/complaint: resolve the violation or complaint and send to board review when that action exists.
- open minor violation: resolve minor violation review.
- inspection document gap or safety recheck: clear the document gap or complete the safety recheck.

Determination and risk:

- `DENY` when an active suspension or open serious violation/complaint exists.
- `HOLD` when there is any deficiency but no denial blocker.
- `APPROVE` only when no deficiencies remain.
- Risk is `high` for denial blockers, `medium` for holds, and `low` for approvals unless the prompt/template defines a stricter tier rule.

`policy_impacted` is true only when a current policy threshold or endorsement rule creates a material deficiency that would not have applied under the prior baseline. Do not mark ordinary stale documents, expired coverage, suspensions, or open violations as policy impacts by themselves.

The summary counts must be computed from application decisions. High-risk and policy-impacted ID lists are sorted. For stale or unverified correspondence, include correspondence that is not agency-verified or is stale/conflicting on its face, unless another field clearly says it was verified by licensing staff.

## Restricted Liquor Staff Packages

Use this workflow when the schema asks for `recommended_posture`, `same_premises_basis_applies`, risk/control code arrays, a first-90-day plan, and escalation triggers.

Data joins:

- Select the target liquor application and target location from the prompt.
- Join settlements, incidents, and site evidence by `location_id`.
- Load privilege rows for the application's `license_class`.
- Current location-specific controls are the union of controls in active, unexpired settlement `controls_json`.
- Standard obligations are privilege rows with `standard_required = 1`; keep these separate from location-specific controls.

Field rules:

- `same_premises_basis_applies` is true when same-premises settlement history exists for the location and the prompt asks whether that basis remains applicable; otherwise rely on the active current basis.
- `covered_risk_codes` should reflect risks actually addressed by current controls or current active settlement bases. Translate controls where the template uses risk vocabulary, such as patio controls to patio-boundary risk. Do not include dismissed incidents as covered risks unless a current control is explicitly tied to that risk.
- Include open or referred incident risks when current controls address them; otherwise they usually become verification gaps.
- `verification_gap_codes` come from missing, conflicting, stale, or identity-mismatched evidence; open/referred incidents; unresolved tax holds; and prompt-specific verification needs such as camera, food-service, floor-plan, signage, police-memo, neighbor-notice, site-photo, or late-night monitoring.
- `recommended_posture` is `request_follow_up` when verification gaps or unresolved incidents remain, `deny` for unresolved major blockers that cannot be conditioned, and `issue_restricted` when current controls cover the risks and no material verification gaps remain.

Common evidence and gap mappings:

- `CONTROL_SIGNAGE` missing/conflicting: use the template's control-signage missing/conflicting code.
- `FLOOR_PLAN` conflicting/stale: use the floor-plan conflicting or stale code.
- `POLICE_MEMO` conflicting or identity-mismatched: use the police-memo code when available.
- Missing camera/CCTV evidence: use the template's camera/CCTV evidence gap and include a camera walkthrough/export check when available.
- Missing food-service evidence for a class with a food-service standard: use the food-service evidence gap and include a food-service check when available.
- Open tax hold: use the tax-hold gap and tax-clearance or tax-hold escalation code when available.
- Open or referred minor-sale incident: use incident follow-up and referred-minor-sale escalation codes when available.

For the `first_90_day_plan`, pick checks that directly test unresolved gaps and active controls. Evidence and record verification usually belongs in `first_30_days`; late-night or after-hours field visits usually belong in `days_31_60`; noise/patio boundary monitoring often belongs in `days_61_90`. Follow any ordering rule in the template; otherwise use operational sequence.

Escalation triggers should mirror the risk and gap set: after-hours service, unverified control signage, major incidents, unresolved minor-sale referrals, camera/security failure, missing footage, missing food service, noise/patio breach, and uncleared tax holds, using only codes allowed by the template.

## Alcohol Renewal Manual-Review Queue

Use this workflow when the schema has a ranked `queue` and `summary` for alcohol license renewals.

Data joins and filtering:

- Target active licensees come from the prompt and template. Ignore inactive licensees except when an active target has a `successor_to` license.
- Use the boundary date from the prompt; if absent, select the matching `renewal_rules` row and use `release_boundary` or `details_json.use_violations_on_or_before`.
- Include exact violations for the current `license_no` with `violation_date <= boundary`.
- If the target has `successor_to`, include predecessor violations only when the predecessor record is an unambiguous address/facility continuation. Mark `match_confidence` as `close_address` for a clean predecessor match and `uncertain` when names or addresses conflict.
- Exclude violations after the boundary, but list their IDs in `summary.post_boundary_violation_ids_excluded` sorted by ID.

Queue fields:

- `matched_violation_ids`: sort by violation date ascending, then ID ascending.
- `violation_count`: count only matched pre-boundary violations.
- `most_recent_violation_date`: latest date among matched violations used for ranking.
- `match_confidence`: `exact` when only current-license exact rows were used, `close_address` for clean successor/address matches, and `uncertain` for ambiguous matches.
- `next_step_label`: use `board_review` for successor/close-address serious matches, unresolved serious control risks, or repeated high-risk themes such as sale-to-minor, tax-hold, or after-hours issues. Use `manual_fine_check` when unpaid fines or positive balances require a hold and board review is not required. Use `manual_ALERT_check` when alert flags require manual review but no stronger label applies. Use `additional_record_check` for uncertain matches or incomplete identity evidence.
- `risk_tier`: `high` for board review, unresolved serious violations, significant unpaid-fine review, or repeated violations; `medium` for alert-only or older lower-severity queues; `low` only for minimal residual manual checks.

Ranking:

1. Build candidates with at least one matched pre-boundary violation or other rule-triggering manual-review reason.
2. Assign action priority: `board_review`, then `manual_fine_check`, then `manual_ALERT_check`, then `additional_record_check`.
3. Within the same action priority, sort by most recent matched violation date descending, then violation count descending, unresolved serious count descending, positive fine balance descending, and license number ascending.
4. Emit ranks `1..N` with no gaps and truncate to the requested queue size.

The summary queue size must equal the emitted queue length. `close_or_uncertain_match_license_numbers` contains every queued license whose confidence is not exact. `board_review_license_numbers` contains every queued license with `next_step_label = board_review`, sorted by license number.
