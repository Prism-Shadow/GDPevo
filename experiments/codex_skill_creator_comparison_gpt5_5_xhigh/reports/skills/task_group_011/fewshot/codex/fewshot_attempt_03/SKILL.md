---
name: credit-office-api-pack
description: Solve committee-style JSON cases from the public credit office API, including branch loan regrades, lending allocations, credit-union segment posture reviews, watch-list stress packets, and competing CRE decisions. Use when a prompt names a branch, segment, applications, benchmark tables, and a strict JSON template.
---

# Credit Office API Pack

## Use This Skill

1. Read the prompt and `input/payloads/answer_template.json` first.
2. Fetch the live case data from `<TASK_ENV_BASE_URL>`.
3. Use [scripts/case_pack.py](scripts/case_pack.py) when the case spans multiple endpoints.
4. Read [references/case_workflow.md](references/case_workflow.md) for the shared formulas and ordering rules.
5. Return JSON only, with the template's keys, enums, precision, and sort order preserved exactly.

## Branch Regrade Cases

- Pull `manifest`, `policies`, branch details, metrics, loans, sector exposures, applications, and the FDIC benchmark.
- Re-rate the target loan population with the policy thresholds.
- Use the worst numeric rating from the available DSCR, LTV, and delinquency factors.
- Treat loans with `current_rating >= 3` as the regrade set when the prompt says "3 or worse".
- Build `material_downgrades` from loans whose notch drop meets the policy threshold.
- Build `watch_list_action_coverage` from the follow-up population after regrade.
- Compute NPA variance from `nonperforming_loans / total_loans_outstanding` versus the FDIC benchmark metric.

## Allocation Cases

- Sort `decisions` by `application_id`.
- Use only the allowed decision and condition enums.
- Set `gross_approved_amount` from approved and conditionally approved applications.
- Set `committed_capacity_amount` from the bank-funded share after participation or guaranty mitigation.
- Compute post-approval sector concentration with the approved amount added into the matching sector exposure.
- Flag only the approvals that need sector mitigation.

## Segment Posture Cases

- Copy the NCUA state row into `state_metrics`.
- Compare the segment's target state to the US row and to the median of the peer-state rows.
- Use all checklist gates from the segment, then add operating controls that match the internal context.
- Choose escalation triggers from the allowed trigger and owner enums only.

## Watch-List Stress Cases

- Use loans with `current_rating >= 6`.
- Sum the policy factor scores for every available objective factor.
- Classify the factor score with the CDFI bands from policy.
- Use the +200bp stress formula from policy for DSCR-bearing loans.
- Sort workout items by exposure descending, then loan_id ascending.
- Escalate the action as severity increases, with nonaccrual or projected-loss credits moving deepest.

## Competing CRE Cases

- Compare only the named applications.
- Use the policy weights to derive the weighted CRE score; lower is better.
- Classify the score with the policy bands before assigning the decision.
- Use the policy dual-stress formula for the DSCR test.
- Compute CRE concentration from `loan_type == "CRE"` balances.
- Use the selected application's requested amount when updating post-approval concentration.
- Explain the unselected application with sorted allowed reason codes.
