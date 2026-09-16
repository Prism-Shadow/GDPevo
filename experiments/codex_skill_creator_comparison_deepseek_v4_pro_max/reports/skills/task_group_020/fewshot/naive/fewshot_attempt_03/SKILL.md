---
name: deal-workbench-analyzer
description: Analyze M&A deal records from a running deal workbench. Gather terms, playbooks, consents, contracts, employees, regulatory data, risk estimates, benchmarks, and diligence findings, then produce structured issue registers, closing-readiness assessments, escalation packages, and transition reviews.
---

When the task calls for analyzing deal records from a running M&A deal workbench
at `<TASK_ENV_BASE_URL>`, follow this skill.

## High-Level Workflow

1. Read the prompt's `answer_template.json` payload first. It defines the
   required output shape, allowed enumerations, stable identifiers, and units.
   Every field in the template must be populated; do not invent new top-level
   keys or omit required fields.

2. Gather all deal records from the workbench. Do not assume records from
   similarly named projects apply. Use only records keyed to the prompt's
   `deal_id`.

3. Compare current draft terms against the applicable playbook or policy.
   Treat a missing required term as an issue. Treat a term whose draft value
   exceeds or falls below the playbook threshold as an issue. A term that
   matches the playbook is in-policy and may be excluded from escalation lists
   unless the template explicitly requires it.

4. Compute all monetary amounts from the deal's headline purchase price (or
   equity value, whichever the template specifies) unless a source explicitly
   states a different basis. Round currency to integer dollars. Round percent
   points to the decimal precision specified in the template. Round month
   values to integers.

5. Classify every issue with the template's enums for status, risk rating,
   and recommended action. Sort issues in the order the template requires.

6. Construct the final JSON answer that exactly matches the template's schema.
   Do not include narrative outside the JSON.

## Gathering Records

The workbench is at `<TASK_ENV_BASE_URL>`. Every endpoint is a GET unless
noted. Start with the deal record and the playbook, then pull supporting
records based on the task scope.

Core endpoints (always hit these first):

- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>` -- deal overview, headline value, parties
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/terms` -- current draft terms with term IDs
- The playbook: either `<TASK_ENV_BASE_URL>/api/playbooks/<playbook_id>/rules` for
  a named playbook ID from the prompt, or
  `<TASK_ENV_BASE_URL>/api/policies/<policy_id>/thresholds` for a committee
  policy ID

Supporting endpoints (pull only what the task scope needs):

- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/benchmarks` -- market benchmarks
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/risk-estimates` -- risk estimates
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/consents` -- third-party consents
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/employees` -- employee records
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/cap-table` -- holder allocation data
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/material-contracts` -- material contracts
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/regulatory` -- HSR and other regulatory
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/diligence-findings` -- diligence findings
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/documents` -- deal documents
- `<TASK_ENV_BASE_URL>/api/deals/<deal_id>/notes` -- negotiation or deal-team notes

Cross-entity lookups:

- `<TASK_ENV_BASE_URL>/api/search` -- search for records across types
- `POST <TASK_ENV_BASE_URL>/api/query` with token `deal-workbench-readonly` --
  read-only SQL for cross-table joins; send a JSON body with `{"sql": "..."}`

Endpoint discovery (if needed):

- `<TASK_ENV_BASE_URL>/api/deals` -- list all deals
- `<TASK_ENV_BASE_URL>/api/playbooks` -- list all playbooks
- `<TASK_ENV_BASE_URL>/api/policies` -- list all policies

## Comparing Terms Against Playbooks or Policies

### Playbook-Based Review (Seller or Buyer APA/SPA)

A playbook rule has a `term_id`, a `rule_type`, a `preferred_value`, and a
`fallback_value`. Rules may be numeric (percent, amount, months) or structural
(presence/absence of a clause, a requirement for specific language).

When a term is present in the draft:

- If the draft value exceeds the playbook's fallback in the direction that
  harms the client, classify as `draft_exceeds_playbook`.
- If the draft value is below the playbook's fallback in the direction that
  harms the client, classify as `draft_below_playbook`.
- If the draft matches the playbook preferred or fallback, classify as
  `in_policy`.

When a term is absent from the draft but the playbook requires it:

- Classify as `missing_required_term`.
- Include an empty `source_term_ids` array.
- The `recommended_action` is `add`.

### Policy-Based Escalation (Committee Review)

A policy threshold is a hard limit. Terms that exceed the threshold are
out-of-policy and must be escalated. In-policy terms (including distractors
that are technically negotiable but not out of policy) must be excluded from
the escalation list and listed instead in an `excluded_in_policy_terms` or
equivalent field.

### Risk Rating

Rate each issue based on the magnitude of the deviation and the deal context:

- `HIGH`: closing certainty at stake, large dollar gap, or missing structural
  protection with material downstream impact.
- `MEDIUM`: meaningful exposure but mitigatable, moderate dollar gap.
- `LOW`: minor deviation, likely negotiable, small or unquantified impact.

### Recommended Action

- `add` for missing required terms.
- `revise` for draft terms that exceed or fall below the playbook in a harmful
  direction.
- `delete` for terms the playbook prohibits (e.g., buyer financing condition
  in a seller playbook).
- `accept` for terms that are in-policy or close enough.
- `escalate` when a business decision is needed beyond counsel's remit.
- `approve` / `approve_with_conditions` / `reject` for committee-level
  decisions.

## Computing Dollar Amounts

Use the headline purchase price (or equity value) from the deal record as the
base unless the term or benchmark explicitly states a different basis.

```
draft_amount_dollars = round(draft_percent / 100 * headline_value)
fallback_amount_dollars = round(fallback_percent / 100 * headline_value)
delta_to_fallback_dollars = abs(draft_amount - fallback_amount)  # when harmful
shortfall_dollars = required_amount - draft_amount  # or just required_amount if absent
```

When the draft lacks a percent but has a dollar amount, use the explicit
dollar amount and derive the percent: `draft_percent = round(draft_amount /
headline_value * 100, decimal_places)`.

For per-employee figures (PTO liability, service credit), sum across the
relevant employee records rather than multiplying by a per-head estimate.

Round to integer dollars and percent points to the decimal precision stated
in the template (typically two decimal places for percent points).

## Identifying Closing Blockers

A closing blocker is anything that must be satisfied before the deal can
close. Scan these record types:

- **Consents**: required consents are those with `condition_type` indicating
  they are a closing condition (not notice-only or post-closing).
- **Regulatory**: HSR clearance, industry-specific approvals.
- **Material contracts**: contracts requiring third-party consent for
  assignment or change of control.

Distinguish blockers (must resolve before closing) from tradeables (can be
negotiated or deferred) and non-blocking notices (information-only).

## Computing Exposure

Exposure is the dollar amount at risk if an issue is not resolved.

- For closing certainty items (reverse break fees, consent gaps): use the
  purchase price or the revenue at risk from the relevant contract/consent.
- For indemnity items: use the gap between draft cap and playbook cap times
  the headline value, plus any special indemnity or privacy finding amounts.
- For employee items: use the stated PTO liability or stranded cost gap.
- For transition items: use the stranded cost gap and the disruption high
  estimate.

When the template asks for low/high ranges, use the low and high values from
the risk estimate records. When only one source exists, derive low/high from
the stated amounts (e.g., low = direct gap, high = gap plus consequential
exposure if stated).

## Priority Ordering

Sort issues from highest to lowest negotiation priority. Use these heuristics:

1. Closing certainty issues (financing conditions, consent gaps, regulatory
   conditions, reverse break fees) generally rank highest.
2. Structural protections (indemnity cap, escrow, survival, restrictive
   covenants) come next.
3. Operational transition issues (TSA, employee continuity, IP transition).
4. Administrative/tax items (Section 1060, transfer tax, governing law) come
   last, unless the deal context elevates them.

When the template provides explicit `priority_order` fields, fill them based
on the above heuristics adjusted for the specific deal's risk-weighted
exposure.

## Source IDs and References

Always use the exact `term_id`, `consent_id`, `contract_id`, `employee_id`,
`risk_estimate_id`, `finding_id`, and other stable identifiers as returned by
the workbench API. Never fabricate or guess IDs.

When the template provides stable IDs (e.g., `possible_issue_ids`), use only
those and do not invent new ones.

For `source_term_ids`, cite the exact draft term IDs from
`/api/deals/<deal_id>/terms` that correspond to the issue. For missing terms,
use an empty array.

## Output

Return only valid JSON. The JSON must validate against the template structure.
No explanatory prose, markdown wrappers, or code fences may appear outside the
JSON object. Every field declared as required in the template must be present.

## Common Task Patterns

### Seller APA Issue Register

Compare buyer draft against seller playbook. Cover financing condition,
reverse break fee, escrow, indemnity cap/basket, survival, restrictive
covenants, employee continuity, TSA, tax allocation, governing law, consent
conditions, materiality scrape, HSR covenant. Summarize with issue count, risk
counts, total quantified exposure, consent count, employee totals.

### Buyer SPA Closing & Economics Package

Pull cap table for holder-level consideration allocation. Compare terms
against buyer playbook for indemnity cap, survival, escrow, NWC, materiality
scrape. Check consents, material contracts, and regulatory for closing
conditions and blockers. Pull employees for service credit and PTO. Pull
diligence findings for NWC collar. Compute closing readiness.

### Committee Escalation Package

Review against policy thresholds. Escalate only out-of-policy terms. Exclude
in-policy distractors explicitly. Provide quantified delta against policy,
benchmark comparisons, exposure, and required conditions for each escalated
term. Include aggregate summary with risk counts, exposure totals, and overall
recommendation.

### Carveout APA Transition Review

Focus on separation terms: IP/domain transition, TSA scope/duration/fees,
Section 1060 allocation, transfer tax split, employee continuity for
transferred groups, closing deadline with regulatory extensions, governing
law/forum. Produce transition issues paired with required redline instructions
that provide must-have terms for each revision or addition.

### Buyer SPA Deviation Matrix

Compare draft against buyer playbook across cap/basket, survival/knowledge,
materiality scrape, escrow/holdback/release, consent conditions, HSR, material
contracts. Include closing blocker analysis with blocker IDs, types, amounts
at risk, and required actions. Summarize with risk totals covering position
counts, exposure aggregates, and highest-modeled-exposure category.
