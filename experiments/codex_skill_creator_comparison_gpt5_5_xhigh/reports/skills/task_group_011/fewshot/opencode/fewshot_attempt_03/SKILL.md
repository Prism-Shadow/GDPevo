---
name: credit-office-committee-json
description: Use this skill for shared credit office API tasks that ask Codex to produce committee-ready, schema-constrained JSON for branch, loan, pending application, benchmark, credit-union segment, risk-rating, concentration, stress, allocation, or posture reviews. Trigger whenever a prompt mentions TASK_ENV_BASE_URL, a credit office public API, branch_id, segment_id, FDIC/NCUA benchmarks, credit policy, lending committee packages, risk rating migration, watch-list stress, CRE decisions, or JSON matching an answer_template.
---

# Credit Office Committee JSON

Use this skill to solve credit-office API tasks that require a single JSON answer matching `input/payloads/answer_template.json`.

The evaluator rewards exact derivation and exact shape. Treat the prompt, template, public API, policies, and benchmark endpoints as the only sources of truth. Do not use web search or remembered example answers.

## Files

- Use `scripts/credit_review_toolkit.py` for API collection, common formulas, and final template checks.
- Read `references/reasoning-guide.md` when the task involves risk ratings, CDFI classes, CRE scoring, allocation, concentration, benchmark variance, or posture selection.

## Workflow

1. Read the prompt and `input/payloads/answer_template.json` completely.
2. Identify all target identifiers: `branch_id`, `segment_id`, application IDs, review/as-of dates, rating thresholds, benchmark versions, and any requested comparison set.
3. Resolve the API base URL from the runner-provided `TASK_ENV_BASE_URL` or the literal base URL in the prompt. Normalize it to one trailing slash.
4. Fetch only public API data needed for the target:
   - Always fetch `/api/manifest` and `/api/policies`.
   - For bank branch tasks, fetch branch details, metrics, loans, sector exposures, applications as needed.
   - For benchmark tasks, fetch the named FDIC or NCUA benchmark endpoint.
   - For credit-union segment tasks, fetch `/api/credit-union-segments/{segment_id}`.
5. Build a scratch derivation table before writing the answer. Keep the scratch outside the final response.
6. Apply policy formulas and controlled enum choices from the API/template, not from intuition.
7. Fill every required template key. Sort lists exactly as the template says.
8. Validate the final JSON mechanically, then manually reconcile totals and ratios.
9. Return only valid JSON. Do not include explanatory text around it.

## API Collection

Use the helper to collect a local snapshot for inspection:

```bash
python skill/scripts/credit_review_toolkit.py collect \
  --base-url "$TASK_ENV_BASE_URL" \
  --branch-id "$BRANCH_ID" \
  --segment-id "$SEGMENT_ID" \
  --out /tmp/credit_api_snapshot.json
```

Omit `--branch-id` or `--segment-id` when not applicable. If the current working directory is the task root and this skill is loaded from a different path, adjust `skill/scripts/...` to the actual skill path.

The snapshot is only a convenience. You may also call endpoints directly with `curl`.

## Core Derivations

Use the current-quarter branch metrics unless the prompt explicitly asks for another quarter. When dates are review dates, do not invent time-series adjustments unless the policy/API data provides them.

Use these rounding conventions unless the template says otherwise:

- Currency: 2 decimals.
- Ratios and policy percentages: 4 decimals.
- Basis points: 2 decimals for calculated bps, integer bps when the benchmark table reports integers.
- Weighted scores: the precision stated by the template, usually 1 decimal.

Benchmark variance:

```text
branch_ratio = branch_metric / branch_total_loans_or_other_denominator
variance_ratio = branch_ratio - benchmark_ratio
variance_bps = variance_ratio * 10000
```

Risk-rating regrade:

- Regrade only the population requested by the prompt.
- From `/api/policies`, derive DSCR, LTV/collateral, and delinquency ratings.
- Final rating is the worst numeric rating from available objective factors. If no objective factor is available, do not improve the current rating by assumption.
- A material downgrade is a final rating worse than current rating by at least the policy material-downgrade notch threshold.

Stress:

- Watch-list stress uses the policy `watch_list_formula`.
- CRE dual stress uses the policy `cre_dual_stress_formula`.
- Compare stressed DSCR with `coverage_breach_threshold`.
- Include only records with available DSCR in stress result lists unless the template requests missing-data entries.

CDFI factor classes:

- Score only available objective factors; do not penalize a missing field unless policy/template says to.
- Sum factor scores from policy bands for LTV, debt-to-asset, FICO, and liquidity months.
- Class from the policy score bands. If a credit is nonaccrual and underwater on collateral, treat it as projected-loss even if the raw factor score is below the ordinary projected-loss threshold.

Concentration and allocation:

- Sector exposure after approval is current sector exposure plus the approved gross amount for selected/approved applications in that sector.
- Total exposure after approval is current total loans/exposure plus approved gross amounts unless the template clearly asks for bank-retained capacity only.
- `bank_capacity_used` is the portion retained by the bank after participation, guaranty, or reduced-amount mitigation.
- Existing over-limit or near-limit sectors require mitigation; new approvals should not worsen a sector breach without a controlled condition/reason code.
- Priority rankings include approved and conditionally approved applications only, in descending credit/committee priority.

Controlled reason codes:

- Use only enums allowed by the template.
- Attach reason codes to the specific weakness supported by data:
  - `weak_dscr`: base or stressed repayment coverage fails the task/policy threshold.
  - `high_ltv`: collateral leverage is above policy tolerance.
  - `underwater_collateral`: LTV is above 1.0 when that enum is available.
  - `low_fico`: FICO falls into the weakest policy band.
  - `recent_bankruptcy`: bankruptcy history is present and recent.
  - `startup_risk`: short operating history or startup note is material and not fully mitigated.
  - `documentation_gap`: required documentation is incomplete.
  - `sector_breach`: post-approval exposure exceeds, worsens, or materially crowds a sector limit.
  - `capacity_limit`: retained exposure would exceed remaining lending capacity.
  - `fdic_adverse_variance`: branch metric is worse than the FDIC benchmark metric used by the template.
  - `ncua_peer_weakness`: state credit-union metrics are weaker than national or peer-state comparators.

## Output Discipline

Before final answer:

- Check all required top-level and nested keys.
- Check exact enum spelling and case.
- Check number precision and that ratio fields are ratios, not percentages.
- Check all list ordering rules from the template.
- Re-sum exposure totals from source records, not from previously rounded groups.
- Recompute every variance and bps field from the rounded or unrounded source consistently.
- Ensure no narrative text appears before or after the JSON object.

Run a final validation:

```bash
python skill/scripts/credit_review_toolkit.py validate \
  --template input/payloads/answer_template.json \
  --answer /tmp/final_answer.json
```

If validation flags issues, fix the JSON and run it again.
