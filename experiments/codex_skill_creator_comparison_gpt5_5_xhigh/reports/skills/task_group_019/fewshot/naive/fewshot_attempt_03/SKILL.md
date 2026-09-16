---
name: licensing-record-review
description: Solve structured licensing review tasks against a task environment. Use for contractor eligibility batches, restricted liquor-license staff packages, and alcohol renewal manual-review queues that require reading policies/rules and endpoint records, mapping evidence to constrained JSON schemas, ranking or summarizing records, and returning strict JSON only.
---

# Licensing Record Review

Use this skill to solve licensing tasks that provide a prompt, an answer template, and a read-only task environment. Work from the task's current prompt and template only. Do not reuse prior final answers or call judge endpoints.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Extract target IDs, target location IDs, review dates, release boundaries, queue size, required keys, allowed enum values, and ordering rules.
2. Read the task environment instructions for the base URL and any SQL token. Use only allowed read-only endpoints. Prefer `POST /api/sql` with `SELECT` queries when it is available because it returns column names and supports targeted filtering.
3. Fetch policies or renewal rules before case records. Parse any `details_json` or `controls_json` fields as JSON.
4. Build an evidence ledger per target record. Keep source row IDs, statuses, dates, amounts, severities, active flags, and any stale/conflicting notes separate from the final answer.
5. Map evidence to the enum names in the current answer template. When similar templates use different labels, choose the allowed label whose meaning matches the condition.
6. Sort arrays exactly as the template requires. Use empty arrays when nothing applies. Return only the JSON object with the required keys.

Useful SQL pattern:

```bash
curl -s -X POST "$TASK_ENV_BASE_URL/api/sql" \
  -H "Content-Type: application/json" \
  -H "X-Task-Token: $TASK_SQL_TOKEN" \
  --data '{"query":"SELECT * FROM table_name WHERE id_column IN (?, ?) ORDER BY id_column","params":["ID-1","ID-2"],"limit":100}'
```

## Contractor Eligibility Batches

Fetch:

- `/api/policies`
- `/api/contractor/applications`
- `/api/contractor/bonds`
- `/api/contractor/insurance`
- `/api/contractor/license-history`
- `/api/contractor/violations`
- `/api/contractor/correspondence`
- `/api/contractor/inspections`

Match each application to the current contractor policy by trade and requested class. Use policy thresholds for minimum bond, minimum insurance, minimum years experience, required endorsement, and serious open violation blocking. If the prompt gives a review date, use it for current financial coverage; otherwise use the task's stated context and record status/date fields consistently.

Evidence-to-condition rules:

- Bond: require a current active bond. If there is no active bond, use the template's no-active/cancelled bond code. If an active bond amount is below the policy minimum, use the shortfall code.
- Insurance: require current verified coverage through the review date. Pending status maps to pending/not-current. Expiration before the review date maps to expired/not-current. Active coverage below the minimum maps to shortfall.
- Endorsement: if policy requires an endorsement, verified status passes. Missing, pending, or unverified status maps to the matching template code. If the template has only a generic endorsement code, use it for both missing and pending.
- Experience: years below the policy minimum maps to experience shortfall.
- License history: a prior license with suspended/active-suspension status is a denial-level issue and usually requires board review or suspension clearance if those actions exist in the schema.
- Violations: open serious violations or unresolved serious complaints are denial-level issues. Open minor violations are hold-level issues when the schema has a minor/open-violation code. Resolved or dismissed violations normally do not create a deficiency.
- Inspections: use failed or conditional findings only when the template has corresponding codes. `DOC_GAP` maps to document-gap actions; `SAFETY_RECHECK` maps to safety recheck actions. Ignore pass results unless the prompt or schema asks for them.
- Correspondence summary: include correspondence IDs that are not agency verified, are stale, conflict with registry records, or explicitly say applicant-only/unverified. Also include verified rows if their notes or assertion values state stale/conflicting evidence. Sort IDs ascending.

Decision rules:

- `DENY` when any denial-level issue is present, especially active suspension or open serious violation/complaint.
- `HOLD` when non-denial deficiencies remain.
- `APPROVE` only when no deficiency codes remain.
- Risk tier is usually `high` for denial-level issues, `medium` for holds, and `low` for approvals unless the template defines a different scheme.
- `policy_impacted` is true when a current policy standard creates a deficiency or material flag that would not have existed under the prior baseline policy. Compare current thresholds and endorsement requirements to any legacy contractor policy in `/api/policies`.

## Restricted Liquor-License Packages

Fetch:

- `/api/policies`
- `/api/liquor/applications`
- `/api/liquor/settlements`
- `/api/liquor/privileges`
- `/api/liquor/incidents`
- `/api/liquor/site-evidence`

Use the target application to find the license class and location. Pull settlements, incidents, and site evidence by location.

Separate three concepts:

- Standard obligations: privilege rows for the license class where `standard_required` is true.
- Location-specific controls: active, unexpired controls from settlement `controls_json`.
- Same-premises basis: true when settlement or history records show the same premises basis for the target location, even if an older control set is no longer active, unless the prompt says the location changed.

Risk and gap mapping:

- Covered risks should be risks that current standard obligations or active location controls actually address. Common mappings are `ID_CHECK` to minor-sale risks, `HOURS` to after-hours risks, `SECURITY`/`CCTV` to assault or public-safety risks, `FOOD_SERVICE` to food-service risks, and `NOISE`/`PATIO` to noise or patio-boundary risks.
- Do not mark unresolved tax holds, missing evidence, or unsupported major incidents as covered.
- Verification gaps come from missing, stale, or conflicting site evidence; open or referred incidents needing follow-up; unresolved tax holds; missing current control signage; conflicting police memos; and late-night monitoring needs when after-hours risk lacks current supporting evidence.
- Standard obligation codes and location-specific control codes may share the same vocabulary. Keep ordinary license obligations out of the location-control list unless they are also active controls in the settlement record.

Posture and operational plan:

- Use `issue_restricted` when the same-premises basis is supported, material risks are covered, and no material evidence gaps remain.
- Use `request_follow_up` when evidence is missing/conflicting, an incident remains open/referred, a tax hold is unresolved, or active controls require verification.
- Use `deny` only for unmanageable or policy-blocking issues.
- Build `first_90_day_plan` from the remaining gaps and controls. Put identity/evidence checks in `first_30_days`, after-hours or late-night field visits in `days_31_60`, and noise/patio boundary checks in `days_61_90` unless the template or prompt gives another sequence.
- Choose escalation triggers that mirror unresolved risks: after-hours service, unverified controls/signage, missing camera coverage or footage, food service unavailable, minor sale, major incident, unresolved tax hold, noise/patio breach, or ID-check failure.

## Alcohol Renewal Manual-Review Queues

Fetch:

- `/api/alcohol/licensees`
- `/api/alcohol/violations`
- `/api/renewal/rules`

Extract the release boundary and queue size from the prompt and confirm the matching renewal rule. Include only active target licenses in the queue unless the prompt says otherwise.

Matching and exclusion:

- Match violations by exact current `license_no`.
- Also check `successor_to` and old license numbers. Include former-license violations when the former and current records share the same address/facility/location context. Mark these as `close_address` unless the template offers a more exact successor label.
- Use `uncertain` for ambiguous name/address matches that still need record review.
- Exclude all violations after the release boundary. List excluded post-boundary violation IDs in the summary sorted by violation ID.
- For each queue entry, sort `matched_violation_ids` by violation date ascending, then violation ID ascending. Set `most_recent_violation_date` to the latest included violation date.

Queue classification:

- `board_review`: use for serious public-safety or sale-to-minor issues that are open, pending, warning with material balance, successor/close-match serious issues, or any rule/prompt condition requiring board review.
- `manual_fine_check`: use for unpaid-fine themes, positive material fine balances, open/pending fine-related rows, or renewal rules stating unpaid fines require hold when no stronger board-review condition applies.
- `manual_ALERT_check`: use for alert-flagged rows when no stronger board or fine condition applies.
- `additional_record_check`: use for uncertain identity/match issues or incomplete supporting records when no stronger condition applies.

Rank entries by next-step severity first:

1. `board_review`
2. `manual_fine_check`
3. `manual_ALERT_check`
4. `additional_record_check`

Within each group, sort by most recent included violation date descending, then violation count descending, then license number ascending. Assign ranks from 1 with no gaps and stop at the target queue size. Summary lists such as close/uncertain matches and board-review licenses should be sorted by license number ascending.

Risk tiers: use `high` for board-review cases, unresolved serious violations, material unpaid balances, or repeated significant violations; `medium` for alert-only or lesser unresolved issues; `low` only for minimal resolved records with no material alert/fine risk.

## Final JSON Check

Before finalizing:

- Ensure every top-level key required by the template is present and no extra prose, markdown, comments, or citations are included.
- Ensure all enum values appear in the current template.
- Ensure counts match item-level decisions or queue entries.
- Ensure summary ID arrays are sorted as requested.
- Ensure booleans are actual JSON booleans, not strings.
- Validate the JSON syntax locally when possible.
