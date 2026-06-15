# Blind-vs-official diff (error reflections)

This is the field-by-field comparison that produced the rules in SKILL.md. Each entry is
generalized — the fix is a rule, not a memorized number. Numbers are illustrative of *what kind*
of error occurred, not answers to copy.

## Task family A — branch rating-migration review

**What matched:** target population (loans ≥ rating 3), target_exposure, final_rating exposure
totals, migration buckets, material_downgrades, NPA ratio/variance, top_problem_credit identity.

**What was wrong → fix:**
- `recommended_action` for the Nonaccrual / final-rating-8 loan: blind `legal_referral`,
  official `partial_chargeoff_review`. → The action enum is a deterministic map on the
  **re-derived final rating**: 6→watchlist, 7→special_assets, 8→partial_chargeoff_review. Do not
  invent a severity scale; `legal_referral`/`workout` were never the right answer in training.
- `by_action` list order: blind emitted watchlist→special_assets→legal_referral; official is
  alphabetical (partial_chargeoff_review, special_assets, watchlist). → Sort enum lists
  alphabetically.

Root cause: the action enum is not defined in `/api/policies`, so the blind solver guessed a map.
The right move was to infer the map from the data shape (one action per final-rating tier) rather
than impose banking intuition (Nonaccrual ⇒ legal referral).

## Task family B — lending-committee allocation

This task had the most errors; all stemmed from invented participation/approval mechanics.

- `bank_capacity_used` for a participation-required, concentration-breaching app: blind used 50%
  of requested; official uses the **sell-down to ceiling** formula
  `retained = (limit*(base + other_bank_used) − existing_sector)/(1 − limit)`. → This is the
  single highest-value rule; it cascades into committed_capacity_amount and remaining_capacity.
- `bank_capacity_used` for an SBA app: blind 50%, official = approved × (1 − sba_guaranty_pct)
  (75% guaranty ⇒ retain 25%).
- A strong app the blind made `participation_required` was actually a clean `approve` (full bank
  retention). → Participation is only forced by a concentration breach, not by ordinary strength.
- `concentration_flags`: blind empty (its 50% haircut hid all breaches); official had the one
  Healthcare breach with `flag:true`, `handling:participation_required`. → Measure breaches on
  **gross** approved amounts, not haircut amounts.
- `post_approval_concentrations`: blind listed all 10 sectors with a wrong (non-growing)
  denominator; official lists only the ~4 sectors that received a new approval, with denominator =
  total_loans_outstanding + Σ gross approved. → Restrict the population to touched sectors and grow
  the denominator.
- `decline_reasons`: thresholds confirmed (weak_dscr<1.25, high_ltv>0.80, low_fico<580,
  startup_risk yib<2, recent_bankruptcy not-null). Two nuances: codes are alphabetical, and the
  list is pruned to decisive reasons (a high_ltv was dropped when low_fico + recent_bankruptcy
  already explained the decline). A no-flag app can still be declined for `capacity_limit` when
  out-prioritized.

## Task family C — credit-union segment posture

**What matched:** posture, state_metrics, peer_states, all directional comparisons, interpretation
block, added_operating_controls set.

**What was wrong → fix:**
- `required_checklist_gates` order: blind alphabetized; official preserves the segment's
  `minimum_checklist` **source order**. → Copy source order for source-provided lists.
- `escalation_triggers`: blind emitted 4 (incl. a generic "gap widens 25bps"); official had 3,
  only those tied to a named segment condition (recent delinquency near 90bps, the insurance/lien
  control_issue, quarterly capacity). → Emit only condition-backed triggers.
- `trigger_id` format: blind `ESC-1`; official `ET001` (zero-padded, `ET` prefix). → Match id
  convention; sort ascending.

## Task family D — watch-list stress packet

**What matched:** adverse population, adverse_balance, all stressed DSCRs and breach flags,
workout_queue ordering, severe_bucket exposures.

**What was wrong → fix:**
- `risk_class` for the underwater (ltv 1.18), score-17, Nonaccrual loan: blind `Watch` (strict
  band); official `Projected Loss`. A sibling loan with score 17 but ltv 0.93 stayed `Watch`. →
  **ltv > 1.0 promotes to Projected Loss regardless of the score band.**
- `recommended_action` for that loan: blind `legal_referral`, official `partial_chargeoff_review`;
  `projected_loss` blind false, official true. → Projected Loss ⇒ partial_chargeoff_review +
  projected_loss:true.
- `severe_bucket_counts` order within a rating: blind put `Current` before `90+ Days Past Due`
  (enum/severity order); official puts `90+ Days Past Due` first. → Secondary sort on
  payment_status is **ASCII ascending** (`'9' < 'C'`), not enum order.

## Task family E — competing CRE decision

**What matched:** stress results, existing_cre_exposure/concentration, selected post-approval
concentration and its bps variance, conditions (mostly), selected app + path.

**What was wrong → fix:**
- `weighted_cdfi_score`: blind tied capacity to a DSCR-derived value (scores ~1.9/2.1); official
  scores were higher and driven by debt_to_asset (the 1.8-point gap between the two apps = 0.45 ×
  (dta_sub 6 − dta_sub 2)). → capacity sub-score = debt_to_asset CDFI sub-score;
  collateral_exposure = LTV CDFI sub-score. This flipped score_class (901 conditional, 902 weak).
- `unselected_disposition`: blind `decline`, official `defer` (weak score ⇒ defer).
- App `reason_codes`: blind omitted `fdic_adverse_variance` and used `capacity_limit` for the CRE
  breach; official includes `fdic_adverse_variance` on both apps (branch RE delinquency far over
  FDIC) and uses `sector_breach` for the CRE concentration breach.
- `branch_delinquency_ratio`: blind recomputed an RE-only ratio from loan rows (~0.49); official =
  the branch `delinquency_30_plus_pct` metric (~0.285). → Use the metric field; don't reconstruct.
- `conditions`: blind omitted `updated_appraisal_before_close`; official included it. → When in
  doubt for a CRE breach + underperformance, the full condition set applies; sort alphabetically.

## Cross-cutting reflections

1. When an enum/map is not in `/api/policies`, infer it from the data's structure (one value per
   tier) instead of importing real-world banking intuition.
2. Participation and SBA change `bank_capacity_used`, never `approved_amount`. The retained amount
   is derived (sell-down to ceiling / 1−guaranty), never a flat percentage.
3. Prefer a provided metric field over re-deriving the same quantity from rows — the grader keys
   on the metric.
4. Ordering and population/exclusion are graded as hard as the numbers: source order vs
   alphabetical vs ASCII, and "only touched/eligible rows."
