---
name: licensing-review-json
description: Use for licensing review tasks that query a provided task environment, apply contractor, restricted liquor, or alcohol renewal policies, and return a schema-only JSON decision package.
---

# Licensing Review JSON

Use this skill when a task asks for a structured licensing decision, staff package, or manual-review queue using a task environment. The common job is to gather policy and record evidence, map it into allowed output codes, and return only JSON conforming to the provided answer template.

## Operating Rules

1. Read the prompt, `environment_access.md`, and the referenced `input/payloads/answer_template.json`.
2. Use only endpoints authorized in `environment_access.md`. Use the provided base URL and the SQL token/header exactly as given.
3. Fetch `/api/policies` first, then fetch only the record families named in the prompt.
4. Prefer targeted SQL when GET endpoints are capped or broad. Endpoint-backed table names generally mirror the endpoint family, for example `contractor_applications`, `contractor_bonds`, `liquor_settlements`, `alcohol_violations`, and `renewal_rules`.
5. Do not use the system date for business cutoffs unless the prompt says to. Use the prompt's review date, release boundary, or policy boundary. If no date is supplied, rely on record statuses and the task's batch context.
6. Treat the answer template as the source of truth for field names, allowed codes, ordering, counts, and whether optional fields are allowed.
7. Return only the JSON object. No prose, markdown, comments, citations, or extra keys.

## Data Gathering

For contractor reviews, collect:

- policies
- applications
- bonds
- insurance
- license history
- violations
- correspondence
- inspections

For restricted liquor staff packages, collect:

- policies
- liquor applications
- settlements
- privileges
- incidents
- site evidence

For alcohol renewal queues, collect:

- licensees
- violations
- renewal rules

Use SQL `WHERE` clauses for target IDs, location IDs, license numbers, predecessor licenses, and date boundaries. Avoid dumping unrelated rows.

## Contractor Eligibility

Select the contractor policy by trade and requested class. Apply the current policy thresholds:

- minimum active bond amount
- minimum active/current insurance amount
- minimum years of experience
- required endorsement, if any
- serious open violation blocking rule

Evidence mapping:

- Active bond means a bond row with active status, no cancellation, and an amount meeting the current threshold. Missing/cancelled active coverage maps to the template's no-active-bond or cancelled-bond code. Active but under threshold maps to bond shortfall.
- Current insurance means active status, not expired as of the review date or task boundary, and an amount meeting the threshold. Pending insurance maps to a pending/not-current code when the template has one. Expired coverage maps to expired/not-current. Under-threshold coverage maps to insurance shortfall.
- Endorsement status `verified` satisfies a required endorsement. `missing` maps to the missing/not-verified endorsement code. `pending` maps to pending/not-verified and usually a verification action.
- Years below the policy minimum map to experience shortfall.
- Prior license history with suspended status maps to active suspension and is a high-risk blocker.
- Open serious violations or unresolved serious complaints map to serious violation/complaint codes and are high-risk blockers. Open minor violations usually create hold-level review codes.
- Inspection finding `DOC_GAP` with non-pass result maps to document-gap deficiency/action codes. `SAFETY_RECHECK` with non-pass result maps to safety-recheck codes.
- Correspondence is stale or unverified when it is not agency-verified, predates the application while being used as support, says applicant-only/unverified/pending/conflicting, or otherwise conflicts with registry evidence. Include those IDs in summary fields when requested.

Decision posture:

- `DENY`: active suspension, open serious violation/complaint, or another policy blocker.
- `HOLD`: fixable financial, endorsement, experience, minor-violation, correspondence, or inspection deficiencies.
- `APPROVE`: no blocking or hold-level deficiencies.

Risk tier:

- `high`: denial blocker, active suspension, open serious violation/complaint, or multiple severe unresolved deficiencies.
- `medium`: hold-level deficiencies without a denial blocker.
- `low`: approve-ready applications or only immaterial resolved history.

Policy-impact flag:

- Compare current contractor policy to the prior baseline when the policy data includes one. Mark impacted when the current standard creates a material deficiency or review flag that would not have applied under the prior baseline, such as a higher bond minimum or a newly required specialty endorsement.

Always sort application decisions by application ID. Sort per-application code arrays and summary ID arrays exactly as the template requires.

## Restricted Liquor Staff Packages

Use `liquor_applications` to identify the application, license class, and location. Use the location ID to collect settlements, incidents, and site evidence.

Core mappings:

- `standard_obligation_codes`: privilege rows for the license class where `standard_required` is true. Keep these separate from location controls.
- `location_specific_control_codes`: active, non-expired controls from settlement `controls_json`. De-duplicate controls.
- `same_premises_basis_applies`: true when a current active settlement basis is `SAME_PREMISES`; false when only expired/historic same-premises rows exist unless the prompt explicitly asks for history-only treatment.
- `covered_risk_codes`: active settlement basis codes and current risks reasonably covered by active controls. For example, `HOURS` covers after-hours risk, `SECURITY`/`CCTV` cover public-safety or assault risk, `NOISE` covers noise, `PATIO` covers patio-boundary risk, `ID_CHECK` covers minor-sale risk, and `FOOD_SERVICE` covers food-service gaps.
- `verification_gap_codes`: map missing/stale/conflicting site evidence to the matching allowed code. Common mappings include control signage, floor plan, police memo, neighbor notice, site photo, tax clearance, camera/CCTV evidence, food-service evidence, and late-night monitoring.
- Open or referred incidents create verification gaps, monitoring checks, or escalation triggers unless current controls clearly cover them. Dismissed incidents are usually distractors.

Recommended posture:

- `issue_restricted`: current controls cover the meaningful risks and remaining gaps can be handled through standard restricted-license monitoring.
- `request_follow_up`: material verification gaps, open/referred incidents, tax holds, conflicting site evidence, or missing evidence needed before issuance.
- `deny`: unresolved major incidents, tax or board-order conflicts, or risks that cannot be conditioned under the available controls.

First-90-day plan:

- Select only checks supported by the schema's allowed `check_code` values.
- Include checks for active controls, unresolved gaps, and open/referred risks.
- Use early timing for evidence verification and tax/police follow-up; middle or late timing for operational monitoring such as after-hours, noise, patio, food-service, ID-check, or CCTV walkthroughs.
- Follow the template's ordering instruction: sort by code when required, or use operational sequence when required.

Escalation triggers:

- Map each unresolved risk to the nearest allowed trigger code: after-hours service, missing/failed CCTV or footage production, food-service failure, noise/patio breach, reopened tax hold, violent/major incident, minor sale, control-signage failure, or ID-check failure.

## Alcohol Renewal Manual-Review Queues

Use the prompt's release boundary and queue size. Confirm the matching renewal rule in `renewal_rules`.

Matching:

- Include target active licensees in scope.
- Match violations by exact `license_no`.
- Also check predecessor/successor licenses from `successor_to`; include predecessor rows when they refer to the same address/facility and are on or before the boundary.
- Mark `match_confidence` as `exact` when all matched rows use the current license number, `close_address` for address/name matches without exact license identity, and `uncertain` for successor/predecessor matches or mixed evidence.
- Exclude violations after the boundary and list their IDs in the summary field when requested.

Queue fields:

- `matched_violation_ids`: pre-boundary matched violations, sorted by violation date ascending then ID ascending.
- `violation_count`: count of matched pre-boundary violations.
- `most_recent_violation_date`: latest matched pre-boundary violation date.
- `risk_tier`: high for serious/open/pending, unpaid balances, alert-heavy histories, or successor uncertainty; medium for non-serious alerts, unpaid balances, or multiple recent violations; low for limited resolved/warning history.
- `next_step_label`: use `board_review` for serious/open/pending high-risk issues, `manual_fine_check` for unpaid balances, `manual_ALERT_check` for alert flags without higher-priority issues, and `additional_record_check` for uncertain matches or residual records.

Ranking:

1. Rank higher-risk tiers before lower tiers.
2. Within a tier, prioritize serious/open/pending violations, unpaid balances, alert flags, greater matched-violation count, and more recent violation dates.
3. Use license number as the final deterministic tie-breaker.
4. Assign ranks as consecutive integers starting at 1 and include exactly the requested queue size.

Summary fields must reconcile with the queue: queue size, boundary date, excluded post-boundary IDs, close/uncertain match license numbers, and board-review license numbers.

## Final Validation

Before responding:

- Check every top-level key exactly matches the template.
- Check all enum values are allowed by the template variant in front of you.
- Check every required target ID appears exactly once.
- Recompute counts from item-level decisions.
- Sort arrays using the template's specified ordering.
- Use empty arrays instead of omitted arrays when no codes apply.
- Ensure the final response parses as JSON and contains no surrounding text.
