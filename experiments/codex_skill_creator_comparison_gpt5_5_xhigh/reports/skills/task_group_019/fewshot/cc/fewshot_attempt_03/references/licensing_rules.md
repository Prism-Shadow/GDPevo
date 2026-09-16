# Licensing Rules

Use these rules after reading the task prompt, answer template, policies, and target records. The template remains authoritative for exact field names, allowed enum values, and ordering.

## Contractor Application Batches

Apply the contractor policy matching the application's trade and requested class. Parse minimum bond, minimum insurance, minimum experience, required endorsement, and serious-violation blocking rules from policy `details_json`. Use the review date in the prompt for current financial coverage; if no review date is supplied, use the task's stated review context rather than today's date.

Map deficiencies from source facts:

- Experience below the policy minimum: use the template's experience shortfall code and corresponding evidence/action code.
- Required endorsement absent, pending, or not agency-verified: use the missing, pending, or not-verified endorsement code available in the template.
- No active bond, cancelled bond, or active bond below the policy minimum: use the template's no-active/cancelled/shortfall bond code and the matching file/increase/obtain action.
- Insurance that is missing, pending, expired before the review date, not current, or below the policy minimum: use the template's pending/expired/not-current/shortfall insurance code and matching action.
- Active suspension in license history: use the active-suspension code and board or clearance action.
- Open serious violation or complaint: use the serious open/unresolved code and board or complaint-resolution action.
- Open minor violation: use the minor open violation code when the template supports it.
- Inspection `DOC_GAP` with a non-pass result: use the inspection/document-gap code when available.
- Inspection `SAFETY_RECHECK` with a failing unresolved result: use the safety-recheck code when available.

Determine posture and risk:

- `DENY` when active suspension or an open serious violation/complaint blocks issuance.
- `HOLD` when any curable deficiency remains.
- `APPROVE` only when no deficiencies remain.
- Use high risk for deny/blocking facts, medium risk for holds, and low risk for clean approvals unless the template or policy states otherwise.

Set `policy_impacted` when the current policy creates a material deficiency that would not have existed under the legacy baseline, such as a new endorsement requirement or higher bond, insurance, or experience threshold. Do not mark it solely for facts independent of the policy change, such as an active suspension or open serious complaint.

For correspondence summaries, include IDs for records that are stale, not agency-verified, explicitly conflict with registry data, or have been superseded without a newer verified source. Sort the IDs as the template requires.

## Restricted Liquor-License Packages

Start from the target application to get `location_id` and `license_class`. Join:

- policies for liquor control requirements,
- settlements by `location_id`, parsing `controls_json`,
- privileges filtered by `license_class`,
- incidents by `location_id`,
- site evidence by `location_id`.

Separate ordinary obligations from location-specific controls:

- `standard_obligation_codes` come from privilege rows for the license class where `standard_required` is true.
- `location_specific_control_codes` come from active, current settlement controls for the location.
- `same_premises_basis_applies` is true when same-premises history exists for the location and policy says that history matters, even if the older control itself is expired.

Map controls and risks:

- `HOURS` covers after-hours risk.
- `SECURITY` and `CCTV` cover public-safety, assault, camera, and security-control risks.
- `ID_CHECK` covers sale-to-minor, minor-sale, and ID-check risks.
- `FOOD_SERVICE` covers food-service-gap risk.
- `NOISE` covers noise risk.
- `PATIO` covers patio-boundary risk.
- Settlement basis codes such as same-premises may be covered risks when the current package relies on that basis.

Use verification gaps for unresolved or conflicting evidence rather than treating them as covered:

- Missing or conflicting control signage: control-signage gap codes.
- Conflicting or stale floor plans: floor-plan gap codes.
- Conflicting police memo or unresolved identity note: police-memo gap code.
- Open, referred, or follow-up incidents: open-incident or incident-follow-up gap codes.
- Open tax hold or missing tax clearance: tax gap code.
- Missing current evidence for expected camera or food-service controls: camera or food-service evidence gap codes.
- Late-night or after-hours risk without enough current evidence: late-night monitoring gap code.

Recommended posture:

- `issue_restricted` when current controls and standard obligations cover the risks and no material verification gap remains.
- `request_follow_up` when evidence is missing, stale, conflicting, or an incident/tax item needs confirmation.
- `deny` only for unresolved disqualifying facts that cannot be cured through follow-up under the supplied policy and schema.

Build the first-90-day plan from gaps and active controls. Evidence checks normally happen in the first 30 days, field visits for after-hours/security concerns in days 31-60, and trend or boundary checks in days 61-90 unless the template mandates lexical sorting. Common mappings:

- signage gap: control-signage review or recheck,
- police memo gap: police-memo follow-up,
- CCTV/security control or camera gap: camera export test or security/CCTV walkthrough,
- food-service gap: food-service check,
- after-hours or late-night risk: after-hours or late-night visit,
- ID/minor-sale risk: ID-check observation,
- noise or patio controls: noise/patio boundary check,
- tax gap: tax clearance review.

Escalation triggers should mirror the unresolved risks and control failures: after-hours service, missing or unproduced camera footage, food service not available, noise or patio breach, tax hold reopened/uncleared, unreported major incident, minor sale, ID-check failure, or security/CCTV control failure.

## Alcohol Renewal Manual-Review Queues

Use the prompt's release boundary and target queue size. Fetch the matching renewal rule and exclude violations dated after the boundary; list excluded post-boundary violation IDs in the summary.

For each target license:

- Fetch the licensee row and exact-license violations.
- If `successor_to` is present, fetch predecessor-license violations too. Include them when address/name context supports the successor match; set `match_confidence` to `close_address` or `uncertain` instead of `exact`.
- Count only matched pre-boundary violations used for the queue.
- Sort `matched_violation_ids` by violation date ascending, then violation ID ascending.
- `most_recent_violation_date` is the latest matched pre-boundary violation date.

Manual-review signals include alert flags, unpaid fine balances, open or pending dispositions, serious severity, successor/predecessor matches, and repeated risk themes such as sale to minor, assault, tax hold, after hours, or noise.

Assign `next_step_label` by strongest applicable signal:

1. `board_review` for successor serious/open matches, major or serious unresolved incidents, repeated high-concern themes near the boundary, or combined alert and unpaid-fine patterns that require board attention.
2. `manual_fine_check` for unpaid balances, tax holds, or unpaid-fine themes that do not rise to board review.
3. `manual_ALERT_check` for alert flags without a stronger board or fine priority.
4. `additional_record_check` for uncertain matches or incomplete identity/address evidence without a stronger signal.

Risk tier should track severity: high for board-review items, successor serious matches, repeated violations with serious/unpaid/open signals, or multiple strong manual-review signals; medium for material but less severe manual-review signals; low only when the template requires a queue entry despite weak signals.

Rank the queue by next-step priority, then most recent matched violation date descending, then violation count descending, then license number ascending. Assign ranks consecutively from 1 through the requested queue size and keep summary lists sorted as the template specifies.
