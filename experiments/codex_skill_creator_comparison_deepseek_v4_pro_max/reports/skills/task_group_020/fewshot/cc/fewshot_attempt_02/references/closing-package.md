# Closing & Economics Package Reference

Use this reference when the prompt asks for a **buyer-side SPA closing and economics package** covering consideration allocation, indemnity, escrow, working capital, consents, covenants, regulatory, and closing readiness.

## Data Sources

Pull in parallel:

1. `/api/deals/<id>` — headline value, upfront cash, stock, milestone, deal structure
2. `/api/deals/<id>/terms` — indemnity cap, survival, escrow, NWC terms
3. `/api/deals/<id>/cap-table` — holders, security classes, fully diluted percentages, share counts
4. `/api/playbooks/<playbook_id>/rules` — buyer playbook (e.g., `PB_BUYER_A`)
5. `/api/deals/<id>/consents` — every consent record with risk and counterparty
6. `/api/deals/<id>/material-contracts` — contract IDs, names, annual revenue
7. `/api/deals/<id>/employees` — continuing count, service-credit employees, PTO liability, WARN risk
8. `/api/deals/<id>/regulatory` — HSR requirement, threshold basis, hell-or-high-water
9. `/api/deals/<id>/diligence-findings` — NWC findings, special indemnity findings, privacy findings
10. `/api/deals/<id>/risk-estimates` — quantified risk ranges

## Holder Allocation

For each holder group from the cap table:

- **cash_amount**: `round(upfront_cash * fully_diluted_pct)` — distribute only the upfront cash proportionally by fully diluted percentage.
- **stock_amount**: `round(stock_value * fully_diluted_pct)` — distribute stock consideration the same way.
- **total_consideration**: `cash_amount + stock_amount`.
- **fully_diluted_pct**: expressed as a decimal (e.g., `0.185` for 18.5%), to four decimal places.

Milestone value goes to `0` unless the deal record explicitly structures milestone payments.

## Indemnity Package

Compare the draft cap and survival terms against the buyer playbook:

- **draft_cap_pct**: from the draft term, in percent points.
- **buyer_preferred_cap_pct / buyer_preferred_cap_amount**: from playbook preferred. `buyer_preferred_cap_amount = round(headline_value * buyer_preferred_cap_pct / 100)`.
- **buyer_fallback_cap_pct / buyer_fallback_cap_amount**: from playbook fallback. `buyer_fallback_cap_amount = round(headline_value * buyer_fallback_cap_pct / 100)`.
- **draft_survival_months**: from the draft term.
- **buyer_preferred_survival_months**: from playbook.
- **fallback_survival_with_escrow_months**: the fallback survival when tied to escrow release.
- **materiality_scrape_required**: check the draft scrape clause against the buyer playbook. `FULL_BREACH_AND_DAMAGES` when buyer requires full scrape; `BREACH_ONLY` when buyer accepts breach-only; `NONE` when no scrape is needed.
- **risk_rating**: HIGH when draft cap is well below fallback; MEDIUM when it is at or near fallback.

## Escrow

Buyer-side escrow defaults to at least 10% of purchase price with release at survival expiration:

- **basis**: `purchase_price` (headline value), `upfront_cash`, or `identified_findings`.
- **required_pct**: from playbook fallback, typically 10.0.
- **amount**: `round(headline_value * required_pct / 100)`.
- **release_months**: survival fallback months (tied to general rep survival).
- **release_trigger**: `general_rep_survival_expiration`.
- **status**: `required_buyer_fallback` when the draft lacks escrow entirely.

## NWC Adjustment

Check diligence findings for NWC risk. When a finding exists:

- **required**: `true`.
- **mechanic**: `dollar_for_dollar_outside_collar`.
- **collar_amount**: from the finding or playbook.
- **source_finding_id**: the finding ID from `/api/deals/<id>/diligence-findings`.
- **status**: `add_closing_mechanic`.

## Consents and Material Contracts

Distinguish three categories:

1. **Required closing consents** (`closing_condition`): consents whose absence would block closing. Include amount_at_risk and risk_rating per consent.
2. **Material contract conditions**: contracts requiring counterparty consent that tie to material revenue. Report annual_revenue per contract.
3. **Non-blocking notices**: consent or contract IDs that require notice only, not a closing condition.

Non-blocking items go in `non_blocking_notices` as an array of source IDs.

## Employment Covenants

- **continuing_employee_count**: total employees flagged as continuing.
- **service_credit_employee_ids**: IDs of employees for whom service credit is a concern.
- **pto_liability_total**: sum PTO liability across all employees.
- **warn_risk_employee_ids**: IDs of employees with WARN Act risk.
- **required_action**: `revise_service_credit_and_pto` when the draft is silent or inadequate.

## Restrictive Covenants

- **required**: `true` for a buyer-side SPA.
- **covered_holder_groups**: founders, executives, key holders from the cap table.
- **required_action**: `add_founder_executive_non_compete_and_non_solicit` when the draft lacks these.

## D&O Tail and Expenses

- **do_tail_required**: `true` when the deal is a stock purchase.
- **tail_period_years**: from playbook (typically 6).
- **tail_cost_allocation**: `seller_expense_or_purchase_price_reduction`.
- **seller_transaction_expenses**: `seller_responsibility_or_purchase_price_reduction`.
- **buyer_transaction_expenses**: `buyer_responsibility`.
- **amount_status**: `amount_not_in_workbench` when no dollar amounts are provided.

## Regulatory

- **hsr_required**: `yes` when the deal exceeds size-of-transaction threshold.
- **threshold_basis**: `size-of-transaction` or `below threshold`.
- **regulatory_approval**: `HSR only`, `HSR and industry review`, or `none expected`.
- **hell_or_high_water_required**: `yes`, `no`, or `limited covenant` per the regulatory record.
- **closing_condition_required**: `true` when HSR applies.

## Closing Readiness

- **overall_status**: `READY` (no unresolved blockers), `READY_WITH_CONDITIONS` (minor open items), `NOT_READY` (material blockers remain).
- **risk_rating**: driven by the highest-risk blocker.
- **blocker_ids**: every consent, contract, regulatory, or term issue that must be resolved before closing can occur.
- **tradeable_issue_ids**: issues that require attention but do not block closing.
- **closing_consent_amount_at_risk**: sum of amount_at_risk for closing-condition consents.
- **material_contract_revenue_conditioned**: sum of annual_revenue for contracts requiring closing consent.
- **employee_pto_liability_total**: from the employment section.
