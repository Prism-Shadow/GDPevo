# Formulas and Computation Rules

Standard formulas for credit risk committee analysis. When the credit policies
endpoint provides explicit thresholds or formulas, those take precedence over
the conventions below.

---

## DSCR Stress Testing

### +200bp Rate Shock (Standard)

Used for watch-list stress and general adverse-scenario testing.



The divisor 1.18 represents a +200bp rate increase over the base rate,
assuming the base rate is embedded in the original DSCR calculation.

**Breach threshold**: 1.0 (stressed DSCR below 1.0 means the borrower cannot
cover debt service under the shocked rate). Use the threshold from policies
when one is provided.

Only compute stress for loans where the API returns a DSCR value. Skip loans
without a DSCR field; do not fabricate values.

Round stressed_dscr to 2 decimal places.

### CRE Dual-Stress (Concurrent Rate + Vacancy Shock)

Used for commercial real estate competing decisions. This applies both a rate
shock and a revenue haircut simultaneously.



- 0.85: 15% revenue haircut (vacancy / lease-roll adjustment)
- 1.18: +200bp rate shock

**Breach threshold**: 1.0 unless policy specifies otherwise.

Round results to 2 decimal places.

---

## NPA Benchmark Variance

Non-performing asset ratio and its variance from the selected benchmark.

### Branch NPA Ratio



Round to 4 decimal places.

### Benchmark Variance



- : decimal, rounded to 4 places
- : basis points, rounded to 2 places

The benchmark metric name to use depends on context:
- For general loan portfolio NPA: 
- For real estate portfolio: 
- For construction/development: 
- For 30-89 day delinquencies: 

Select the metric that best matches the review scope. The policies endpoint
often specifies the recommended benchmark metric.

---

## Sector Concentration

### Base Concentration



Round to 4 decimal places.

### Post-Approval Concentration

When evaluating a new application against an existing sector:



(Some policies may use total_loans + approved_amount as the denominator.
Check policy wording; absent explicit guidance, use total_loans only.)

### Policy Limit Variance



Positive variance means the concentration exceeds the policy limit.

---

## CDFI Factor Scoring

Community Development Financial Institution (CDFI) scoring compresses multiple
objective credit factors into a single weighted score per loan or application.
Lower scores indicate stronger credits.

### Factor Count

The API or policy defines the number of factors (typically 5-7). Each factor is
scored on a 1-5 scale (1 = strongest, 5 = weakest) then weighted.

### Weighted Score



When the policy supplies factor weights, use them. When weights are not
explicit, apply equal weighting. Round to 1 decimal place.

### Score-to-Class Mapping (Applications)

| Weighted Score | Score Class |
|---------------|-------------|
| 1.0 - 2.5 | approve_quality |
| 2.6 - 3.9 | conditional |
| 4.0 - 5.0 | weak |

These thresholds are conventional. Use policy thresholds when provided.

### Factor Score to Risk Class (Loans)

CDFI factor scoring maps to the standard risk classes. The policy endpoint
provides threshold ranges. The conventional mapping is monotonic: higher
factor scores map to worse risk classes.

**Payment-status override**: Nonaccrual payment status forces at least
"Projected Loss" regardless of factor score. "90+ Days Past Due" forces
at least "Doubtful". Apply the worse of the score-derived class and the
payment-status floor.

---

## Capacity Computation



For participation-required applications,  is the portion
the bank retains (not the full approved amount). The API or policy defines
the bank retention split.

Round all currency values to 2 decimal places.

---

## Material Downgrade Detection

A regraded loan is a **material downgrade** when:



Higher rating numbers mean worse credit quality (1 = best, 8 = worst).
Include every loan meeting this threshold in the material_downgrades list.

---

## Rating Migration

Migration tracks loans whose rating **changed** after regrade. Group by
final_rating and list included loan_ids ascending within each group.

A loan whose rating stays the same after regrade is NOT included in the
migration list (it did not migrate).

---

## Watch-List Action Assignment

Assign recommended actions based on the combination of final risk rating
and payment status. Use the table below when policy is silent; when policy
provides an explicit mapping, use the policy version.

| Final Rating | Payment Status | Recommended Action |
|-------------|---------------|-------------------|
| 8 | Nonaccrual | partial_chargeoff_review |
| 8 | Any other | legal_referral |
| 7 | Nonaccrual, 90+ Days Past Due | special_assets |
| 7 | Current, 30 Days, 60 Days | special_assets |
| 6 | Nonaccrual, 90+ Days Past Due | special_assets |
| 6 | Current, 30 Days, 60 Days | watchlist |
| 5 | Nonaccrual, 90+ Days Past Due | special_assets |
| 5 | Current, 30 Days, 60 Days | watchlist |
| 4 | 90+ Days Past Due, Nonaccrual | workout |
| 4 | Current, 30 Days, 60 Days | monitor |
| 3 | Any | monitor |

**Projected loss**: When the CDFI risk class is "Projected Loss" or the
loan is nonaccrual with a rating of 7 or worse, set .

The controlled action vocabulary is:
, , , , , 

---

## Reason Code Assignment

Assign reason codes from the template-controlled vocabulary. Multiple reasons
can apply to a single declined application.

### Common Triggers

| Condition | Reason Code |
|-----------|------------|
| remaining_capacity < requested_amount after higher-priority approvals | capacity_limit |
| post_approval_pct > limit_pct (over sector limit) | sector_breach |
| base DSCR or stressed DSCR below policy floor | weak_dscr |
| LTV above policy maximum | high_ltv |
| FICO/credit score below policy minimum | low_fico |
| Applicant has recent bankruptcy flag | recent_bankruptcy |
| Business age under policy startup threshold | startup_risk |
| Collateral value less than loan amount | underwater_collateral |
| Policy floor not met (generic catch-all) | policy_floor_missing |
| Required documentation incomplete | documentation_gap |
| Branch NPA or delinquency materially worse than FDIC benchmark | fdic_adverse_variance |
| Segment metrics materially worse than NCUA peers | ncua_peer_weakness |

When multiple reasons apply, list them sorted alphabetically.

---

## Posture Assessment (Credit Union Segments)

Assess segment posture by combining capacity and external risk:

| Capacity | External Risk | Posture |
|----------|--------------|---------|
| capacity_available | stronger_than_national_and_peers | continue_with_standard_conditions |
| capacity_available | mixed_vs_national_and_peers | continue_with_standard_conditions |
| capacity_available | weaker_than_national_and_peers | continue_with_tighter_conditions |
| capacity_constrained | stronger_than_national_and_peers | continue_with_tighter_conditions |
| capacity_constrained | mixed_vs_national_and_peers | pause_unless_strategic |
| capacity_constrained | weaker_than_national_and_peers | pause_until_state_metrics_recover |
| no_capacity | any | pause_until_state_metrics_recover |

Capacity comes from segment-level lending limits vs. current utilization.
External risk comes from comparing segment state metrics against national
NCUA benchmarks and peer state medians.

---

## Priority Ranking

When the template requires a priority ranking of applications, rank by a
compound view of credit quality and strategic fit. Do not use a single field.
Consider:

1. CDFI score (lower is better)
2. DSCR strength (higher is better)
3. Exposure size (larger may be higher priority for strategic relationships)

Rank approved and conditionally-approved applications only.
