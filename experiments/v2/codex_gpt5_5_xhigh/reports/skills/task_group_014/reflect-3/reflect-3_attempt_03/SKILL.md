---
name: northstar-payer-ops
description: Turn Northstar payer-operations records into exact JSON answers for UM nurse determinations, pharmacy appeals and assistance intake, claim repricing, peer-to-peer summaries, and finance queue reviews. Use when a task references the Northstar environment, case/appeal/claim/P2P/queue records, policies, rate schedules, documents, criteria, or an answer template.
---

# Northstar Payer Ops

## Workflow

1. Read the prompt, task context, and answer template first.
2. Identify the workflow from the required fields.
3. Query the live Northstar records for the target case or queue and its linked member, plan, policy, criteria, documents, line items, auth, trial, benchmark, appeal, or P2P records.
4. Resolve conflicts by precedence:
   - current clinical records over stale exports
   - payer appeal before manufacturer assistance
   - effective benchmark by payer, plan, CPT, modifier, and date over stale rates
   - new patient-specific P2P evidence over older summaries
   - margin threshold before charge sensitivity
5. Build the JSON exactly to the template. Keep key order, enum values, date format, and numeric precision unchanged.
6. Put controlling record IDs in precedence order and put stale, missing, or conflicting records in `exception_record_ids`.

## UM Nurse Determinations

- Pull case, member, plan, request lines, policy, policy criteria, current clinical documents, document facts, and authorization.
- Use current documents and facts to set criteria results.
- Exclude stale or conflicting documents in `excluded_documents`.
- When approved, copy the authorization number, dates, units, CPTs, and modifier from the auth record.

## Pharmacy Appeals

- Pull case, appeal, policy, criteria, documents, drug trials, and assistance screen.
- Separate documented failures from insufficiently documented failures.
- Keep appeal evidence requirements ahead of assistance information in the packet lists.
- Put only actually missing packet items into the gap list.

## Claim Repricing

- Pull claim, claim lines, benchmarks or rate schedules, case context, and stale-source evidence.
- Match the benchmark on payer, plan type, service domain, CPT, modifier, and effective date.
- Apply allowed amounts per unit, then multiply by claim units for line and total allowed amounts.
- Reject stale schedules explicitly in the audit trail.

## P2P Summaries

- Pull case, P2P event, policy, criteria, current clinical evidence, and authorization.
- Treat not-met required criteria as unresolved when the template asks for unresolved criteria.
- List every missing PET-over-SPECT factor the record supports.
- Compute the appeal deadline from the adverse determination date plus the plan window.

## Finance Queue Reviews

- Use only the named queue rows.
- Compute total cost as variable cost plus allocated fixed cost.
- Compute revenue-to-cost ratio and compare it to the threshold.
- Separate below-threshold segments from charge-sensitive segments.
- Identify the top issue from the most actionable below-threshold row.

## Final Checks

- Use only required keys.
- Do not invent record IDs or add prose.
- Keep lists in the required order.
- Use empty lists only when the template or evidence truly calls for none.
