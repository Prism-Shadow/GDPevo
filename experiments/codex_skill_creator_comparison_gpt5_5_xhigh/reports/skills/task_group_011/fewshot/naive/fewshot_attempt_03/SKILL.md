---
name: credit-office-committee-json
description: Solve credit-office lending committee tasks by deriving JSON answers from the public API, policy rules, benchmarks, and the supplied answer template.
---

# Credit Office Committee JSON Skill

Use this skill when a task asks for a credit-office, lending-committee, credit-risk, branch, portfolio, pending-application, CRE, watch-list, FDIC benchmark, NCUA benchmark, or credit-union segment JSON answer from `<TASK_ENV_BASE_URL>`.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. The template is authoritative for keys, enum values, precision, and sorting.
2. Set the API base URL from the runner value: `BASE="$TASK_ENV_BASE_URL"`. If the runner presents the placeholder text only, use the task environment base URL provided with the task.
3. Fetch only public API data needed for the prompt:
   - `/api/manifest`
   - `/api/policies`
   - `/api/benchmarks/fdic/q4-2024`
   - `/api/benchmarks/ncua/q1-2025`
   - `/api/branches/{branch_id}`
   - `/api/branches/{branch_id}/metrics`
   - `/api/branches/{branch_id}/loans`
   - `/api/branches/{branch_id}/sector-exposures`
   - `/api/branches/{branch_id}/applications`
   - `/api/credit-union-segments/{segment_id}`
4. Build the answer from calculations, not from names or narrative notes alone. Use notes only as supporting evidence when the prompt asks for posture, controls, mitigants, or recommended actions.
5. Emit one valid JSON object with no text outside JSON.

## General Calculation Rules

- Use the latest quarter on or before the review/as-of date, usually the `2025Q1` metrics row for a `2025-03-31` task.
- Money fields: round to 2 decimals only at output time. Ratios and percentages in templates are decimal ratios, not percent strings.
- Basis points: `ratio * 10000`, rounded to the requested precision.
- Sort exactly as the template says. If it says sort by an enum-like string without an explicit enum order, use lexicographic ascending order.
- For grouped totals, group before rounding and sum source balances, not already rounded display values.
- Missing numeric factors are ignored in factor scoring. If all objective regrade factors are missing, preserve the existing current rating for that loan.
- Reason-code and condition arrays must use only template enums. Sort reason codes alphabetically unless the template says otherwise.

## Policy Rules To Apply

Read `/api/policies` and use those values if present. The policy normally contains:

- Risk rating thresholds:
  - DSCR maps to numeric ratings: high DSCR is better; below the policy breach threshold is worse.
  - LTV maps to numeric ratings: low LTV is better; LTV above 1.0 is severe.
  - Payment delinquency minimums set floors for `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, and `Nonaccrual`.
  - Re-derived final rating is the worst numeric rating from available DSCR, LTV/collateral, and delinquency factors.
- Material downgrade threshold: use `risk_rating.material_downgrade_notches`.
- Watch-list stress: `stressed_dscr = dscr / (1 + 0.18)` unless the policy endpoint gives a different expression.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)` unless the policy endpoint gives a different expression.
- CDFI factor scoring:
  - Score available `ltv`, `debt_to_asset`, `liquidity_months`, and `fico` from the policy tables.
  - Sum the factor scores.
  - Map the sum to the policy classes.
  - Override to `Projected Loss` when the credit is nonaccrual or otherwise explicitly projected-loss, and collateral is underwater.
- CRE weighted score:
  - Use `cre_weighted_score.weights`.
  - Lower score is better.
  - Capacity should reflect repayment coverage, including stressed DSCR when the prompt asks for stressed repayment.
  - Capital should reflect leverage or debt-to-asset.
  - Character should reflect guarantor strength, relationship depth, prior delinquencies, and bankruptcy history.
  - Collateral/exposure should reflect LTV plus sector or CRE concentration.
  - Conditions should reflect branch/sector concentration and adverse FDIC benchmark variance.
  - Classify by the policy `approve_quality`, `conditional`, and `weak` score cutoffs.

## Branch Rating Migration Tasks

Use this for prompts asking to re-derive ratings, summarize migration, benchmark NPA variance, list material downgrades, or identify the worst problem credit.

1. Select loans from `/loans` where `current_rating >= target_current_rating_min` from the prompt.
2. For each selected loan:
   - Derive DSCR rating from policy if `dscr` is available.
   - Derive LTV rating from policy if `ltv` is available.
   - Derive delinquency/payment rating from policy if payment status is not current.
   - `final_rating = max(available_factor_ratings)`. If no factors are available, use `current_rating`.
3. Portfolio totals:
   - `target_loan_count`: selected loan count.
   - `target_exposure`: sum selected `outstanding_balance`.
   - `final_rating_exposure_totals`: group by final rating, count loans, sum exposure, sort ascending final rating.
   - `migration_from_current_rating_3`: only selected loans whose current rating is exactly 3, grouped by final rating. Include loan IDs sorted ascending.
4. Watch-list action coverage:
   - Include loans needing follow-up after regrade, normally final rating 6 or worse.
   - Recommended action mapping:
     - Final rating 6: `watchlist`.
     - Final rating 7: `special_assets`.
     - Final rating 8 or projected loss/nonaccrual with underwater collateral: `partial_chargeoff_review`.
     - Use `workout` or `legal_referral` only when the facts clearly demand those enum values.
   - Group coverage by action, sort by action, and include counts, exposure, and sorted loan IDs.
5. Material downgrades:
   - Include loans where `final_rating - current_rating >= material_downgrade_notches`.
   - Sort by loan ID.
6. NPA benchmark:
   - `branch_npa_exposure = latest_metrics.nonperforming_loans`.
   - `branch_total_loans = latest_metrics.total_loans_outstanding`.
   - `branch_npa_ratio = branch_npa_exposure / branch_total_loans`.
   - Select the FDIC metric requested by the template/prompt.
   - `variance_ratio = branch_ratio - fdic_benchmark_ratio`.
   - `variance_bps = variance_ratio * 10000`.
7. Top problem credit:
   - Choose the most severe selected loan by final rating, then nonaccrual/projected-loss evidence, then largest exposure.
   - Include borrower name, exposure, current/final rating, payment status, and recommended action.

## Pending Application Allocation Tasks

Use this for prompts asking for allocation, application decisions, concentration flags, decline reasons, and post-approval concentration view.

1. Fetch branch, latest metrics, sector exposures, applications, and policies.
2. Start with hard-fail reason codes:
   - `weak_dscr`: DSCR below the task or policy floor, or stressed DSCR below threshold when the task uses stress.
   - `high_ltv`: LTV exceeds the product/sector tolerance implied by policy and examples; business/CRE requests around or above 0.80 often need this code.
   - `low_fico`: FICO is below acceptable floor.
   - `recent_bankruptcy`: bankruptcy is recent enough to be material.
   - `startup_risk`: very short time in business without strong SBA/guarantor mitigation.
   - `documentation_gap`: documentation is incomplete and the template allows the code.
   - `sector_breach`: approval would worsen a sector above its limit without mitigation.
   - `capacity_limit`: the application is not selected because branch capacity is consumed by higher-priority acceptable credits.
3. Decision treatment:
   - `decline` when unmitigated hard-fail reasons are present.
   - `approve` when credit quality is acceptable, capacity is available, and no sector mitigation is needed.
   - `conditional_approve` when approval is acceptable only with enumerated conditions, such as SBA guaranty, startup monitoring, reduced amount, or participation.
   - `participation_required` when the bank should approve the credit but retain only the amount that keeps internal sector or capacity exposure within limits.
   - `defer` when the credit is not selected in a competing comparison but is not an outright hard decline.
4. Capacity fields:
   - `lending_capacity_q1` comes from the branch record.
   - `approved_amount` is normally the requested amount for approved or conditionally approved applications, else 0.
   - `bank_capacity_used` is the retained bank amount.
   - For SBA approvals, `bank_capacity_used = approved_amount * (1 - sba_guaranty_pct)`.
   - For participation, solve the retained amount needed to respect the sector ceiling against bank-retained exposure:
     `retained = (limit_pct * (latest_total_loans + other_committed_capacity) - current_sector_exposure) / (1 - limit_pct)`.
     Clamp retained between 0 and the requested amount.
   - `committed_capacity_amount = sum(bank_capacity_used)`.
   - `gross_approved_amount = sum(approved_amount)`.
   - `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
5. Priority ranking:
   - Include only approved and conditionally approved application IDs.
   - Rank stronger, strategically necessary, or mitigation-ready credits first. Use DSCR, LTV, guarantor/SBA support, relationship quality, and concentration handling to break ties.
6. Concentration flags:
   - Evaluate each approved or conditionally approved application's sector using sector exposures and the latest total loans.
   - Flag an application if full retained exposure would breach the limit, would worsen an already grandfathered/over-limit sector, or requires participation/reduced amount/board exception.
   - Use handling enum matching the mitigation.
7. Post-approval concentration view:
   - Include sectors affected by approved or conditionally approved applications.
   - `exposure_after_approval = current_sector_exposure + gross approved amount in that sector`.
   - Denominator is `latest_total_loans + gross_approved_amount` unless the prompt explicitly asks for bank-retained exposure.
   - `post_approval_pct = exposure_after_approval / denominator`.
   - `over_limit = post_approval_pct > limit_pct`.

## Watch-List Stress And Workout Tasks

Use this for prompts asking for adversely rated loans, CDFI-style risk classes, watch-list DSCR stress, workout queue, or severe bucket counts.

1. Select loans with `current_rating >= adverse_rating_min` from the prompt.
2. Summary:
   - Count selected loans and sum outstanding balances.
   - Monitoring cadence is usually `monthly` for adverse-rated watch-list populations.
3. CDFI risk classes:
   - Score available `ltv`, `debt_to_asset`, `liquidity_months`, and `fico` from policy.
   - Sum to `factor_score`.
   - Map to CDFI class from policy; apply the projected-loss override for underwater nonaccrual/projected-loss facts.
   - Sort risk class rows by loan ID.
4. Stress:
   - Include only selected loans with DSCR available.
   - Use the policy watch-list stress formula.
   - `breaches_threshold = stressed_dscr < breach_threshold`.
   - Sort results and breach IDs by loan ID.
5. Workout queue:
   - Include selected loans requiring queue action.
   - Sort by descending exposure, then ascending loan ID.
   - Recommended action:
     - Projected Loss: `partial_chargeoff_review`.
     - Nonaccrual or severe payment distress without projected loss: `workout` or `special_assets`, depending on template fit.
     - Rating 7 or 90+ days past due: `special_assets`.
     - Rating 6 current credits: `watchlist`.
6. Severe bucket counts:
   - Group selected loans by `current_rating` and `payment_status`.
   - Sum loan count and exposure.
   - Sort by current rating, then payment-status string unless the template provides an explicit status order.

## Competing CRE Decision Tasks

Use this for prompts comparing two or more CRE applications and asking for a selected path, stress, concentration, conditions, or reason-code treatment.

1. Restrict `applications_compared` to the application IDs named in the prompt.
2. Compute CRE weighted scores using policy weights and objective sub-scores. Round to one decimal. Lower is better.
3. Compute stress with the policy CRE dual-stress formula and threshold.
4. Classify:
   - Score at or below approve-quality cutoff: `approve_quality`.
   - Score at or below conditional cutoff: `conditional`.
   - Above conditional cutoff: `weak`.
5. Decision and reason codes:
   - Add `weak_dscr` when stressed DSCR breaches threshold.
   - Add `high_ltv` for high collateral leverage.
   - Add `sector_breach` when the CRE or sector concentration is over limit or would worsen over-limit exposure.
   - Add `fdic_adverse_variance` when branch delinquency/noncurrent ratio exceeds the selected FDIC benchmark.
   - Select the lower-score credit unless it has an unmitigated hard fail.
   - Use `participation_required` for the selected credit when concentration is already above policy or approval requires retained-exposure cap.
   - Use `defer` for an unselected but potentially bankable competing credit; use `decline` only for clear hard-fail treatment.
6. CRE concentration:
   - Existing CRE exposure is the sum of outstanding balances where `loan_type == "CRE"`.
   - `existing_cre_concentration = existing_cre_exposure / latest_total_loans`.
   - For the selected application, `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_requested_amount) / (latest_total_loans + selected_requested_amount)`.
   - `selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`.
   - Use the FDIC metric named by the template and compute branch variance as branch ratio minus benchmark ratio.
7. Conditions:
   - Choose only template enums.
   - Participation/concentration cases usually need retained exposure cap, committee exception, CRE reporting/covenants, no additional CRE without review, appraisal/tenant diligence when relevant.
   - Sort conditions as the template requires.

## Credit-Union Segment Posture Tasks

Use this for prompts asking for a credit-union segment posture, NCUA state metrics, peer comparison, controls, triggers, and controlled interpretation.

1. Fetch `/api/credit-union-segments/{segment_id}`, `/api/benchmarks/ncua/q1-2025`, `/api/policies`, and manifest as needed.
2. State metrics:
   - Select the NCUA row for `segment.state_code`.
   - Copy exact integer benchmark metrics requested by the template.
3. Peer comparison:
   - Use `segment.peer_states`.
   - Compare the state value to the `US` row and to the median of peer-state values.
   - Return `higher`, `lower`, or `equal` for each metric.
4. Controls:
   - `required_checklist_gates` should come from the segment minimum checklist.
   - Add operating controls based on segment facts:
     - Insurance issue: `pre_close_insurance_binder_verification`.
     - Lien or title collateral: `lien_perfection_prior_to_funding`.
     - Elevated internal delinquency: `monthly_segment_delinquency_watch`.
     - External state benchmark weakness: `quarterly_state_benchmark_monitoring`.
     - Staffing or judgment-sensitive approvals: `senior_underwriter_second_review`.
     - Capacity overrun or exception: `committee_exception_for_capacity_overrun`.
5. Posture and interpretation:
   - `continue_approving`: capacity available and external metrics stronger or routine.
   - `continue_with_tighter_conditions`: capacity available but external or internal risk is weaker/mixed and controls can mitigate.
   - `temporarily_pause`: no capacity, severe benchmark weakness, or unmitigated operating control failures.
   - Capacity status:
     - Available if quarterly capacity remains for ordinary production.
     - Constrained if near capacity or requiring exceptions.
     - No capacity if approvals would exceed capacity.
   - External risk status:
     - Stronger if the state is better than both national and peer median on risk metrics.
     - Mixed if directions are split.
     - Weaker if delinquency and utilization are higher while earnings metrics are lower.
   - Use the committee-message enum that matches capacity plus external risk.
6. Escalation triggers:
   - Include trigger rows for monitored future exceptions, not just already-breached facts.
   - Use stable trigger IDs sorted ascending.
   - Assign owners by domain: credit risk for delinquency/benchmark risk, operations control for insurance/lien files, lending committee chair for capacity or exception approval.

## Final Validation

Before final output:

- Confirm every required top-level key exists and no extra narrative text is present.
- Confirm every enum value appears in the template.
- Confirm all requested rows are sorted as specified.
- Recompute totals from source data and verify grouped exposure sums tie back to summary fields.
- Verify ratio and money precision.
- Run `python -m json.tool` on the draft JSON when a shell is available.
