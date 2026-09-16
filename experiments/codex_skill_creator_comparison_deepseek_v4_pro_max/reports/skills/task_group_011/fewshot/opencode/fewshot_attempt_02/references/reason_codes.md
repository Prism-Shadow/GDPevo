# Reason Codes and Action Rules

This reference maps policy violations and risk conditions to the controlled
enum values used in answer templates. Always use exactly the enum strings
listed; do not invent variations.

## Decline Reason Codes

Assign these codes when declining an application. Multiple codes may apply;
list them sorted alphabetically.

| Code | Condition |
|------|-----------|
| `capacity_limit` | Remaining lending capacity insufficient to cover the requested amount. |
| `sector_breach` | Post-approval sector concentration exceeds the limit_pct for that sector and no mitigation was accepted. |
| `weak_dscr` | DSCR is below 1.05 (or null); insufficient repayment coverage. |
| `high_ltv` | LTV exceeds 1.00 (or null); collateral does not cover the loan. |
| `low_fico` | FICO score below 580 (or null) with no compensating factors. |
| `recent_bankruptcy` | Applicant has a bankruptcy within the lookback period. |
| `startup_risk` | years_in_business < 3 and no SBA guaranty or strong co-guarantor. |
| `underwater_collateral` | collateral_value < requested_amount and LTV > 1.00. |
| `policy_floor_missing` | Required policy minimums not met (documentation, guarantor, or rate floor). |
| `documentation_gap` | documentation_complete is 0/false and the gap is material. |
| `fdic_adverse_variance` | Branch delinquency or NPA ratio substantially exceeds the FDIC benchmark (variance > 10 bps adverse). |
| `ncua_peer_weakness` | NC state metrics are directionally worse than both national and peer median on key dimensions. |

## Watch-List Action Assignment (Rating Migration)

Assign a recommended_action to each loan in the watch-list coverage scope:

| Conditions | Action |
|------------|--------|
| final_rating == 8, any payment_status | `partial_chargeoff_review` |
| final_rating == 7, payment_status in (90+DPD, Nonaccrual) | `special_assets` |
| final_rating == 7, payment_status Current | `special_assets` |
| final_rating == 6, any payment_status | `watchlist` |
| final_rating == 5, payment_status 60+DPD | `watchlist` |
| final_rating in (3, 4), payment_status 30+DPD | `monitor` |

## Workout Queue Action Assignment (Watch-List Stress)

Assign a recommended_action based on risk_class and payment_status:

| Risk Class | Payment Status | Action |
|------------|---------------|--------|
| Projected Loss | any | `partial_chargeoff_review` |
| Watch | Nonaccrual | `workout` |
| Watch | 90+ Days Past Due | `special_assets` |
| Watch | Current or 30/60 DPD | `special_assets` |
| Doubtful | any | `special_assets` |
| Satisfactory | 90+ Days Past Due | `special_assets` |
| Satisfactory | Current or 30/60 DPD | `watchlist` |
| Desirable | 90+ Days Past Due | `special_assets` |
| Desirable | Current or 30/60 DPD | `watchlist` |
| Prime | 90+ Days Past Due | `special_assets` |
| Prime | Current or 30/60 DPD | `watchlist` |

## Concentration Flag Handling

| Situation | Handling |
|-----------|----------|
| post_approval_pct > limit_pct, participation mitigates | `participation_required` |
| post_approval_pct > limit_pct, no participation available | `decline` |
| post_approval_pct <= limit_pct but close (< 0.02 margin) | `conditional_approve` |
| post_approval_pct <= limit_pct comfortably | `approve` or `none` |

## Competing CRE Unselected Reason Codes

When one CRE application is selected over the other, the unselected reason
codes must come from this set:

| Code | Meaning |
|------|---------|
| `sector_breach` | The unselected application worsens a sector already at or above its concentration limit. |
| `weak_dscr` | The unselected application's DSCR is lower and/or breaches the stress threshold. |
| `high_ltv` | The unselected application's LTV is materially worse. |
| `fdic_adverse_variance` | The branch's CRE delinquency significantly exceeds the FDIC benchmark. |

## CRE Conditions

Assign from the template's conditions enum. Standard minimum set:

- `committee_cre_exception` — Required when CRE concentration exceeds policy limit.
- `minimum_dscr_covenant_1_25` — Required when stressed DSCR is near 1.0 or CRE concentration is elevated.
- `quarterly_financial_reporting` — Standard for all CRE approvals.
- `no_additional_cre_without_committee_review` — Standard when CRE concentration is above the policy limit.

Additional conditions based on property/borrower characteristics:

- `tenant_roll_and_lease_review` — Multi-tenant CRE or property with lease renewal risk.
- `updated_appraisal_before_close` — When collateral is aged or LTV is borderline.
- `bank_retained_exposure_cap` — When participation is used, cap the bank's retained exposure.

Sort conditions alphabetically in the output.

## Application Decision Logic

For the allocation archetype, determine each application decision:

1. Check capacity: if remaining_capacity < requested_amount, tentative decline for `capacity_limit`.
2. Check sector concentration: if post_approval_pct > limit_pct, check for mitigations
   (participation, reduced_amount, board_exception). If no mitigation available, decline
   for `sector_breach`.
3. Check DSCR: if below 1.05, decline for `weak_dscr` (unless SBA guaranty compensates).
4. Check LTV: if > 1.00, decline for `high_ltv`.
5. Check FICO: if < 580 and null, decline for `low_fico`.
6. Check startup risk: if years_in_business < 3, require SBA or strong co-guarantor.
7. If all checks pass -> `approve`.
8. If some checks fail but mitigations exist -> `conditional_approve` with appropriate conditions.
9. If application is viable but capacity is tight -> `defer` to next quarter.

## Escalation Trigger Mappings (Credit Union)

| trigger_id | condition | owner |
|------------|-----------|-------|
| ET001 | `segment_recent_delinquency_ge_90_bps` | `credit_risk_manager` |
| ET002 | `missing_insurance_or_lien_exception` | `operations_control_manager` |
| ET003 | `quarterly_capacity_exceeded_or_exception_requested` | `lending_committee_chair` |
| ET004 | `state_delinquency_gap_widens_25_bps` | `credit_risk_manager` |

Standard triggers for segment posture: ET001, ET002, ET003. Add ET004 when
NC delinquency_bps exceeds both US and peer median by a widening margin.
