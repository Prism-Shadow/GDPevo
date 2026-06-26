# Credit Office Committee JSON Skill

Use this skill for Credit Office tasks that ask for committee-ready JSON from the public API. Work from the prompt identifiers and the supplied answer template; do not hardcode branch, segment, application, or loan IDs from examples.

## Core Workflow

1. Read the prompt and answer template first. Treat the template as the contract for required keys, enum spellings, ordering, and numeric precision.
2. Pull only the public API surfaces needed by the prompt: manifest, branch details, branch metrics, loans, sector exposures, applications, policies, FDIC benchmarks, NCUA benchmarks, or credit-union segment details.
3. Use the review date to choose the matching branch metric quarter. For 2025-03-31, use 2025Q1 metrics unless the prompt explicitly names another period.
4. Build the answer mechanically from the template:
   - currency and exposures: round to 2 decimals;
   - ratios: decimals rounded to 4 decimals;
   - basis points: `(ratio variance) * 10000`, rounded to 2 decimals;
   - weighted scores: round to the template precision, commonly 1 decimal;
   - reason codes and conditions: use only template enums and sort as requested.
5. Return only the JSON object. Do not include prose outside the JSON.

## Risk Rating And Watch-List Rules

- “Rated N or worse” means numeric rating `>= N`; lower numeric ratings are better.
- For regraded loan populations, derive the final rating from the worst numeric rating among available DSCR, LTV/collateral, and payment-status factors from `policies.risk_rating`. Do not clamp the rederived rating to the current rating; upgrades are allowed when the factors support them. If no regrade factor is available, retain the current rating rather than inventing a null or extreme value.
- Delinquency/payment floors are minimum ratings. Nonaccrual is the most severe payment status.
- Material downgrade means `final_rating - current_rating >= policies.risk_rating.material_downgrade_notches`.
- For watch-list DSCR stress, use `stressed_dscr = dscr / (1 + 0.18)` and include only loans with DSCR available.
- For CRE dual stress, use `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- A coverage breach is `stressed_dscr < policies.stress.coverage_breach_threshold`.
- For workout queues, use severity-oriented actions: rating 6 generally maps to `special_assets`, rating 7 to `workout`, and rating 8/nonaccrual to `legal_referral`. Use `partial_chargeoff_review` only when the prompt or template specifically asks for chargeoff/projected-loss treatment.
- Severe payment-status bucket summaries usually start at rating 7 unless the template asks for the full adverse population.

## CDFI Factor Classes

- Use `policies.cdfi_factor_scores` for debt-to-asset, FICO, liquidity months, and LTV factor scores.
- Score only objective factors that are available and applicable. Do not penalize missing non-applicable fields unless the prompt explicitly treats missing information as a documentation or policy-floor issue.
- Map total factor score to the policy classes. If a prompt flags an underwater nonaccrual/projected-loss review, mark projected-loss treatment even if other score fields are sparse.

## Benchmark And Variance Conventions

- Use the benchmark version named by the manifest or prompt.
- FDIC ratios are decimals. For NPA or delinquency variance, calculate:
  - `variance_ratio = branch_ratio - benchmark_ratio`
  - `variance_bps = variance_ratio * 10000`
- When the template names a branch metric such as delinquency or nonperforming loans, use the branch metric value directly instead of rebuilding a narrower denominator, unless the prompt explicitly asks for a sub-portfolio ratio.
- For NCUA segment tasks, copy state benchmark integer metrics exactly as reported. Sort peer states ascending, compute the peer median metric by metric, then record direction as `higher`, `lower`, or `equal` for the target state versus US and versus the peer median.
- Interpret external risk direction economically: higher delinquency and higher loan-to-share are more strained; lower ROAA and lower positive-net-income share are weaker.

## Allocation And Concentration

- Separate gross approval from bank capacity used. SBA guaranties, participations, or retained-exposure caps can make `bank_capacity_used` less than `approved_amount`.
- Existing over-ceiling sector exposure may be grandfathered, but new approvals that worsen the sector need mitigation such as participation, reduced amount, or committee exception.
- Use `sector_exposures.limit_pct` when a sector-specific limit exists; otherwise use the branch default sector ceiling.
- For concentration ratios, prefer the branch metric `total_loans_outstanding` as the exposure denominator unless the template explicitly says to use lending capacity. Lending capacity is for allocation capacity, not automatically the denominator for portfolio concentration.
- Priority rankings should include only approved and conditionally approved applications unless the template says otherwise. Keep participation-required, declined, or deferred items out of approval priority lists.

## CRE Competing-Application Decisions

- Use `policies.cre_weighted_score.weights` for the weighted CRE score. Lower is better; map scores to policy classes: `approve_quality` at or below the approve max, `conditional` at or below the conditional max, and `weak` above that.
- Component scoring should be grounded in objective fields:
  - capacity: DSCR and stressed DSCR;
  - capital: debt-to-asset or comparable leverage;
  - character: guarantor strength, prior delinquencies, relationship tenure, and documentation;
  - collateral exposure: LTV and appraisal quality;
  - conditions: sector/CRE concentration, benchmark underperformance, and policy exceptions.
- For CRE concentration, use existing CRE exposure over branch total loans, and add the selected request to the numerator for post-approval concentration unless the prompt specifies a different retained-exposure amount.
- If the stronger CRE credit passes stress but branch CRE concentration or FDIC variance is adverse, prefer a controlled path (`conditional_approve` or `participation_required`) with conditions rather than an unconditional approval.
- Sort unselected reason codes alphabetically and keep them to the narrowed enum in the recommended-path section.

## Segment Posture Controls

- For credit-union segment posture tasks, start with the segment’s own minimum checklist; do not add checklist gates merely because they sound plausible.
- Added operating controls should correspond to concrete segment facts: insurance/lien exceptions, staffing constraints, benchmark monitoring, or delinquency watch items.
- Do not add a capacity-overrun control unless capacity is actually exceeded or an exception is requested.
- If capacity is available but external benchmarks are weaker than national and peer comparisons, the usual posture is tighter conditions rather than a full pause.

## Final Checks

- Confirm every list obeys template ordering: IDs ascending, exposure queues descending when requested, reason codes alphabetic, and grouped buckets sorted by the specified keys.
- Reconcile counts and exposures back to the included population before finalizing.
- Use exact enum strings from the template; never invent friendly labels.
