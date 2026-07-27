---
name: licensing-review
description: Use for structured licensing review tasks involving contractor applications, restricted liquor-license packages, or alcohol renewal queues where Codex must gather task-provided records, apply policy/rule thresholds, and return exact JSON matching a supplied template.
---

# Licensing Review

## Core Workflow

1. Read the prompt, output template, and task-provided data access instructions before querying records.
2. Treat the output template as authoritative: use exactly its keys, allowed enum values, ordering rules, empty-array conventions, date format, and summary fields.
3. Gather records with structured filters. If a public data response appears capped or incomplete, use the task-provided structured query mechanism when available and filter by the target identifiers.
4. Normalize parsed JSON fields inside records, especially policy `details_json` and settlement/control payloads.
5. Build an evidence table by target id before drafting JSON. Keep raw facts separate from derived decisions.
6. Reconcile summaries from item-level decisions after all item rows are final.
7. Return only the requested JSON. Do not include citations, rationale prose, markdown, or extra keys unless the template explicitly permits them.

## Contractor Application Reviews

Map each application to the matching current policy by trade and requested class. Use policy thresholds for minimum bond, minimum insurance, years of experience, required endorsement, and serious open violation blocking.

Evaluate each target application:

- Bond: use current active bonds only. No active bond and active bond shortfall are separate conditions when the schema distinguishes them. Cancelled-only evidence is not current coverage.
- Insurance: require active status, sufficient amount, and expiration on or after the task's review date. Use the schema's distinct codes for pending/not-current, expired, and shortfall.
- Experience: compare stated years to the policy minimum. Do not treat correspondence as curing a shortfall unless it is agency-verified and clearly updates the years.
- Endorsement: missing or pending/non-verified status is a deficiency when the matched policy requires an endorsement.
- Prior license history: suspended status is an active-suspension blocker; expired status alone is not a suspension.
- Violations: unresolved serious complaints/violations are high-risk blockers. Open minor violations usually hold for review, not denial.
- Inspections and correspondence: only emit inspection deficiency codes if the template has them. Summary stale/unverified correspondence should include records with an unverified agency flag, stale attachments, applicant-only notes, conflicting registry statements, or unverified applicant notes.

Determination guidance:

- `APPROVE` only when no template-relevant deficiency remains.
- `HOLD` for curable items such as missing proof, shortfalls, pending endorsements, and minor open issues.
- `DENY` when the schema and policy indicate blocking conditions, especially active suspension or unresolved serious violations.
- Mark high risk for denial blockers; medium for curable multi-part holds; low for clean approvals.

Policy-impact guidance:

- Compare the current policy to any supplied legacy/prior baseline.
- Mark policy impact only when the current standard creates a deficiency that would not exist under that baseline, such as a current bond minimum exceeding the legacy-reduced minimum or a specialty endorsement newly required by current policy.
- Do not mark routine pending proof, expired documents, active suspensions, unresolved complaints, or non-specialty endorsement/experience items as policy-impacted unless the prior baseline explicitly changes that factor.

Map each deficiency to the closest allowed required-action enum in the template. Sort codes and actions exactly as required.

## Restricted Liquor-License Packages

Separate ordinary class obligations from location-specific controls:

- Ordinary obligations come from the license-class privilege/control table entries marked as standard required.
- Location-specific controls come only from active, unexpired settlement/control records for the target location.
- Expired or inactive settlement history can explain risk context, but should not be treated as a current control unless the prompt or policy explicitly carries it forward.

Classify same-premises basis from current applicable settlement/control history. An active same-premises basis generally applies; inactive or expired same-premises history is context unless the task says history alone remains operative.

Covered risks should be risks actually addressed by active current controls or ordinary required controls. Do not list open incidents, missing evidence, or expired controls as covered risks. Put those in verification gaps or monitoring instead.

Common verification gaps:

- Missing or conflicting control signage, floor plans, site photos, food-service evidence, camera/CCTV evidence, or police memoranda.
- Open incident follow-up, unresolved tax hold, identity-note conflicts, and late-night monitoring needs.
- Use the exact enum names and casing from the template; the same concept may have different names across tasks.

Posture guidance:

- Use restricted issuance when active controls cover the relevant risks and no blocking verification gap remains.
- Request follow-up when evidence needed to verify current controls is missing, conflicting, stale, or when open incidents/tax holds need staff confirmation.
- Deny only for non-curable or policy-blocking conditions.

First-90-day plans should be traceable to either an active control or a verification gap. Put current-evidence checks in the first 30 days; operational observations and incident-log reviews can follow in later windows if the template permits. Avoid generic checks that are not connected to a risk, control, or gap. Escalation triggers should mirror the unresolved gaps and active-control failures.

## Alcohol Renewal Queues

Use the release boundary exactly:

- Include matched violations known on or before the boundary.
- Exclude post-boundary rows from matched counts and matched ids, but list their ids in the required exclusion summary.
- Sort matched violation ids by violation date ascending, then id ascending unless the template says otherwise.

Matching and confidence:

- Prefer exact current license-number matches.
- If the license has a predecessor/successor relationship, include legacy matches only when the task policy says successor matching is allowed or required, and mark confidence as uncertain or the closest allowed non-exact value.
- Put close or uncertain license numbers in the required summary.

Ranking should follow the task's renewal rules. In absence of a supplied numeric formula, rank by manual-review severity using these tie-breakers in order:

1. Blocking/high-risk conditions such as serious open or pending violations, unresolved holds, or successor uncertainty.
2. Manual-review triggers such as alert flags and positive fine balances.
3. Matched violation count.
4. Most recent matched violation date.
5. Stable license number as a final tie-breaker.

Choose `next_step_label` from the dominant review need: board review for serious/high-risk blockers, manual fine check for positive balances, manual alert check for alert-only cases, and additional record check for close or uncertain matches.

## Final Validation

Before returning JSON, verify:

- Target ids and counts match the prompt.
- Item ordering and summary id ordering follow the template.
- Every enum value is allowed by the template.
- Empty lists are used instead of omitted list fields.
- Summary counts and id lists agree with item-level decisions.
- Date comparisons use the review or boundary date from the prompt, not the system date.
