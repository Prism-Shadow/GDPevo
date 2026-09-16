---
name: licensing-review-json
description: Produce schema-conforming JSON for licensing-environment review tasks. Use when a prompt asks Codex to analyze task-environment records for contractor application eligibility batches, restricted liquor-license staff packages, or alcohol renewal manual-review queues, especially when outputs must match an answer_template.json exactly.
---

# Licensing Review JSON

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Extract the task family, target identifiers, review date or release boundary, endpoint list, required top-level keys, allowed enum values, ordering rules, and summary fields.
2. Fetch only the endpoint data needed for the target identifiers. Prefer the GET endpoints listed in the prompt. Treat `POST /api/sql` as optional: use it only when the environment provides credentials and it saves work.
3. Parse JSON-encoded fields such as `details_json` and `controls_json` before applying rules.
4. Derive facts from current records, then map them into the exact code vocabulary in the answer template. When two templates use different names for the same concept, choose the allowed name from the current template.
5. Return only the JSON object. Do not include prose, markdown, citations, comments, or keys not present in the template.

Use `scripts/collect_records.py` from this skill directory when endpoint filtering would save time:

```bash
python scripts/collect_records.py --base-url "$TASK_ENV_BASE_URL" --family contractor --ids C-001 C-002
python scripts/collect_records.py --base-url "$TASK_ENV_BASE_URL" --family liquor --ids L-001 --locations LOC-001
python scripts/collect_records.py --base-url "$TASK_ENV_BASE_URL" --family renewal --ids AL-001 AL-002 --boundary "$BOUNDARY_DATE"
```

The helper prints filtered records only; it does not make final determinations.
For renewal tasks, the helper filters exact and declared predecessor license numbers; inspect address-only ambiguities manually before using `uncertain`.

## Contractor Batches

Match each application to the contractor policy whose trade/class title or rule code fits the application. Use `details_json` fields such as `minimum_bond`, `minimum_insurance`, `minimum_years_experience`, `required_endorsement`, and `serious_open_violation_blocks`.

Assess each target application:

- Bond: require an active bond with no effective cancellation and amount at least the policy minimum. Map no active/current bond to `no_active_bond`, `bond_cancelled`, or equivalent. Map low amount to `bond_shortfall`.
- Insurance: require active, current coverage on the prompt's review date when one is given; otherwise use the task's stated current baseline. Map expired/not-current/pending/shortfall to the closest allowed insurance code.
- Endorsement: when policy requires an endorsement, statuses `missing` and `pending` are deficiencies. Use distinct missing/pending codes when available; otherwise use the template's generic not-verified code.
- Experience: years below the policy minimum creates `experience_shortfall` or the template equivalent.
- License history: a suspended prior license is an active-suspension blocker.
- Violations: unresolved serious/open complaint records are denial-level blockers when policy says serious open violations block. Open minor records are hold-level review flags. Ignore resolved or dismissed records as blockers.
- Inspections: failed or conditional `DOC_GAP` creates a document-gap code when available. Failed `SAFETY_RECHECK` creates a safety-recheck code when available. Passing inspections do not create deficiencies.
- Correspondence summary: include target-related correspondence IDs that are unverified by agency (`0`/false) or whose notes indicate stale attachments. Sort IDs lexically.

Determinations:

- `DENY` when there is an active suspension or unresolved serious/open complaint/violation blocker.
- `HOLD` when there are deficiencies but no denial-level blocker.
- `APPROVE` only when no deficiency or required action applies.

Risk tiers:

- `high` for denial-level blockers.
- `medium` for hold-level deficiencies.
- `low` for clean approvals.

Policy impact:

- Mark true when the current 2025 contractor policy creates a material deficiency that would not apply under the legacy baseline, especially required endorsements that legacy policy did not require or shortfalls caused only by the current minimums.
- Mark false when the same blocker would remain under the prior baseline, such as active suspension, expired/no current insurance, or an unresolved serious complaint.

Action mapping:

- Bond shortfall -> increase bond amount/action.
- No active/cancelled bond -> file or obtain current bond.
- Insurance expired/not current -> provide or renew current insurance.
- Insurance pending -> verify binding.
- Insurance shortfall -> increase insurance.
- Endorsement missing/not verified -> obtain or verify endorsement.
- Endorsement pending -> verify pending endorsement.
- Experience shortfall -> submit/document experience evidence.
- Active suspension -> board review or clear suspension.
- Serious open violation/complaint -> resolve serious violation/complaint and board review when allowed.
- Minor open violation -> resolve minor violation review.
- Inspection document gap -> clear document gap.
- Inspection safety recheck -> complete safety recheck.

Sort per the template, usually application IDs ascending and deficiency/action codes alphabetically.

## Restricted Liquor Packages

Use the target application and location. Join:

- `liquor/applications` by application ID and location ID.
- `liquor/privileges` by license class for standard obligations.
- `liquor/settlements` by location ID for same-premises basis, risk basis, and active controls from `controls_json`.
- `liquor/incidents` by location ID for current and historic risks.
- `liquor/site-evidence` by location ID for missing, stale, or conflicting verification materials.

Separate ordinary obligations from location-specific controls:

- `standard_obligation_codes`: privilege rows for the license class where `standard_required` is true, limited to template-allowed codes.
- `location_specific_control_codes`: active settlement controls from `controls_json.controls`, limited to template-allowed codes.

Risk and gap handling:

- `same_premises_basis_applies` is true when any same-premises settlement/history applies to the target location, even if the older control has expired, because the policy says same-premises history matters.
- `covered_risk_codes` should include active settlement basis codes and incident risks that are addressed by current obligations or active controls. Include same-premises only when the template has such a code.
- Site evidence statuses `missing`, `stale`, or `conflicting` create verification gaps using the template's vocabulary. Map evidence codes directly when possible: floor plan, control signage, police memo, tax clearance, site photo, neighbor notice, camera/CCTV, and food service.
- Open or referred incidents normally create follow-up gaps or escalation triggers unless the current controls clearly cover the risk.
- Keep standard obligations out of `location_specific_control_codes` unless they also appear in active settlement controls.

Recommended posture:

- `issue_restricted` when active controls cover the relevant risks and no verification gaps remain.
- `request_follow_up` when controls may support restricted issuance but evidence, open incident, tax, floor-plan, camera, food-service, signage, or monitoring gaps remain.
- `deny` only for an unresolved blocking condition that the prompt/template makes denial-level.

Monitoring and escalation:

- First-30-day checks are appropriate for document/evidence verification: control signage, police memo, tax clearance, camera export, food-service evidence, ID checks, and CCTV/security walkthroughs.
- Days 31-60 is appropriate for after-hours or late-night visits.
- Days 61-90 is appropriate for noise, patio, or boundary behavior checks unless the prompt says earlier.
- Escalation triggers should mirror unresolved risks and gaps using allowed codes: after-hours service, control-signage failure, major/violent incidents, minor sale, CCTV/camera failure, footage not produced, food service unavailable, tax hold, noise/patio breach, and ID-check failure.

## Alcohol Renewal Queues

Use the prompt's target license range/list, release boundary, and queue size. Load renewal rules and use the rule whose `release_boundary` or `use_violations_on_or_before` matches the prompt.

For each target license:

- Match exact violation rows by `license_no`.
- If the current license has `successor_to`, include predecessor rows when they match the predecessor license and/or the same address. Mark confidence `close_address` when predecessor rows are included by address/successor matching; use `exact` when only current-license rows are used; use `uncertain` for ambiguous successor/address matches.
- Include only violations with `violation_date` on or before the boundary date in queue fields.
- Put post-boundary violation IDs in the summary exclusion list, sorted by violation ID.
- Sort matched violation IDs by violation date ascending, then violation ID ascending.

For each queue entry compute:

- `violation_count`: count of included matched violations.
- `most_recent_violation_date`: latest included violation date.
- `risk_tier`: high for unresolved serious records, material unpaid fines, successor/close-address risk, repeated alert-flag records, or multiple significant pre-boundary violations; medium for lower unresolved alert/fine risk; low only for minor resolved history.
- `next_step_label`: use `board_review` for serious unresolved, major, or high-risk successor/same-address issues; `manual_fine_check` for unpaid-fine holds; `manual_ALERT_check` for alert-flag review without a board/fine priority; `additional_record_check` for ambiguous or low-information matches.

Ranking:

1. Rank by next-step severity: `board_review`, then `manual_fine_check`, then `manual_ALERT_check`, then `additional_record_check`.
2. Within a severity group, sort by most recent included violation date descending.
3. Break remaining ties with higher violation count, then license number ascending.
4. Assign contiguous integer ranks starting at 1 and truncate to the requested queue size.

Summary fields must reconcile with queue contents: queue size, boundary date, excluded post-boundary IDs, close/uncertain match license numbers, and board-review license numbers.

## Final Validation

Before final output:

- Ensure every required top-level key exists and no extra keys exist.
- Use empty arrays where no codes apply.
- Verify every enum value appears in the current template.
- Recompute counts from application decisions or queue entries.
- Re-sort arrays and entries exactly as the template requires.
- Emit valid JSON only.
