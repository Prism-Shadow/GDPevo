---
name: licensing-record-review
description: Analyze licensing-environment records for schema-strict licensing decisions. Use when a task asks Codex to review contractor application batches, restricted liquor-license transfers or renewals, or alcohol renewal manual-review queues using policy and case-record endpoints, then return JSON decisions, risk codes, verification gaps, monitoring plans, ranked queues, and summaries.
---

# Licensing Record Review

## Core Workflow

1. Read the prompt, environment-access instructions, and the full answer template before fetching records.
2. Extract target IDs, location IDs, review dates, boundary dates, queue size, required top-level keys, enum values, ordering rules, and summary requirements.
3. Use only the endpoints and SQL access authorized by the environment instructions. Do not browse the web for licensing facts.
4. Fetch all relevant policy and record endpoints for the target family. Parse nested JSON fields such as `details_json` and `controls_json` with a JSON parser.
5. Build target-indexed record maps, then evaluate each target against the current policy baseline and the answer template's allowed codes.
6. Treat missing expected records as evidence when the schema asks about coverage, verification, or review gaps.
7. Return only valid JSON conforming to the template. Use empty arrays for no applicable codes and never add prose, citations, comments, or extra keys.

## Data Handling

- Prefer GET endpoints for canonical records. Use SQL only when the environment instructions allow it and it helps cross-check joins, missing records, or ranking.
- Use the prompt's review date or boundary date when supplied. Otherwise infer the relevant date from policy/rule records or the task's release boundary.
- Apply policies effective on or before the review date. If legacy policy comparison is required, compare only the fields described by the legacy baseline.
- Dedupe code arrays. Sort arrays exactly as the template specifies; if no order is specified, use deterministic order from the business workflow or lexical order.
- Validate summary counts and ID lists from the item-level decisions or queue rows after building the full answer.

## Contractor Eligibility Batches

Fetch contractor applications, bonds, insurance, license history, violations, correspondence, inspections, and contractor-family policies.

For each application:

- Match the current contractor policy by trade and requested class. Compare application experience, bond amount, insurance amount/currentness, required endorsement, and serious-open-violation blocking rules against that policy.
- Current bond means an active bond for the application, with no cancellation that makes it ineffective as of the review date. No active record is a coverage deficiency; an active amount below the policy minimum is a shortfall.
- Current insurance means active, verified coverage that has not expired by the review date and meets the policy minimum. Pending, expired, missing, or under-limit coverage maps to the closest allowed insurance deficiency/action codes in the template.
- Required endorsement statuses usually map as: `verified` passes; `pending` requires verification; `missing` or unverified applicant-only support is a deficiency. Do not require endorsements when policy says none are required.
- Years of experience below the policy minimum create an experience deficiency.
- Suspended prior-license history is a high-risk blocker. Open serious violations or unresolved serious complaints are high-risk blockers when the policy says they block eligibility. Open minor issues generally create a hold, not a denial, unless the template or policy says otherwise.
- Include stale or unverified correspondence IDs in the summary when requested. Treat `verified_by_agency` false, applicant-only notes, conflicting assertions, or stale attachments as stale/unverified; do not let those records clear a deficiency.
- Use inspection findings only when the template allows corresponding codes. Document gaps, failed/conditional safety rechecks, or unverified-site findings create hold-level review items unless paired with a blocker.

Determinations:

- `APPROVE`: no applicable deficiencies remain.
- `HOLD`: curable deficiencies remain, such as missing/current financial proof, shortfalls, pending endorsements, experience documentation, minor open issues, document gaps, or inspection rechecks.
- `DENY`: non-curable or board-blocking items remain, such as active suspension or open serious violation/complaint, when the policy/template supports denial.

Risk tiers:

- `high`: active suspension, open serious violation/complaint, denial posture, or board-review blocker.
- `medium`: hold-level financial, endorsement, experience, correspondence, or inspection deficiencies.
- `low`: approval with no material deficiencies.

Use only deficiency and action codes present in the answer template. Map semantically equivalent schemas carefully, for example:

- Missing or cancelled bond: `bond_cancelled`, `no_active_bond`, `obtain_current_bond`, or `file_active_bond`.
- Bond below minimum: `bond_shortfall`, `increase_bond_amount`, or `increase_bond`.
- Insurance not current, expired, pending, or short: the closest allowed `insurance_*` deficiency and `provide_current_insurance`, `renew_insurance`, `increase_insurance`, or verification action.
- Endorsement missing/pending/not verified: the closest allowed endorsement deficiency and verification/obtain action.
- Open serious complaint/violation or active suspension: the closest blocker code plus `board_review`, `clear_suspension`, or `resolve_complaint`.

Set `policy_impacted` true only when a current policy standard, compared with the stated prior baseline, creates a deficiency or material flag that would not have applied under that prior baseline.

## Restricted Liquor-License Packages

Fetch liquor applications, settlements, privileges, incidents, site evidence, and liquor-family policies.

For the target application and location:

- Use the application record for license class, posture, location, and identity.
- Use privileges for ordinary license obligations. Standard obligations are privilege rows for the application license class where `standard_required` is true.
- Parse settlement `controls_json`. Location-specific controls are active, unexpired controls tied to the target location; expired or inactive controls may inform risk history but are not current controls.
- Set the same-premises basis boolean from current applicable same-premises settlement/control evidence. Distinguish historical same-premises relevance from an active basis that still applies.
- Covered risk codes come from settlement bases, incident risks, and active controls that currently mitigate those risks. Include only risks supported by the record and allowed by the template.
- Verification gaps come from missing, conflicting, stale, or absent current site evidence required by policy, plus unresolved incident follow-up. Examples include signage conflicts, floor-plan conflicts/staleness, police memo conflict, missing site photos, unresolved tax holds, camera/food-service evidence gaps, and late-night monitoring needs.
- Dismissed incidents normally do not create escalation triggers. Open, referred, high-severity, tax-hold, minor-sale, assault, after-hours, noise, patio, or public-safety records may drive risks, follow-up gaps, monitoring checks, or escalation triggers.
- Separate standard obligations from location-specific controls. A code can appear in both only if it is both standard for the license class and active as a location-specific settlement/control.

Recommended posture:

- `issue_restricted`: risks are covered by active controls and no material verification gap blocks issuance.
- `request_follow_up`: controls can support restricted issuance only after evidence, incident, tax, signage, camera, food-service, floor-plan, or memo gaps are cleared.
- `deny`: unresolved major incidents, board-order conflicts, unmitigated same-premises risks, or unresolved tax/public-safety blockers make issuance unsupported.

Build the first-90-day plan from the risks and gaps actually present. Choose checks for CCTV/camera, food service, ID checks, hours/after-hours, noise/patio, control signage, police memo, tax clearance, or incident logs only when supported by records and allowed by the template. Escalation triggers should mirror the most serious unresolved control failures or incident risks.

## Alcohol Renewal Manual-Review Queues

Fetch alcohol licensees, alcohol violations, and renewal rules.

For a target renewal queue:

- Use the prompt or renewal rule for the release boundary. Include only violations known on or before the boundary in queue scoring and matched IDs.
- Exclude post-boundary violations from matching and list their IDs in the summary when requested.
- Start from the target license numbers in the prompt. If the target list size equals the queue size, include those targets exactly; do not add same-address distractors from unrelated task prefixes.
- Prefer exact `license_no` matches. If a target license has `successor_to`, include predecessor violations only when policy allows successor matching and mark confidence as `uncertain` unless the task defines a stronger match. Use close address/name matches only when exact or successor evidence is unavailable or the prompt explicitly asks for close matching; mark those as `close_address` or `uncertain`.
- Sort each row's matched violation IDs by violation date ascending, then violation ID ascending.
- Set `violation_count` from the matched pre-boundary violations and `most_recent_violation_date` from the latest matched pre-boundary date.

Queue ranking should follow explicit prompt or rule instructions first. If no precise scoring formula is given, rank deterministically by:

1. Higher risk tier.
2. More matched pre-boundary violations.
3. More alert-flagged or unpaid-fine violations.
4. More serious and open/pending violations.
5. More recent matched violation date.
6. Stronger confidence (`exact`, then `close_address`, then `uncertain`).
7. License number ascending.

Risk and next-step labels:

- Use `high` for serious unresolved issues, multiple alert/unpaid records, successor uncertainty with serious violations, or board-review conditions.
- Use `medium` for alert or unpaid-fine records without high-risk blockers.
- Use `low` for low-volume, non-alert, resolved/warning-only records.
- Choose `board_review` for serious/high-risk or policy-blocking records, `manual_fine_check` for unpaid-fine-driven holds, `manual_ALERT_check` for alert-driven manual review, and `additional_record_check` for identity uncertainty or weak matches. Use the single best label allowed by the template.

## Final JSON Checks

Before answering:

- Parse the JSON locally or mentally validate all brackets, commas, and string values.
- Confirm every required top-level key and item key is present.
- Confirm every enum value appears in the template's allowed values exactly, including case.
- Confirm required item counts, ranks, ordering, and summary counts match the generated rows.
- Confirm no task-specific training IDs, notes, citations, or explanatory text leak into the response unless the active user task explicitly requests those IDs in the JSON schema.
