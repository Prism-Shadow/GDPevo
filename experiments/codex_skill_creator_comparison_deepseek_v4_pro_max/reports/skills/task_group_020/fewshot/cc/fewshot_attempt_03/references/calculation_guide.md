# Calculation Guide

Dollar amounts, percentages, exposure ranges, and employee data must
follow these rules.  They apply to every task type unless the answer
template explicitly overrides one of them.

## Base value

Every dollar amount is derived from the headline purchase price in the
deal record (`GET /api/deals/<deal_id>`) unless a workbench record
explicitly states a different basis.

Accepted alternative bases:
- **Equity value** — used for public-company reverse-termination fees
  and committee-policy thresholds when the policy states "equity value."
- **Upfront cash** — used for escrow when the deal has both cash and
  stock consideration and the escrow provision references upfront cash
  rather than total purchase price.
- **Identified findings** — used when a diligence finding specifies a
  quantified exposure amount that feeds directly into a term.

When neither the deal record nor any term record provides a value,
leave the field `null`.  Do not estimate.

## Percentage arithmetic

Percent values are stored as decimal numbers in percent points (not as
ratios).  `12.5` means 12.5%, not 0.125.

### Computing dollar amounts from percentages

```
dollar_amount = (percent / 100) * base_value
```

Round to the nearest integer.  For example, at a $500M headline price
with a 15% escrow:

```
15 / 100 = 0.15
0.15 * 500000000 = 75000000
```

### Delta and shortfall

```
delta_to_fallback_dollars = draft_amount_dollars - fallback_amount_dollars
```

For seller-side: positive delta means the draft is worse than fallback
(you need to reduce it).  Negative delta means the draft is better than
fallback (you are in an acceptable position).

For buyer-side: positive shortfall means the draft is below what the
buyer needs (you need to increase it).

```
shortfall_to_fallback_usd = fallback_amount_usd - draft_amount_usd
```

When the draft has no provision (missing required term), the draft
amount is 0 and the shortfall equals the full fallback amount.

### Percentage deltas

```
percent_delta = draft_percent - policy_threshold_percent
```

For survival/month deltas:

```
month_delta = draft_months - fallback_months
```

Positive means draft exceeds fallback (bad for seller; potentially
acceptable for buyer if the extra months are within policy).

## Exposure ranges

When the template requires low/high exposure ranges, derive them from
risk estimates:

- **Low exposure**: The estimate's `low` field.
- **High exposure**: The estimate's `high` field.

For terms without risk estimates, exposure is `not_quantified` and both
low and high are 0.

To aggregate across issues:

```
total_quantified_exposure_low = sum(issue.exposure.low for issues with "closing_certainty" or "indemnity_leakage")
total_quantified_exposure_high = sum(issue.exposure.high for same)
```

Only include the exposure components the template or task specifies.
The aggregate summary should list both included and excluded components.

## Employee data

Employee counts, PTO liabilities, and service-credit requirements come
from `/api/deals/<deal_id>/employees`.

- **Employee count**: Count continuing employees (those being
  transferred or retained).  If the task splits employees by group
  (field vs. corporate), count only the relevant group.
- **PTO liability**: Sum PTO liabilities across the relevant employee
  group.  Use integer dollars.
- **Service credit**: Mark `true` when the playbook requires service
  credit for continuing employees and the draft is missing or
  insufficient.
- **WARN risk**: Flag employees with WARN exposure when the playbook
  mentions WARN Act compliance.

## Consent and contract amounts

- **Amount at risk** for a consent: from the consent record's value.
- **Annual revenue** for a material contract: from the contract record.
- **Required consent count**: only count consents whose
  `condition_type` is `closing_condition`, not `notice_only` or
  `post_closing_covenant`.
- **Non-blocking notices**: consent or contract IDs with
  `condition_type` of `notice_only` or similar non-blocking types.

## Exposure aggregation

The template usually requires these aggregate fields.  Compute them
from the issue register, not from raw workbench data:

- `issue_count`: total number of issues in the register.
- `high_risk_count`: issues with `risk_rating` of `HIGH`.
- `medium_risk_count`: issues with `risk_rating` of `MEDIUM`.
- `business_outcome_count`: distinct business outcomes across all issues.
- `headline_value_dollars`: from the deal record.
- `total_quantified_exposure_low_dollars`: sum of low exposures.
- `total_quantified_exposure_high_dollars`: sum of high exposures.
- `total_negotiation_delta_dollars`: sum of all `delta_to_fallback_dollars`
  values in the issue register.
- `required_closing_consent_count`: count of consent closing conditions.
- `total_employee_count`: count of continuing employees.
- `total_pto_liability_dollars`: sum of PTO liabilities.

Additional fields the template may require:

- `closing_blocker_count`: count of distinct blocking items.
- `required_consent_amount_at_risk_usd`: sum of amounts at risk for
  required-consent blockers.
- `material_contract_revenue_requiring_consent_usd`: sum of annual
  revenue for material contracts requiring consent.
- `indemnity_cap_shortfall_to_fallback_usd`: from the indemnity cap issue.
- `indemnity_cap_shortfall_to_preferred_usd`: from the indemnity cap issue.
- `total_modeled_exposure_low_usd` / `total_modeled_exposure_high_usd`:
  sum of all quantified exposure estimates, including special indemnity
  and privacy findings when the template includes them.
- `highest_modeled_exposure_category`: the business outcome with the
  largest high exposure value.

## Months arithmetic

Months are always integers.  Draft months come from the draft term;
playbook months come from playbook rules.

```
delta_to_fallback_months = draft_months - fallback_months
```

When the draft is silent (missing required term), `draft_months` is
`null` and the delta is the negative of the fallback (for buyer shortfall
calculations) or computed implicitly.  Use `null` when the template
permits it.

## Edge cases

- **Zero-value terms**: When a draft term explicitly sets a value to 0
  (e.g., reverse break fee at 0%), use `0` not `null`.  The delta is the
  full fallback amount.
- **Missing provisions vs. explicit silence**: When the API returns no
  term record for a required item, treat it as missing.  When the API
  returns a term record with no numeric value and the playbook requires
  one, treat it as missing.
- **Excluded/distractor terms**: The escalation memo task explicitly
  says to exclude in-policy and non-committee terms.  When other tasks
  have terms that are in-policy, you may include them in the issue
  register with `in_policy` status or exclude them, depending on what
  the template requires.  Read the template's `required_output_shape`
  and `possible_issue_ids` to decide.
- **Holder allocation**: Derive cash and stock amounts from the
  holder's fully-diluted percentage applied to the upfront cash and
  stock value respectively.  When the cap table gives shares, compute
  per-share consideration and multiply.
