# Aggregate and summary math

The summary/aggregate block is deterministic — every field is derived from the issue list or the
source tables. Compute it last, after the per-issue rows are settled. The two recurring ambiguities
(and the safe conventions) are below.

## Counts

- `issue_count`, `position_issue_count` = number of rows in the issue register / position matrix
  you produced.
- `high_risk_count` / `medium_risk_count` / `risk_counts.{HIGH,MEDIUM,LOW}` = counts by
  `risk_rating`.
- `business_outcome_count` = count of distinct `business_outcome` values used (dedup).
- `out_of_policy_issue_count`, `draft_below_playbook_count`, `missing_required_term_count` =
  counts by `issue_status` / `status`.
- `closing_blocker_count` = number of rows in `closing_blockers` (after de-dup, see below).
- `required_closing_consent_count` = count of consents with `required_for_closing == "yes"`.

Build counts **from the rows you actually emitted**, so they can never disagree with the register.

## Dollar aggregates

- `headline_value_dollars` / `headline_purchase_price_usd` = `deal.headline_value`.
- `indemnity_cap_shortfall_to_fallback_usd` = `fallback_amount − draft_amount` (≥ 0).
- `indemnity_cap_shortfall_to_preferred_usd` = `preferred_amount − draft_amount` (≥ 0).
- `rtf_excess_amount` = `draft_amount − threshold_amount` for an over-threshold RTF (≥ 0).
- `total_negotiation_delta_dollars` = Σ of per-issue `delta_to_fallback_dollars` /
  `shortfall_to_fallback_usd`. Sum each issue's dollar gap once; do **not** re-add a fee that is
  already the same issue's shortfall.
- `required_consent_amount_at_risk_usd` / `required_closing_consent_amount_at_risk_dollars` =
  Σ `amount_at_risk` over consents with `required_for_closing == "yes"`.
- `material_contract_revenue_requiring_consent_usd` / `material_contract_revenue_conditioned` =
  Σ `annual_revenue` over material contracts with `consent_required == "yes"`.
- `total_employee_count` / `continuing_employee_count` = Σ `count`.
- `total_pto_liability_dollars` / `employee_pto_liability_total` = Σ `pto_liability`.

## Quantified exposure — the exposure-component convention

Two readings of "total quantified exposure" appear; pick by what the template asks and **always
state the included components** so the convention is auditable:

1. **Distinct-risk-estimate sum (preferred for committee/aggregate memos):** sum the
   `exposure_low`/`exposure_high` of each **distinct** risk-estimate category you include
   (e.g. closing-certainty + indemnity-leakage), excluding categories you're not scoring
   (transition disruption for a non-carveout). Each estimate is counted **once**, regardless of how
   many issues cite it. Record the included ones in `included_exposure_components` and the rest in
   `excluded_exposure_components`.
2. **Per-issue exposure (used inside an issue's `exposure` block):** the single risk estimate that
   matches that issue's economic type.

Do not sum the same risk estimate once per issue into the aggregate — that double-counts. If a
template's aggregate field is ambiguous, the distinct-category sum is the defensible default.

## Total modeled exposure (deviation-matrix style)

`total_modeled_exposure_low_usd` / `_high_usd` = Σ over the risk-estimate categories the package
models (typically all three: closing certainty + indemnity leakage + transition disruption), low
and high separately. `highest_modeled_exposure_category` = the category with the largest
`exposure_high`.

## Priority / negotiation ordering

Order issue IDs highest-leverage first. Reliable ordering heuristic:

1. Termination economics and financing/closing-blocker issues (RTF, financing condition,
   fiduciary out, customer-consent termination right, HSR) — these can kill the deal.
2. Indemnity cap / escrow / survival / materiality scrape — large dollar exposure.
3. Structural protective terms the deal type requires (Section 1060, transfer tax, IP transition,
   TSA, outside date, governing law).
4. Employee/PTO/service-credit — smaller dollar, operational.

Within a tier, larger quantified dollar impact ranks higher. If the template gives an explicit
`ordering` rule (e.g. "sort by `issue_id` ascending"), follow that instead for the array it
governs, and use the leverage ordering only for fields labeled `priority_order`.

## De-duplicating blockers / consents

One customer relationship often appears as both a consent (`CNS_…`) and a material contract
(`MAT_…`) — the Apex Master Commercial Agreement is the recurring example. To avoid
double-counting in `closing_blocker_count` and revenue/amount aggregates:

- Count the consent's `amount_at_risk` once (under the consent), and the contract's
  `annual_revenue` once (under the material-contract aggregation).
- In the `closing_blockers` list you may represent the relationship as one `required_consent`
  blocker (citing the consent id, with `related_contract_id` pointing at the mat-contract) **or**
  as separate consent + material-contract blockers — but keep `closing_blocker_count` consistent
  with the list length, and never let the same dollar amount inflate a sum twice.
- `non_blocking_notices` / `excluded_contract_ids` hold the `notice only` contracts (e.g. the Core
  Platform License).
