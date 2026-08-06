---
name: licensing-review
description: Structured licensing review for state contractor applications, restricted liquor-license staff packages, and alcohol renewal manual-review queues. Use when a task asks Codex to inspect a licensing environment/API, apply policy/rule records, and return schema-conforming JSON decisions, risk codes, review queues, summaries, or staff package fields.
---

# Licensing Review

Use this skill to produce exact JSON for licensing review tasks backed by a running data service.

## Core Workflow

1. Read the prompt and the provided answer template before fetching data. Treat the template as the contract for field names, allowed values, ordering, lengths, and empty-list behavior.
2. Read environment access instructions only from the provided environment file or prompt. Do not invent base URLs, tokens, or endpoints.
3. Fetch all records needed for the target IDs or target location. Prefer public endpoints for small data; use SQL when public endpoints are truncated, paginated, or cannot express the necessary join.
4. Build a working table outside the final answer that shows each target, matched source records, triggered policy facts, selected codes, and summary membership.
5. Emit only the JSON object requested by the template. Do not include citations, markdown, comments, or extra keys.

If SQL is available, use the endpoint token exactly as supplied. Metadata introspection may be blocked, so query known tables by domain:

```text
contractor_applications, contractor_bonds, contractor_insurance,
contractor_license_history, contractor_violations,
contractor_correspondence, contractor_inspections,
policies, liquor_applications, liquor_settlements, liquor_privileges,
liquor_incidents, liquor_site_evidence, alcohol_licensees,
alcohol_violations, renewal_rules
```

Filter SQL to the target IDs, license range, or location. Verify row counts against the prompt and template; missing rows usually mean the query is too narrow or a public endpoint omitted later records.

## Contractor Batch Reviews

Gather contractor policies, applications, bonds, insurance, license history, violations, correspondence, and inspections for every target application.

For each application:

- Select the current contractor policy by `trade` and `requested_class`; parse `details_json` for minimum bond, minimum insurance, minimum experience, required endorsement, and serious-violation blocking rules.
- Use only active current bond rows for bond sufficiency. A cancelled, expired, or missing active bond triggers the applicable no-current-bond code/action from the template; an active bond below the policy minimum triggers the bond-shortfall code/action.
- Use the prompt review date for insurance currency when supplied. Insurance is current only when status is active and expiration is on or after the review date; pending policies require binding verification; active policies below the minimum trigger shortfall.
- Compare `years_experience` to the policy minimum.
- If the policy requires an endorsement, treat missing or pending endorsement status as a deficiency; choose the template's exact missing, pending, or not-verified code.
- Treat a matched prior license with status `suspended` as an active-suspension blocker.
- Treat open serious violations or unresolved serious complaints as denial-level blockers. Open minor or medium violations are hold-level issues if the template offers a matching code.
- For inspections, trigger document-gap or safety-recheck codes only for adverse results such as fail or conditional; ignore pass results unless the prompt or template says otherwise.
- Add stale/unverified correspondence IDs to the summary when the row is tied to a target application and is not agency-verified, is stale, contains a conflict, or is explicitly an unverified applicant note.

Decision and risk defaults:

- `DENY` for active suspension or open serious/unresolved serious violations.
- `HOLD` for any non-denial deficiency.
- `APPROVE` only when no deficiency code or required action applies.
- Use high risk for denial-level blockers, medium risk for holds, and low risk for approvals unless the prompt defines a different risk scale.

For `policy_impacted`, compare the current policy to any legacy or prior-baseline policy. Mark true only when a current policy standard creates a material deficiency or review flag that would not have existed under the prior baseline, such as a newly required endorsement or a higher bond/insurance/experience threshold. Do not mark true for ordinary currentness failures, active suspensions, or open complaints that would block under both baselines.

After all rows, recompute summary counts and sorted summary ID lists from the application decisions. Do not hand-enter summary totals.

## Restricted Liquor Staff Packages

Gather liquor policies, the target application, settlements, privileges, incidents, and site evidence for the target application and location.

Apply these separations carefully:

- `standard_obligation_codes` come only from privilege rows for the application license class where `standard_required` is true.
- `location_specific_control_codes` come from active settlement `controls_json.controls` for the target location.
- `same_premises_basis_applies` is true when same-premises history exists for the location, even if an individual historic control set is expired.
- `covered_risk_codes` should reflect risks addressed by active controls, current settlement basis, relevant non-dismissed incidents, or same-premises history. Exclude dismissed incidents and expired controls unless they explain a still-applicable same-premises basis or active mitigation.

Common control-to-risk reasoning:

- `HOURS` supports after-hours risk coverage and late-night monitoring.
- `SECURITY` and `CCTV` support public-safety, assault, and security-camera control coverage.
- `ID_CHECK` supports minor-sale or sale-to-minor risk coverage.
- `FOOD_SERVICE` supports food-service risk coverage.
- `NOISE` and `PATIO` support noise and patio-boundary risk coverage.

Verification gaps come from missing, stale, conflicting, or unresolved records:

- Conflicting or missing current site evidence maps to the matching template code for control signage, floor plan, police memo, site photos, camera coverage, or food service.
- Open or referred incidents require follow-up; open tax holds remain unresolved until a current clearance record exists.
- Required standard obligations and active controls should have current evidence when the prompt emphasizes them.

Recommended posture:

- Use `issue_restricted` when active controls and evidence support issuance without material follow-up.
- Use `request_follow_up` when verification gaps, open/referred incidents, or current evidence gaps remain but conditions can address them.
- Use `deny` only for blockers that cannot be cured through follow-up or restricted issuance.

Build the first-90-day plan from the actual gaps and active controls. Put document/evidence verification in the first 30 days, late-night or after-hours checks in days 31-60, and follow-up monitoring such as noise or patio checks later unless the template or prompt gives a different order. Escalation triggers should mirror unresolved gaps and field risks.

## Alcohol Renewal Queues

Gather target licensees, violations, and renewal rules. Use the release boundary from the prompt or the matching `renewal_rules` row.

For each target license:

- Include violations known on or before the boundary. Exclude post-boundary rows and report their IDs in the summary if requested.
- Match direct rows by exact license number. Also include predecessor or successor rows when the target license record identifies `successor_to` and the address/facility confirms the same premises.
- Set match confidence to exact for direct license-number matches, close address for predecessor/successor same-premises matches, and uncertain only for weak or conflicting matches.
- Sort `matched_violation_ids` by violation date ascending, then violation ID ascending.
- `violation_count` and `most_recent_violation_date` must be based only on included pre-boundary matches.

Rank the queue in operational priority groups before applying tie-breakers:

1. Board-review cases: serious open or pending matters, successor/predecessor close matches needing board confirmation, or major public-safety patterns near the boundary.
2. Manual fine checks: non-board cases with unpaid balances, large positive fine balances, mixed paid/open fine records, or unpaid-fine/tax-hold themes.
3. Manual alert checks: non-board cases where alert flags drive the manual review and no stronger fine or board priority applies.
4. Additional record checks: weak, uncertain, or incomplete matches.

Within a priority group, sort by most recent included violation date descending, then higher violation count, then license number ascending unless the prompt or rule table defines a different scoring order.

Use high risk for board-review cases, fine-check cases, or serious open/pending violations. Use medium risk for alert-only cases with older or less severe records. Reserve low risk for included records that have only minor resolved issues and no active alert/fine concern.

Summary checks:

- `queue_size` equals the number of queue entries emitted.
- Boundary date exactly matches the prompt or rule used.
- Close or uncertain match license numbers are sorted ascending.
- Board-review license numbers are sorted ascending.
- Post-boundary excluded IDs are sorted by ID unless the template states otherwise.

## Final Validation

Before responding:

- Confirm the final JSON parses.
- Confirm every required top-level key is present and no extra key is present.
- Confirm every enum value appears in the template.
- Confirm all list ordering rules from the template are followed.
- Confirm target count, queue ranks, summary counts, and summary lists are recomputed from the row-level data.
