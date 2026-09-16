# Business Patterns

Reusable logic for M&A deal-workbench analysis tasks. Apply these patterns after gathering all API data and before building the output JSON.

## Computation Rules

### Dollar Amounts

Compute dollar amounts from the deal's headline purchase price (`deal.headline_purchase_price`):

```
draft_amount = headline_purchase_price * (draft_percent / 100)   # round to integer
preferred_amount = headline_purchase_price * (preferred_percent / 100)   # round to integer
fallback_amount = headline_purchase_price * (fallback_percent / 100)   # round to integer
delta_to_fallback = draft_amount - fallback_amount
```

When a term explicitly states a dollar amount that differs from the headline-based computation, use the explicit value. When a risk estimate or finding specifies a dollar amount, use it directly. When the basis is upfront_cash or a subset of purchase price, derive from the corresponding deal record field.

### Fee Percent and Shortfall

```
required_fee_dollars = headline_purchase_price * (required_fee_percent / 100)
shortfall_dollars = required_fee_dollars - draft_amount (which may be zero if absent)
```

### PTO Liability

Sum `pto_accrued_dollars` from relevant employee records.

### Employee Counts

Count employees by filtering on applicable fields (continuing status, group membership, WARN risk).

## Playbook Comparison

### Process

1. Load playbook rules from `/api/playbooks/<playbook_id>/rules`.
2. Load draft terms from `/api/deals/<deal_id>/terms`.
3. For each playbook rule, find the matching draft term by category or label.
4. Compare draft values against playbook `preferred` and `fallback` targets.

### Status Classification

| Condition | issue_status |
|-----------|-------------|
| Draft term present and values match or are within playbook range | `in_policy` |
| Draft term present but exceeds playbook preferred/fallback bounds | `draft_exceeds_playbook` |
| Draft term present but falls below playbook preferred/fallback bounds | `draft_below_playbook` |
| Playbook requires term but draft is silent/absent | `missing_required_term` |
| Playbook requires term and supporting data shows need, but draft is absent | `missing_required_term` |

### Value Ranges

- For percentages and months: `draft > fallback` is out_of_policy; `draft < fallback` is draft_below_playbook.
- For boolean requirements (service credit, hell-or-high-water, field selection): presence/absence comparison.
- For text fields (governing law, forum, tax allocation method): exact match against playbook preferred.

## Policy Threshold Comparison

### Process

1. Load policy thresholds from `/api/policies/<policy_id>/thresholds`.
2. Load draft terms.
3. Compare draft metric values against policy threshold values.
4. Mark terms exceeding thresholds as `out_of_policy`. Exclude in-policy terms from escalation.

### Delta Calculation

For numerical thresholds:
```
delta.percent_points = draft.value - policy.threshold_value
delta.amount = draft.amount - policy.threshold_amount
```

For text/category thresholds (carveouts, triggers):
- Count draft additions beyond policy-approved list.
- Identify which required triggers are missing.

### Benchmark Positioning

Classify draft values against benchmark quartiles from `/api/deals/<deal_id>/benchmarks`:

| Draft value range | position |
|-------------------|----------|
| <= median | `at_or_below_median` |
| > median and <= upper_quartile | `between_median_and_upper_quartile` |
| == upper_quartile | `at_upper_quartile` |
| > upper_quartile | `above_upper_quartile` |
| No benchmark data available | `not_applicable` |

## Risk Classification

| Signal | Risk Rating |
|--------|------------|
| Closing certainty blocker, buyer termination right, or deal-break exposure | `HIGH` |
| Indemnity exposure with large delta (>10% of purchase price), missing escrow, or consent condition at risk | `HIGH` |
| Missing required regulatory condition (HSR) | `HIGH` |
| Employee transition issues with material PTO liability | `HIGH` |
| Missing restrictive covenants where needed | `HIGH` |
| Modest indemnity or survival delta, missing secondary tax/governing-law terms | `MEDIUM` |
| Draft matches playbook or only minor deviation | `LOW` |
| Notice-only or post-closing items | `LOW` |

## Priority Ordering

Order issues from highest negotiation priority to lowest. Apply these factors in order:

1. **Closing certainty**: regulatory conditions, consent conditions that could block closing, financing conditions.
2. **Quantified exposure**: larger dollar deltas rank higher.
3. **Risk rating**: HIGH before MEDIUM before LOW.
4. **Business outcome group**: closing_certainty > employee_transition > indemnity_exposure > escrow_economics > restrictive_covenants > tax_allocation > governing_law.

## Closing Blocker Identification

A record is a closing blocker when it:

- Is a consent with `condition_type: "closing_condition"` and a positive `amount_at_risk`.
- Is a material contract with `condition_type: "closing_condition"`.
- Is a regulatory record where `hsr_required: true` and no HSR clearance condition exists in draft terms.

Tradeable issues are those with non-zero risk but where draft terms already provide partial coverage or the item can be resolved post-closing.

## Holder Allocation (Stock Purchase)

When the template requires holder-level consideration allocation:

1. Load cap table from `/api/deals/<deal_id>/cap-table`.
2. Compute per-holder amounts: `cash_amount = upfront_cash * fully_diluted_pct`, `stock_amount = stock_value * fully_diluted_pct`.
3. Total consideration = cash_amount + stock_amount. Round to integer dollars.

## Missing Term Detection

A term is missing from the draft when:

- The playbook or policy requires it (check `required` field or the rule's presence implies it).
- Supporting data shows a material need (e.g., HSR is required in regulatory records but no HSR covenant term exists; employees exist but no employee continuity term exists).
- The template's `possible_issue_ids` or `stable_issue_ids` includes it and the task description covers that category.

When a term is missing, set `source_term_ids` to an empty array. Derive all needed values from playbook rules, supporting records, or computed from the purchase price.
