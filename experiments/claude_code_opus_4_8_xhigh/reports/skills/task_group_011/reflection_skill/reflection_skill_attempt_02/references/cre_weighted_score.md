# 5-C Weighted CDFI Score (CRE competing-decision tasks)

Read this before populating `weighted_cdfi_score` / `score_class` in a CRE comparison.
This is the most underspecified rule in the family: the policy endpoint gives the **weights
and class cutoffs** but **not** which raw application field feeds each "C" or the exact
0-6 sub-scale per C. Treat the parts below as: CERTAIN (from policy), STRONG (consistent
with official answers), and JUDGMENT (you must reason and sanity-check).

## CERTAIN — from `/api/policies` `cre_weighted_score`

Weights (they sum to 1.0):

| C | weight |
|---|---|
| capacity | 0.45 |
| collateral_exposure | 0.36 |
| conditions | 0.11 |
| character | 0.05 |
| capital | 0.03 |

Class cutoffs on the weighted total (lower is better):
- `weighted_cdfi_score <= 2.0` → `approve_quality`
- `<= 3.0` → `conditional`
- `> 3.0` → `weak`

`capacity` (0.45) and `collateral_exposure` (0.36) together drive ~81% of the score, so
spend your effort getting those two right; `character` (0.05) and `capital` (0.03) barely
move the result.

## STRONG — scoring approach consistent with the official answers

Score each C on the same 0-6 CDFI-style sub-scale used elsewhere in the policy
(`cdfi_factor_scores`), where **higher = worse** (since lower total is better):

- **capacity** ← repayment coverage, driven by **DSCR** (and stressed DSCR). Weaker DSCR →
  higher capacity score. This factor must separate the two competing credits: the stronger
  DSCR / stress-passing credit gets a clearly lower capacity score than the weaker /
  stress-breaching one.
- **collateral_exposure** ← **LTV** on the CDFI LTV scale (`<0.40 ->0`, `0.40-0.60 ->2`,
  `0.60-0.80 ->4`, `>0.80 ->6`), reflecting collateral coverage and the branch CRE
  exposure pressure. When branch CRE is already over its `cre_policy_limit_pct`, both
  competing credits carry meaningful collateral_exposure weight.
- **capital** ← leverage = `total_debt / total_assets` on the CDFI debt-to-asset scale
  (`<0.40 ->0`, `0.40-0.60 ->2`, `0.60-0.80 ->4`, `>0.80 ->6`). A borrower whose debt
  exceeds assets (ratio > 1.0) lands at the top of the scale.
- **conditions** ← deal/relationship context (e.g. `existing_relationship_years`, seasonal
  cash-flow / sponsor dependence noted in `notes`). Longer, stable relationships → lower.
- **character** ← guarantor strength + delinquency history (`co_guarantor_strength`,
  `prior_delinquencies_12m`). Strong guarantor / clean history → lower.

Compute `weighted_cdfi_score = Σ weight_C * subscore_C`, rounded to **1 decimal** (per the
template's `precision: 1`).

## JUDGMENT & sanity checks

The exact sub-scale boundaries for capacity/conditions/character are not published, so
verify your result against these anchors instead of trusting a single recipe:

1. **Relative order must match the credit story.** The stronger credit (better DSCR, lower
   LTV, lower leverage, longer relationship, stronger guarantor, stress-passing) must score
   **lower** than the weaker one. If your numbers invert that, your sub-mapping is wrong.
2. **The weaker credit should not be artificially compressed into `conditional`.** A credit
   that breaches stress, has high leverage (debt > assets), a short relationship, and no
   guarantor should land in **`weak` (> 3.0)** — a common blind error was scoring it ~2.9
   and mislabeling it `conditional`, which then flipped the disposition. Let the dominant
   `capacity` and `collateral_exposure` factors push a genuinely weak credit past 3.0.
3. **Score class must agree with the decision.** `approve_quality`/`conditional` credits get
   an approval-style path; a `weak` competing credit that loses the head-to-head is
   `defer` (not decline). If class and decision disagree, re-examine.
4. **Both competing credits over an already-breached CRE limit** will each carry
   `sector_breach` (and `fdic_adverse_variance` when branch RE delinquency exceeds the FDIC
   benchmark). The selected credit's reason codes should reflect the *binding* constraints
   (sector_breach, fdic_adverse_variance) — do **not** add `capacity_limit` unless lending
   capacity is actually exhausted, and do **not** add `high_ltv` for an LTV at/below 0.85.

If you cannot fully pin the sub-scales, prioritize getting capacity and collateral_exposure
directionally right and the **score_class boundary** correct, since the class (not the exact
decimal) drives the downstream decision and disposition.
