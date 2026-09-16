# Transition Review Reference

Use this reference when the prompt asks for a **seller-side carveout APA transition review** covering transition/separation terms with issue analysis, required redlines, and operational risk summary.

## Data Sources

1. `/api/deals/<id>` — deal structure, parties
2. `/api/deals/<id>/terms` — TSA terms, consent terms, employee terms
3. `/api/playbooks/<playbook_id>/rules` — seller playbook
4. `/api/deals/<id>/consents` — consent records with contract references
5. `/api/deals/<id>/material-contracts` — material contract records with revenue
6. `/api/deals/<id>/employees` — employee groups, counts, PTO
7. `/api/deals/<id>/regulatory` — HSR requirement
8. `/api/deals/<id>/documents` — documents that may contain IP/domain/tax references
9. `/api/deals/<id>/risk-estimates` — stranded cost, disruption estimates

## Issue Categories

The template defines eight stable issue IDs covering the full transition scope:

| Issue ID                          | What to check                                                              |
|-----------------------------------|----------------------------------------------------------------------------|
| `TSA_SCOPE_DURATION_FEES`         | Draft TSA duration exceeds seller fallback; fee model is at-cost instead of cost-plus-stranded-overhead; clean termination right is missing. |
| `IP_DOMAIN_TRANSITION_MISSING`    | No transitional trademark license or domain redirect provision when the deal transfers IP-dependent operations. |
| `FIELD_EMPLOYEE_CONTINUITY_PTO`   | Draft allows buyer cherry-picking; rejects accrued PTO; lacks service credit. |
| `CUSTOMER_CONSENT_TERMINATION_RIGHT` | Draft gives buyer termination right if any top customer consent is missing; too broad. |
| `OUTSIDE_DATE_EXTENSION_MISSING`  | No outside date or seller regulatory extension when HSR is required. |
| `SECTION_1060_ALLOCATION_MISSING` | No Section 1060 purchase-price allocation provision. |
| `TRANSFER_TAX_SPLIT_MISSING`      | No transfer tax split provision; draft silent. |
| `GOVERNING_LAW_FORUM_FIX`         | No governing law or forum specified. |

## Issue Object Shape

Each transition issue uses `draft_value_normalized` and `required_position_normalized` objects (not scalar percent/month fields) because most transition issues are binary or multi-faceted:

- **draft_value_normalized**: what the draft currently says, expressed as booleans, counts, and extracted values.
- **required_position_normalized**: what the seller playbook requires, in the same shape.
- **quantified_impact_dollars**: integer dollar risk or null when not quantifiable.

## Required Redlines

Each issue maps to one required redline. The redline_id must come from the template's `stable_redline_ids`. The `redline_action` is `add` for missing terms and `revise` for existing terms that need correction.

The `must_have_terms` object captures the concrete provisions the redline must include — use the `required_position_normalized` values, translated into enforceable contract language.

## Operational Risk Summary

- **overall_risk_rating**: HIGH when any transition issue is HIGH.
- **overall_posture**: `revise_before_signing` when HIGH-risk issues exist; `accept_as_drafted` only when all issues are LOW or in-policy.
- **priority_order**: issue IDs ordered highest to lowest negotiation priority. TSA scope and fees typically top the list.
- **quantified_exposures**: five named dollar amounts:
  - `stranded_cost_gap_dollars`: from risk estimate for TSA.
  - `field_operations_pto_liability_dollars`: from employee records.
  - `required_closing_consent_amount_at_risk_dollars`: sum of at-risk amounts on closing-condition consents.
  - `top_customer_annual_revenue_at_risk_dollars`: highest annual revenue among material contracts requiring consent.
  - `transition_disruption_high_dollars`: from risk estimate or calculated as a proportion of stranded cost.
- **required_closing_consent_ids**: consent IDs flagged as closing conditions.
- **material_contract_consent_ids**: material contract IDs requiring consent.
- **business_outcomes_protected**: short descriptions of what each redline protects (e.g., "seller separation cost recovery", "Delaware dispute forum predictability").
