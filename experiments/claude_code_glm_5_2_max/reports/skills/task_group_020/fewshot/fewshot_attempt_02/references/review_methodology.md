# Review Methodology

How to turn workbench data into a template-conforming JSON deliverable. The answer_template.json is always authoritative for field names, enums, units, precision, and ordering — what follows is the reasoning that fills those fields.

## 1. Scope: what to include vs. exclude

- Include: draft terms that are out of policy, restricted, or deviate from the playbook (above or below the fallback), and required protective terms that are **absent** from the draft when the deal data shows they are needed.
- Exclude distractors unless the template asks for them:
  - **stale** terms (`staleness_flag` set),
  - terms that are **in policy / at the preferred position** (action `accept`),
  - terms **outside the requested scope** (e.g. a committee-escalation task excludes non-committee categories; a transition review excludes non-transition categories).
- When the template has an `excluded_in_policy_terms` / `excluded_in_policy_categories` field, list what you left out there; otherwise just omit.

## 2. Classify each issue

### issue_status (and equivalent `status` fields)
- `missing_required_term` — playbook/policy requires an affirmative term and the draft is silent or the term is absent. Set `source_term_ids: []` (or the template's equivalent). Action `add`.
- `draft_exceeds_playbook` — term is present but drifted **against** the seller (more buyer-friendly than the seller's fallback). Typical seller-side framing. Action `revise` (or `delete` if the term should not exist at all, e.g. a buyer financing condition).
- `draft_below_playbook` — term is present but **below** the buyer's required position (more seller-friendly than the buyer's fallback). Typical buyer-side framing. Action `revise`.
- `out_of_policy` — term crosses a policy threshold or is in a restricted category; requires committee routing. Action `escalate` / `approve_with_conditions` / `reject`.
- `in_policy` — term meets or beats the preferred position. Action `accept`. (Usually excluded from the register, but a deviation-matrix template may list it.)

### risk_rating (LOW / MEDIUM / HIGH)
Start from the rule's `risk_default`. Adjust upward when: the deal-specific `risk-estimates` exposure is material; the term affects closing certainty or indemnity exposure; a restricted/policy category is involved; customer-concentration or employee-count magnitude is high. Adjust downward only when exposure is clearly immaterial.

### recommended_action / redline_action / required_action
Use only the template's allowed enum. The action follows from the status: `add` (missing), `revise` (present but off), `delete` (term should not exist), `accept` (in policy), `escalate` / `approve` / `approve_with_conditions` / `reject` (committee routing).

### Affirmative position fields
Templates name these differently — `required_position_code`, `final_position`, `must_have_terms`, `required_position_normalized`, `required_position`. State the concrete position your side requires (the fallback, or preferred if achievable), drawn from the playbook `preferred_position` / `fallback_position` or the policy `policy_standard`. Encode limits precisely (e.g. non-compete months max, escrow release months, fee model, tax-allocation method, transfer-tax split).

## 3. Quantify

### Base for dollar math
Default base = the deal's `headline_value`. Use a different base only when a source explicitly states one — e.g. an RTF measured on **equity value**, an escrow measured on **upfront_cash**, or an indemnity cap measured on **purchase price**. The `basis` field on the term/rule/threshold tells you which. When the template carries a `value_basis` / `basis` field, echo it.

```
amount_usd = round_to_integer( percent_value × base )
```

- Currency: **integer USD** (round, do not truncate unless the template says to).
- Percent fields: decimals at the template's precision (1 dp, 2 dp, or whole percent — follow the template). Note: percent **values** in inputs are sometimes fractions (e.g. `fully_diluted_pct` 0.341 = 34.1%); convert to the unit the template wants before emitting.
- Months: integers.
- Dates: `YYYY-MM-DD`.
- Holder allocations: `fully_diluted_pct` typically to four decimals.

### Negotiation gaps
- `delta_to_fallback_*` — the gap between the **draft** position and the **fallback** position, in the unit named by the field (`_dollars`, `_months`, `_percent`). It is the amount still to be negotiated to reach the fallback. For a seller whose draft drifted too far (draft exceeds playbook), it is `draft − fallback`; for a buyer whose draft is too low (draft below playbook), it is `fallback − draft`. Use the absolute gap that represents what must move.
- `shortfall_*` — the gap when the draft falls **short of a required minimum**: `required − draft` (e.g. a reverse break fee of 0% vs a required 6% → shortfall = 6% and its dollar equivalent).
- `delta.percent_points` / `delta.amount` / `delta.fundamental_months` / `delta.general_months` / `delta.excess_count` / `delta.removed_triggers` — fill the delta sub-object the template defines, in the unit(s) that apply to that category.

### Exposure
- Pull `exposure_low` / `exposure_high` from `risk-estimates` by matching `category`. Cite the `estimate_id` as `source_estimate_id`.
- If no estimate exists for a category, use `type: "not_quantified"`, `low: 0`, `high: 0`, `source_estimate_id: "not_applicable"` (only when the template allows it).

### Benchmarks
- Match `benchmarks` by `category`/`metric`. Emit `sample_size`, `median`, `upper_quartile` (map `median_value` / `upper_quartile`).
- Classify `position`:
  - value ≤ median → `at_or_below_median`;
  - median < value ≤ upper_quartile → `between_median_and_upper_quartile`;
  - value ≈ upper_quartile → `at_upper_quartile`;
  - value > upper_quartile → `above_upper_quartile`;
  - no benchmark applies → `not_applicable` (with zeros / `not_applicable` for the metric).

## 4. Prioritize

Order issues from **highest negotiation priority to lowest**. Priority is driven by:
1. closing-certainty impact (financing conditions, reverse break fees, regulatory/HSR, required consents) — typically highest;
2. indemnity exposure magnitude (cap, basket, survival, escrow);
3. then employee transition, restrictive covenants, tax allocation, governing law.

Within similar impact, higher `risk_rating` ranks first. If the template specifies a different ordering (e.g. "sort by issue_id ascending"), follow the template — but `priority_order` / `priority_rank` / `negotiation_priority` fields are explicitly priority-driven, not alphabetical.

## 5. Aggregate and reconcile

Every aggregate field must reconcile with the line items. Concretely:

- `issue_count` / `position_issue_count` / `escalated_term_count` = length of the issue/term list.
- `high_risk_count` / `medium_risk_count` / `low_risk_count` (and `risk_counts`) = counts by `risk_rating`.
- `out_of_policy_issue_count`, `draft_below_playbook_count`, `missing_required_term_count`, `draft_exceeds_playbook_count` = counts by `issue_status`/`status`.
- `closing_blocker_count` = length of the `closing_blockers` list.
- `total_negotiation_delta_dollars` = Σ `delta_to_fallback_dollars` over the quantified issues (the ones with a dollar delta).
- `total_quantified_exposure_low_dollars` / `_high_dollars` (and `aggregate_quantified_exposure_low` / `_high`, `total_modeled_exposure_low_usd` / `_high_usd`) = Σ `exposure.low` / Σ `exposure.high` over the **quantified** (non-`not_quantified`) terms only.
- `required_consent_amount_at_risk_*` = Σ `amount_at_risk` over consents with `required_for_closing`.
- `material_contract_revenue_requiring_consent_*` (or `material_contract_revenue_conditioned`) = Σ `annual_revenue` over material contracts where consent is required.
- `total_employee_count` = Σ employee `count`; `total_pto_liability_dollars` = Σ `pto_liability`.
- `headline_value_dollars` / `headline_purchase_price_usd` = the deal `headline_value`.
- `indemnity_cap_shortfall_to_fallback_usd` / `_to_preferred_usd` = the cap issue's `shortfall_to_fallback_usd` / `shortfall_to_preferred_usd`.
- `rtf_excess_amount` = the reverse-termination-fee term's `delta.amount`.
- `highest_modeled_exposure_category` = the category contributing the largest exposure (by high estimate).
- Excluded components (e.g. `transition_disruption`) are listed in `excluded_exposure_components` and **not** summed into the aggregate.

If a count does not reconcile, re-check the line items before emitting.

## 6. Closing readiness & blockers

When the template has a `closing_readiness` / `closing_blockers` / `operational_risk` block:

- A **blocker** is anything that must be satisfied before closing: a required consent (`required_for_closing`), a regulatory clearance (HSR/industry), or a material-contract consent. List each with its stable id, `blocker_type`, `risk_rating`, and `amount_at_risk`/`annual_revenue`.
- `overall_status` (`READY` / `READY_WITH_CONDITIONS` / `NOT_READY`) and `overall_risk_rating`: `NOT_READY`/`HIGH` when any HIGH-risk blocker or out-of-policy indemnity term is open; `READY_WITH_CONDITIONS` when only tradable/conditionable items remain; `READY` when all blockers are resolved.
- Separate **blockers** (must fix before signing/closing) from **tradeable issues** (negotiable, non-blocking) into the template's `blocker_ids` vs `tradeable_issue_ids` (or `closing_blockers` vs the non-blocking list).
