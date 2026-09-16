# Deviation Matrix Reference

Use this reference when the prompt asks for a **buyer-side SPA deviation matrix** with position mapping, closing blockers, and risk totals.

## Data Sources

1. `/api/deals/<id>` — headline purchase price
2. `/api/deals/<id>/terms` — indemnity cap, survival, materiality scrape, consent terms
3. `/api/playbooks/<playbook_id>/rules` — buyer playbook
4. `/api/deals/<id>/regulatory` — HSR requirement, hell-or-high-water
5. `/api/deals/<id>/consents` — consent records with risk amounts
6. `/api/deals/<id>/material-contracts` — material contracts with annual revenue
7. `/api/deals/<id>/diligence-findings` — special indemnity, privacy findings
8. `/api/deals/<id>/risk-estimates` — quantified exposure ranges

## Position Matrix Issues

The seven issue IDs are fixed by the template. Map each one as follows:

### 1. `consent_closing_condition`

Check the consent-related term against the buyer playbook. The buyer wants all material consents as closing conditions.

- `draft_contract_count`: number of contracts the draft covers (from the term).
- `required_consent_ids`: consent IDs that map to closing conditions.
- `required_contract_ids`: material contract IDs needing consent.
- `excluded_from_draft`: contract categories the draft omits (e.g., `["payer_gateway_agreements"]`).
- `final_position`: `require_all_material_consents`.
- `status`: `draft_below_playbook` when the draft covers fewer contracts than the buyer needs.

### 2. `hsr_condition`

Check the regulatory record. If `hsr_required: true` and no corresponding draft term exists:

- `status`: `missing_required_term`.
- `hsr_required`: `true` from the regulatory record.
- `hell_or_high_water_required`: from regulatory.
- `final_position`: `add_hsr_clearance_condition`.

If a term exists but the covenant is weak, status is `draft_below_playbook`.

### 3. `material_contracts`

Check if the draft identifies specific contracts whose consent is a closing condition.

- `required_contract_ids`: the contracts the buyer needs.
- `excluded_contract_ids`: contracts the buyer accepts excluding (e.g., lower risk).
- `final_position`: `require_specific_contract_consents`.

### 4. `indemnity_cap_and_basket`

Compare the draft cap percentage against the buyer playbook.

- `basket_status`: check diligence findings and terms for basket language. `not_found_in_current_records` when absent.
- `special_indemnity_amount_usd`: from diligence findings (special indemnity finding).
- `privacy_finding_amount_usd`: from diligence findings (privacy-related finding).
- `final_position`: `raise_cap_to_at_least_fallback` when draft cap is below fallback.
- `shortfall_to_fallback_usd`: `fallback_amount_usd - draft_amount_usd`.
- `shortfall_to_preferred_usd`: `preferred_amount_usd - draft_amount_usd`.

### 5. `survival_and_knowledge`

Compare draft survival months against buyer playbook.

- `knowledge_qualifier_status`: check if the draft uses actual-knowledge or constructive-knowledge qualifiers. `not_found_in_current_records` when neither is present.
- When draft survival is at or above fallback but below preferred: `seek_18_months_or_condition_15_on_escrow`.

### 6. `escrow_holdback_release`

When the draft lacks escrow entirely:

- `status`: `missing_required_term`.
- `fallback_percent`: 10.0% of purchase price (buyer standard).
- `shortfall_to_fallback_usd`: full fallback amount since draft provides $0.
- `escrow_agent_status`: `not_found_in_current_records` when no agent is designated.
- `release_status`: `not_found_in_current_records` when no release mechanics are specified.
- `final_position`: `add_10_percent_escrow_with_unresolved_agent_and_release`.

### 7. `materiality_scrape`

Check the draft materiality-scrape clause.

- When the draft provides breach-only scrape and the buyer fallback accepts breach-only: `in_policy`, `accept`, `accept_breach_only_fallback`.

## Closing Blockers

Enumerate every item that must be resolved before closing:

- **Consent blockers**: one entry per `required_consent_id` with `blocker_type: required_consent`, `amount_at_risk_usd` from the consent record.
- **Regulatory blocker**: synthetic ID like `REG_<deal_id>_HSR` with `blocker_type: regulatory_clearance`.
- **Material contract blockers**: one entry per `required_contract_id` with `blocker_type: material_contract_consent`, `annual_revenue_usd` from the contract record.

All blockers have `must_be_satisfied_before_closing: true`.

## Risk Totals

- **headline_purchase_price_usd**: from the deal record.
- **position_issue_count**: total issues in the position matrix.
- **out_of_policy_issue_count**: count of issues not `in_policy`.
- **draft_below_playbook_count / missing_required_term_count**: counts by status.
- **high_risk_issue_count**: count of HIGH risk issues.
- **closing_blocker_count**: total closing blockers.
- **required_consent_amount_at_risk_usd**: sum of `amount_at_risk_usd` across consent blockers.
- **material_contract_revenue_requiring_consent_usd**: sum of `annual_revenue_usd` across material contract blockers.
- **indemnity_cap_shortfall_to_fallback_usd / _to_preferred_usd**: from the indemnity cap issue.
- **total_modeled_exposure_low_usd / _high_usd**: sum of risk estimate low/high ranges.
- **highest_modeled_exposure_category**: `closing_certainty` or `indemnity_leakage`, whichever has the larger high-end exposure.
