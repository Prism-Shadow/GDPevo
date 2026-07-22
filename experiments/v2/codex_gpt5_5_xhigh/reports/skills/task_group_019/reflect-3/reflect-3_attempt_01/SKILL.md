---
name: licensing-review
description: Structured licensing review for contractor eligibility batches, restricted liquor-license staff packages, and alcohol renewal manual-review queues. Use when Codex must inspect licensing records, policies, violations, evidence, financial coverage, settlements, or renewal boundaries and return a strict JSON decision package matching a provided schema.
---

# Licensing Review

## Core Workflow

1. Read the prompt and answer template before querying records.
2. Extract the target IDs, location IDs, review date or release boundary, required output keys, allowed enum codes, count requirements, and ordering rules.
3. Read current policy records and parse embedded JSON policy details. Map policies by family and by the task-specific class, trade, license class, or renewal boundary.
4. Pull only records relevant to the target IDs, predecessor IDs, and target locations. If a public record source appears incomplete or paginated and a query service is available in the environment, use concrete filtered queries to verify completeness.
5. Build the answer from the schema outward. Prefer empty arrays over omitted keys, sort arrays exactly as instructed, and keep summary counts and ID lists consistent with item-level decisions.
6. Do not add prose, citations, markdown, or extra fields to the final answer unless the template explicitly allows them.

## Contractor Eligibility

For each application, join application, bond, insurance, prior license, violation, correspondence, inspection, and policy records.

Use the current policy for the application trade/class to evaluate:

- active bond status and minimum bond amount
- insurance status, amount, and expiration against the prompt's review date when one is supplied
- required endorsement status
- minimum experience years
- active suspension history
- unresolved serious/open complaints or violations
- inspection or correspondence issues only when the output schema includes matching codes

Map determinations consistently:

- `APPROVE`: no unresolved deficiencies under the schema.
- `HOLD`: remediable missing, pending, stale, shortfall, expired, or documentation issues.
- `DENY`: active suspension or unresolved serious/open complaint or violation when the schema treats those as blocking.

Use high risk for denial-level issues, active suspensions, or unresolved serious matters. Use medium risk for financial shortfalls, non-current financial coverage, missing/pending endorsements, experience shortfalls, and unresolved document gaps. Use low risk only when no meaningful deficiency remains.

For action codes, include the concrete remediation for every deficiency. If the schema has a generic board-review action, include it for denial-level suspension or serious-complaint cases in addition to the concrete clearance/resolution action.

Set policy-impact flags narrowly. Mark them when a current policy standard materially creates the deficiency compared with a legacy baseline, such as a newly required specialty endorsement or a raised bond threshold. Do not mark ordinary stale records, suspensions, open complaints, or expired documents as policy-impact solely because they are reviewed under current policy.

For stale or unverified correspondence summaries, prefer explicit fields such as unverified flags, stale dates, or conflict values. Do not treat a free-text note as controlling when the structured verification field says otherwise unless the prompt directs that note text should override the field.

## Restricted Liquor Packages

Separate three concepts:

- Standard obligations: ordinary required obligations for the application license class, usually indicated by the privilege table's standard-required flag.
- Location-specific controls: current active controls from active settlements or orders at the target location.
- Verification gaps: current missing, conflicting, stale, unresolved, or identity-mismatch evidence and incidents.

Evaluate same-premises basis from target-location history. If policy says same-premises history matters, a same-premises settlement or order at the target location can keep the basis applicable even when older controls have expired; active same-premises controls are a stronger basis.

Recommended posture:

- `issue_restricted`: current controls and current evidence are sufficient, with no material unresolved incident, tax, or evidence gap.
- `request_follow_up`: controls may support a restricted posture, but current evidence, open incidents, tax holds, identity notes, floor plans, signage, camera, food-service, or monitoring gaps need staff follow-up.
- `deny`: the record contains an unremediable or currently blocking issue under the prompt and policy.

For covered-risk codes, list risks actually addressed by current active controls. Keep risks that are only historical, expired, missing, or unresolved in verification gaps, monitoring checks, or escalation triggers instead of calling them covered. Include standard-obligation risks only when the schema or prompt treats standard obligations as risk coverage rather than merely ordinary obligations.

Use verification gaps for evidence that is current and missing/conflicting, open incident follow-up, unresolved tax holds, floor-plan conflicts, police memo identity conflicts, or prompt-emphasized missing evidence such as camera or food-service proof. Do not infer every possible missing evidence type merely because no row exists.

Build the first-90-day plan from active controls and unresolved gaps. Put high-risk follow-up such as tax clearance, camera proof, food-service proof, current signage, police memo follow-up, or late-night monitoring early. Include later checks for ongoing noise, patio, incident-log, security, CCTV, or ID-check monitoring when those controls or risks are active in the record.

Escalation triggers should mirror unresolved gaps and active controls: service after hours, missing or unavailable camera coverage, unavailable food service, uncleared tax holds, serious unreported incidents, noise or patio breaches, boundary failures, or ID-check failures when those risks are present.

## Renewal Manual-Review Queues

Use the prompt's release boundary and target queue size exactly.

For each target license:

- Include violations known on or before the boundary.
- Exclude later rows from the queue and list their IDs in the summary when the schema asks for excluded post-boundary IDs.
- Prefer exact license-number matches.
- Use predecessor/successor records only when the licensee record links them; mark those matches uncertain.
- Use close-address matches only when the task or policy calls for address-based matching and exact/predecessor matching is insufficient.

When rules specify manual-review triggers, distinguish the queue basis clearly:

- alert-flagged rows require manual alert review
- unpaid balances require manual fine review
- serious open or pending matters can require board review
- weak, successor, or address-only matches can require additional record checks

Rank by the prompt or rule text. If no explicit sort is given, use a defensible stable order: highest review severity first, then matched violation count, then most recent matched violation date, then license number. Keep `rank`, `violation_count`, `most_recent_violation_date`, and `matched_violation_ids` internally consistent.
