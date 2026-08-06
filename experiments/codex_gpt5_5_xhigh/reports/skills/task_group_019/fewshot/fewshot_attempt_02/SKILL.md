---
name: licensing-review
description: Structured licensing review for contractor application batches, restricted liquor-license staff packages, and alcohol renewal manual-review queues using a task environment API, policy JSON, record endpoints or SQL, and JSON answer templates. Use when Codex must evaluate licensing eligibility, deficiencies, postures, verification gaps, renewal review ranking, or produce schema-conformant JSON from licensing environment records.
---

# Licensing Review

Use this skill to turn licensing environment records into a strict JSON answer. Work from the prompt, the provided answer template, and live records; do not reuse example answer values.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Extract target IDs, target locations, boundary dates, review dates, queue size, required keys, allowed enum values, and ordering rules.
2. Read the environment access file supplied with the task. Use only its base URL and SQL token; do not guess credentials.
3. Fetch relevant records and policies. Prefer targeted SQL slices when SQL is available because GET dumps may omit records needed for a target slice; use GET endpoints as fallback or cross-check.
4. Parse JSON-in-string fields such as policy `details_json` and settlement `controls_json`.
5. Build the answer only from schema-supported fields and enum values. When a deficiency exists but the template lacks that exact code, omit it instead of inventing a key or code.
6. Sort arrays exactly as the template requires, use empty arrays where applicable, and return only JSON.

The bundled helper groups environment records without making determinations:

```bash
python skill/scripts/licensing_context.py --env-file environment_access.md --domain contractor --target-id <id> --target-id <id>
python skill/scripts/licensing_context.py --env-file environment_access.md --domain liquor --application-id <id> --location-id <loc>
python skill/scripts/licensing_context.py --env-file environment_access.md --domain renewal --target-id <license> --boundary-date <YYYY-MM-DD>
```

## Contractor Batches

Use this procedure for State Contractors Licensing Board application batches.

1. Match each application to the current contractor policy by trade and requested class. Read thresholds from `details_json`: minimum bond, insurance, experience years, required endorsement, and serious-violation blocking behavior.
2. For each target application, gather:
   - application row
   - active/current bond rows and cancelled or expired bond rows
   - insurance rows evaluated against the prompt's review date, if given; otherwise use the date implied by the task context
   - prior license history via `prior_license_id`
   - violations by related application and linked prior license
   - correspondence and inspections
3. Apply deficiencies using the template's allowed codes:
   - Bond: no active bond or cancelled-only coverage maps to the template's no-active-bond/cancelled-bond code. Active amount below the policy minimum maps to bond shortfall.
   - Insurance: pending or otherwise not verified maps to pending/not-current. Expired as of the review date maps to expired. Active verified amount below policy minimum maps to shortfall.
   - Endorsement: if the policy requires an endorsement and the application status is missing or pending, map to the template's missing, pending, or generic not-verified code.
   - Experience: years below policy minimum maps to experience shortfall.
   - License history: suspended prior licenses map to active suspension and require board-facing action when supported by the template.
   - Violations: open serious violations or complaints are denial-level blockers when policy says they block. Open minor violations are hold-level only when the template has a matching code.
   - Inspections: unresolved document gaps or failed safety rechecks are hold-level deficiencies only when the template exposes inspection codes.
4. Map required actions from deficiencies using the nearest allowed action code. Examples of action families: file or obtain current bond, increase bond, provide or renew insurance, increase insurance, verify endorsement, document experience, clear suspension, resolve complaint or violation, board review, clear document gap, complete safety recheck.
5. Determination: deny for active suspension or unresolved serious/open blocker; hold for any non-denial deficiency; approve only when no deficiency applies.
6. Risk tier: high for deny/blocker cases, medium for holds, low for approvals unless the template or policy defines a stricter tiering rule.
7. `policy_impacted`: mark true when a current policy standard creates a material deficiency that would not apply under the prior baseline, such as a new endorsement requirement or a higher bond threshold. Do not mark true merely because a file is incomplete under both old and current baselines.
8. Summary counts must equal application-level determinations. High-risk and policy-impacted ID lists must be sorted. For stale or unverified correspondence, include linked correspondence that is agency-unverified or has stale/conflicting/unverified registry content; sort IDs.

## Restricted Liquor Staff Packages

Use this procedure for restricted liquor-license transfer, renewal-with-controls, or location review packages.

1. Identify the target application and location. Load application, liquor policies, settlement history, class privileges, incidents, and site evidence.
2. Standard obligations come from `liquor_privileges` rows for the application's license class where `standard_required` is true. Keep these separate from location-specific controls.
3. Location-specific controls come from active, unexpired settlement controls in `controls_json`. A settlement can also establish the basis for same-premises review even when its controls have expired.
4. `same_premises_basis_applies` is true when current policy says same-premises history matters and the location has same-premises settlement or transfer history relevant to the target application.
5. Covered risk codes should represent settlement bases and incident risks that are materially addressed by current standard obligations or active location controls. Exclude dismissed or unrelated risks unless the policy/template treats the history itself as covered.
6. Verification gaps come from missing, conflicting, stale, or identity-mismatched site evidence; open or referred incidents needing follow-up; unresolved tax holds; and absent evidence for controls or obligations emphasized by the prompt, such as camera coverage, food service, floor plan, signage, police memo, notice, or site photos.
7. Recommended posture:
   - `issue_restricted` when risks are covered and no material verification gap remains.
   - `request_follow_up` when controls are plausible but evidence, incident, or tax gaps remain.
   - `deny` only when the template and records show an unresolved blocker that cannot be cured by follow-up.
8. First-90-day plans should use template-supported check codes. Put immediate evidence or document checks in the first 30 days, operational observations such as late-night or after-hours visits in days 31-60, and follow-up boundary/noise/patio checks in days 61-90 unless the prompt specifies different timing.
9. Escalation triggers should mirror unresolved gaps and major controlled risks: after-hours service, missing or failed camera coverage, footage not produced, missing food service, noise or patio breach, tax hold reopened/uncleared, violent incident, minor sale, control signage failure, or ID-check failure as supported by the template.

## Alcohol Renewal Queues

Use this procedure for renewal-unit manual-review queues.

1. Extract the target license set, release boundary date, and queue size. Load matching `alcohol_licensees`, `alcohol_violations`, renewal rules, and renewal policies.
2. Include only violations known on or before the boundary date in queue decisions. Collect post-boundary violation IDs separately for the summary.
3. Match violations by exact license number first. If a target license has a predecessor/successor link, include predecessor violations only when address, location, or facility context supports the match; mark confidence `close_address` or `uncertain` as appropriate.
4. For each license, compute matched violation count, most recent included violation date, and matched violation IDs sorted by violation date ascending then violation ID ascending.
5. Assign next-step labels using template-supported values:
   - board review for successor/uncertain matches needing judgment, recent serious/open matters, or repeated/high-severity patterns
   - manual fine check when unpaid fines or positive balances are material
   - manual alert check when alert flags drive the hold and no stronger fine or board reason applies
   - additional record check for weaker matches or incomplete data
6. Risk tier is high for board-review cases, serious/open matters, repeated violations, or material unpaid balances; medium for lower-count alert/fine holds; low only when the template allows low-risk queue entries and the record supports it.
7. Rank by next-step priority first (`board_review`, then `manual_fine_check`, then `manual_ALERT_check`, then `additional_record_check`), then by most recent included violation date descending, then violation count descending, then stable license number. Truncate to the requested queue size and renumber ranks from 1 without gaps.
8. Summary fields must reflect the final queue: queue size, boundary date, sorted post-boundary excluded IDs, sorted close/uncertain match license numbers, and sorted board-review license numbers.

## Output Checks

Before finalizing:

- Confirm every required top-level key is present and no extra keys are present.
- Confirm all enum values appear in the answer template.
- Confirm per-item and summary counts agree.
- Confirm all requested target IDs are present exactly once unless the prompt requests a smaller ranked queue.
- Confirm dates are `YYYY-MM-DD`.
- Return only the JSON object, with no markdown or prose.
