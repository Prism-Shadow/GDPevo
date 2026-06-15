# Worked examples (end-to-end traces)

These trace each family from raw API records to the final JSON, so a fresh solver can sanity-check its
own pipeline. They were validated to match real gold answers field-for-field. Client numbers below are
illustrative of the *mechanics* — for a new task, pull that client's own records and recompute.

## A. Roth conversion + RMD

Records: signed profile {non_ira_income 185000, MTR 0.32, age 66, filing MFJ, planning_year 2026};
IRA export {trad 2,800,000, roth 0, return 0.065, rmd_start_age 73, recommended_conversion_years 7};
MFJ bracket target 394600; horizon 2046.

1. annual_conversion_amount = 394600 − 185000 = 209600.0
2. conversion_years = 7; first_conversion_year = 2026
3. total_converted = 209600 × 7 = 1,467,200.0; total_conversion_tax = × 0.32 = 469,504.0
4. first_rmd_year = 2026 + (73 − 66) = 2033
5. Simulate 2026..2046, order = convert → RMD → grow each year:
   - baseline (no conversions): rmd_tax = 1,097,182.33
   - conversion: rmd_tax = 617,448.59; ending roth = 4,594,320.16; ending trad = 2,895,040.03
6. savings = 1,097,182.33 − 617,448.59 = 479,733.74
7. roth share = 4.594M / 7.489M = 0.61 → MIXED_TAXABLE_AND_TAX_FREE
8. recommendation: STAGED_ROTH_CONVERSION / SUITABLE / TAX_BRACKET_MANAGEMENT
9. source_resolution: profile=SIGNED_PROFILE, account=CUSTODIAN_EXPORT

## B. ILIT / Crummey

Records: signed beneficiary_count 4; gift exclusion 2026 = 20000; policy {death_benefit 4,500,000,
annual_premium 78000, planned_contribution_date 2026-03-10, is_existing_policy_transfer false};
estate_tax_rate 0.4.

1. annual_exclusion_per_beneficiary = 20000; capacity = 20000 × 4 = 80,000.0
2. premium_gap = max(0, 78000 − 80000) = 0.0
3. notices_required = 4; dedicated_bank_account_required = true
4. dates from 2026-03-10: notice_due 2026-03-17 (+7d); window_end 2026-04-16 (+30d);
   earliest_premium 2026-04-17 (+1d)
5. death_benefit 4,500,000; projected_outside_estate 4,500,000;
   tax_liquidity_support = 4,500,000 × 0.4 = 1,800,000.0
6. risk: not a transfer + premium_gap 0 → LOW_IF_FORMALITIES_MET; estate_inclusion_risk = same
7. recommendation: FUND_WITH_CRUMMEY_NOTICES / SUITABLE_WITH_ADMINISTRATION / LOW_IF_FORMALITIES_MET
8. source_resolution: beneficiary=SIGNED_PROFILE, policy=SIGNED_PROFILE

## C. GRAT vs CRAT

Records: signed {family_transfer_priority high, philanthropic_intent moderate, marital married,
liquid 6,200,000}; attorney estate_value 38,800,000; trust {asset 8,000,000, growth 0.08,
grat_term 5, grat_annuity 0.04, crat_term 20, crat_payout 0.055}; exemption 2026 = 13,610,000,
rates 0.4 / 0.35.

1. estate_context: exemption_used = 13.61M × 2 = 27,220,000; taxable = 38.8M − 27.22M = 11,580,000;
   exposure = × 0.4 = 4,632,000; liquidity_gap = max(0, 4.632M − 6.2M) = 0.0
2. GRAT_remainder = 8M × 1.08^5 − 8M × 0.04 × 5 = 10,154,624.61;
   estate_tax_reduction = × 0.4 = 4,061,849.85; mortality_inclusion_risk = TERM_SURVIVAL_REQUIRED
3. CRAT_remainder = 8M × 1.08^20 − 8M × 0.055 × 20 = 28,487,657.15;
   income_deduction = × 0.35 = 9,970,680.0; family_transfer_fit = LOW
4. goals: family(high) > philanthropic(moderate) → preferred GRAT, rationale CHILDREN_TRANSFER_PRIORITY,
   alternate SECONDARY_CHARITABLE_TOOL
5. source_resolution: goal=SIGNED_PROFILE, asset=ATTORNEY_MEMO

## D. Estate-liquidity action plan

Records: single client, attorney estate_value 31,200,000, liquid 2,400,000; ILIT policy
{death_benefit 5,200,000, premium 56000, beneficiary_count 3}; trust {asset 9,500,000, growth 0.09,
grat_term 6, grat_annuity 0.045}; family_transfer_priority high.

1. estate_context (single): exemption_used = 13,610,000; taxable = 17,590,000; exposure = 7,036,000;
   liquidity_gap = max(0, 7.036M − 2.4M) = 4,636,000.0
2. ilit: capacity = 20000 × 3 = 60,000; premium_gap = max(0, 56000 − 60000) = 0.0;
   risk LOW_IF_FORMALITIES_MET; projected_outside_estate = 5,200,000
3. trust_transfer: preferred GRAT (family priority high);
   projected_remainder_to_heirs = 13,367,451.05; estimated_estate_tax_reduction = 5,346,980.42;
   projected_charitable_remainder = 42,791,902.29 (CRAT remainder, always reported)
4. recommendation: COMBINE_ILIT_AND_GRAT / ILIT_FIRST_THEN_GRAT / LOW_IF_FORMALITIES_MET
5. action_set (sorted): ATTORNEY_DRAFT_REVIEW, GRAT_FOR_APPRECIATING_SHARES, ILIT_CRUMMEY_NOTICE_CYCLE
   (no LIFETIME_EXEMPTION_ALLOCATION because premium_gap = 0)
6. source_resolution: goal=SIGNED_PROFILE, policy=SIGNED_PROFILE

## Reusing the bundled solver

`references/solver.py` implements all of the above and a `--selftest` that recomputes the bolded numbers
from the live API. Read it, run `python solver.py --selftest`, then for a new task call e.g.
`python solver.py roth CLT-XXXX --horizon 2045` to get the numeric block, and assemble the JSON to match
the exact keys and enum spellings in *that* task's `answer_template.json`. Do not assume the key names —
templates differ slightly between families (e.g. some put `planning_year` inside `estate_context`).
