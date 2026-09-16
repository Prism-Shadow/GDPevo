---
name: credit-office-committee-json
description: Solve shared credit-office committee packet prompts by querying the task-env API, applying the public policy tables and benchmark data, and returning strict JSON that matches the provided answer template. Use this skill whenever a prompt asks for branch regrades, lending allocations, segment posture, watch-list stress, or competing CRE decisions from the shared credit office API, even if it does not explicitly say to use a skill or API.
---

# Credit Office Committee JSON

Use this skill for the staged shared credit-office tasks. The job is always the same at a high level: read the prompt, read the template, pull the right public API records, apply the policy tables, and return JSON only.

## Source Order

1. Treat `input/payloads/answer_template.json` as the exact schema.
2. Use the prompt for the branch, segment, application IDs, review date, and any special threshold language.
3. Query the task environment with the supplied `<TASK_ENV_BASE_URL>`.
4. Read `/api/manifest` and `/api/policies` before you compute anything nontrivial.
5. Use the branch, segment, loan, application, and benchmark endpoints named by the prompt.

Do not infer final values from the example answers. Use them only as shape and workflow guidance.

## What To Fetch

Use the prompt to decide which records matter.

- Branch review: `/api/branches/{branch_id}`, `/api/branches/{branch_id}/metrics`, `/api/branches/{branch_id}/loans`, `/api/branches/{branch_id}/sector-exposures`, `/api/branches/{branch_id}/applications`
- Segment review: `/api/credit-union-segments/{segment_id}`, plus `/api/benchmarks/ncua/q1-2025`
- FDIC comparison: `/api/benchmarks/fdic/q4-2024`
- Always read `/api/manifest` and `/api/policies`

## Policy Facts To Keep In View

Use the policy response as the source of truth. The recurring rules in this environment are:

- Risk rating uses the worst numeric result across the available DSCR, LTV, collateral, and delinquency factors.
- Material downgrade means 2 or more notches.
- DSCR thresholds map roughly to ratings 3, 4, 5, 6, and 7 at 1.50, 1.25, 1.05, 1.00, and below 1.00.
- LTV thresholds map roughly to ratings 3, 4, 5, 6, and 7 at below 0.65, 0.75, 0.85, 1.00, and above 1.00.
- Delinquency minimums matter: 30+ DPD, 60+ DPD, 90+ DPD, and nonaccrual all push ratings worse.
- CRE weighted score bands are `approve_quality` up to 2.0, `conditional` up to 3.0, and `weak` above 3.0.
- CDFI factor-score classes are based on the policy score bands for FICO, debt-to-asset, liquidity months, and LTV.
- Stress formulas are provided by policy and should be applied exactly, not approximated from memory.

If the prompt names a benchmark version, use that benchmark endpoint and compare against the branch or state metric the prompt asks for.

## Archetype Playbooks

### Portfolio Regrade

When the template contains `portfolio_regrade`, `npa_benchmark`, `material_downgrades`, or `top_problem_credit`:

- Re-derive ratings for the loans the prompt targets, usually current rating 3 or worse.
- Aggregate final ratings into `final_rating_exposure_totals`.
- Build migration buckets from current rating to final rating.
- Mark every downgrade of 2 or more notches as material.
- Compute the NPA or noncurrent variance against the named FDIC benchmark as both a ratio gap and a bps gap.
- Pick the worst problem credit using the strongest combination of rating severity, payment status, and exposure.
- Make watch-list action coverage reconcile to the loans assigned to each action.

### Allocation Package

When the template contains `allocation`, `decisions`, `concentration_flags`, or `post_approval_concentrations`:

- Rank applications using the weighted CDFI score and the committee criteria in the prompt.
- Compare each request to branch capacity and to the relevant concentration limits.
- Use only the allowed mitigation and decision enums from the template and policies.
- If a concentration limit would be worsened, prefer a mitigation such as participation, reduced amount, or another allowed exception path.
- Make the post-approval concentration math balance with the approved and conditional amounts.
- Put the strongest credits first in any priority ranking.

### Segment Posture

When the template contains `posture`, `state_metrics`, `peer_comparison`, `controls`, or `escalation_triggers`:

- Compare the state metrics to US and peer-median values from the benchmark set.
- Tie the posture to both external risk and internal capacity.
- Carry forward the checklist gates that the segment endpoint requires.
- Add operating controls that directly address the stated control issue.
- Write escalation triggers as concrete conditions with named owners.
- Keep the final interpretation short and operational.

### Watch-List Stress

When the template contains `watch_list_summary`, `stress_results`, `workout_queue`, or `severe_bucket_counts`:

- Identify the adverse-rated population exactly as the prompt defines it.
- Classify each loan with the policy factor-score bands and keep the class names aligned with the allowed values.
- Apply the +200bp stress formula exactly as given by policy.
- Queue workout actions by severity, payment status, and projected-loss risk.
- Summarize severe bucket counts by rating and payment status so they reconcile to the source records.

### Competing CRE Decision

When the template contains `applications_compared`, `recommended_path`, `stress`, `concentration`, or `conditions`:

- Score both applications with the weighted CDFI score.
- Compare stressed DSCR to the coverage threshold.
- Factor in current CRE exposure, sector exposure, and FDIC benchmark variance.
- Select the stronger credit path and assign the weaker one a disposition and reason codes that fit the template.
- Keep the condition set operational, not decorative.

## Output Discipline

- Return valid JSON only.
- Match the template structure exactly.
- Preserve IDs, enums, and reason-code values from the prompt, policies, and template.
- Use the source precision. Do not round away meaningful differences.
- Use `null` only when the source data is genuinely missing and the template allows it.
- Do not add narrative text, markdown, or explanations outside the JSON.

## Final Check

Before responding, verify that:

- every required section from the template is present,
- every list reconciles to the source records,
- every benchmark comparison uses the named benchmark,
- every decision or rating is supported by a policy rule or a direct record,
- and nothing task-specific leaked into the reusable skill itself.

