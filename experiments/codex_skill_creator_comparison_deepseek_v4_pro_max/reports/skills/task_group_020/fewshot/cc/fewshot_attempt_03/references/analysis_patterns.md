# Analysis Patterns

This reference covers how to classify issues, assign risk ratings,
choose recommended actions, build priority orderings, and map issues to
business outcomes.  It applies to every task type.

## Issue classification

### Status assignment

Match the draft term value against the playbook or policy thresholds.
The client side determines the direction that is "bad" for your client.

| Status | When | Example |
|--------|------|---------|
| `in_policy` | Draft equals or is within the playbook preferred/fallback range | Materiality scrape at breach-only, which is the buyer fallback |
| `out_of_policy` | Draft violates a committee policy threshold | RTF at 6.0% when policy caps at 3.5% |
| `draft_exceeds_playbook` | Buyer draft gives buyer more than seller's fallback; or draft exceeds policy cap | Escrow at 15% when seller's fallback is 10% |
| `draft_below_playbook` | Seller draft gives buyer less than buyer's fallback; or draft is below required floor | Indemnity cap at 5% when buyer's fallback is 8% |
| `missing_required_term` | Draft is completely silent on a term the playbook or policy requires | No escrow provision when buyer playbook requires one |

### Seller-side direction

For seller reviews, the buyer draft is the starting point.  "Exceeds
playbook" means the buyer-requested value is higher than the seller's
fallback permits.  Higher escrow %, longer survival, broader
non-compete scope, broader MAE carveouts — all are "exceeds."

"Below playbook" for a seller means the buyer draft gives the seller
less than the seller's fallback requires — e.g., a missing or
zero-dollar reverse break fee when the seller needs fallback coverage.

### Buyer-side direction

For buyer reviews, the seller draft is the starting point.  "Below
playbook" means the seller-offered value is lower than the buyer's
fallback requires.  Lower indemnity cap, shorter survival, no escrow,
weaker consent conditions — all are "below."

"Missing required term" applies regardless of side when the playbook
or policy demands an affirmative provision and the draft is silent.

## Risk rating

Assign risk by answering: how much does this issue threaten the deal
or expose the client to uncompensated loss?

| Risk | Criteria |
|------|----------|
| HIGH | Closing certainty (financing condition, missing HSR condition, missing reverse break fee, consent blockers), quantified exposure at or above ~10% of headline price, fiduciary-out removal, missing required terms (escrow, IP-domain transition, TSA, outside-date extension) |
| MEDIUM | Moderate dollar gaps, survival-period overage, missing basket/tax/governing-law terms, knowledge-qualifier gaps, D&O tail |
| LOW | Housekeeping items, terms within negotiation range, notice-only conditions with no dollar exposure |

When a term has both a dollar gap and a structural risk, the dollar
exposure usually dominates.  A missing escrow provision on a $365M
deal is HIGH even if the gap is "only" 10%.

## Recommended action

Map status to the default action, then adjust for deal context.

| Status | Default action |
|--------|---------------|
| `in_policy` | `accept` |
| `out_of_policy` | `approve_with_conditions` or `reject` (reject for fiduciary-out removal, structural policy violations with no way to conditionally approve) |
| `draft_exceeds_playbook` | `revise` |
| `draft_below_playbook` | `revise` |
| `missing_required_term` | `add` |

For escalation memos: use `approve`, `approve_with_conditions`, or
`reject`.  `reject` is reserved for terms where the policy violation is
structural (e.g., removing a board's fiduciary-out trigger) rather than
just an economic overage.

## Priority ordering

Sort issues from highest negotiation urgency to lowest.  Within each
tier, sort by dollar exposure (descending).

### Tier 1: Closing certainty (always first)

- Financing condition
- HSR / regulatory clearance conditions
- Reverse break fee / termination fee
- Consent closing conditions
- Fiduciary out

### Tier 2: Core economics and mechanics

- Indemnity cap
- Escrow / holdback
- Materiality scrape
- Indemnity basket

### Tier 3: People and operations

- Employee continuity / service credit / PTO
- Transition services (TSA)
- Restrictive covenants (non-compete, non-solicit)
- Outside-date extension

### Tier 4: Administrative and structural

- Survival period
- Tax allocation / Section 1060
- Transfer tax split
- Governing law / forum
- IP / domain transition
- D&O tail and expenses

When the template provides a `priority_order` field, list every issue
ID in the sorted order.  Do not omit issues.

## Business outcome mapping

Map each issue to one business outcome.  Use the template's allowed
values when provided; otherwise use these standard categories:

| Issue domain | Business outcome |
|-------------|-----------------|
| Financing condition, reverse break fee, HSR, outside date, fiduciary out | `closing_certainty` |
| Escrow amount, release mechanics | `escrow_economics` |
| Indemnity cap, basket, survival, materiality scrape | `indemnity_exposure` |
| Non-compete, non-solicit | `restrictive_covenants` |
| Employee continuity, service credit, PTO, TSA | `employee_transition` |
| Section 1060, transfer tax | `tax_allocation` |
| Governing law, forum | `governing_law` |
| Consent conditions | `closing_certainty` |
| Regulatory approval requirements | `regulatory_efforts` |

## Recommended position codes

When the template requires a `required_position_code` or
`final_position`, derive it from the playbook fallback.  The code
should be a short snake_case summary of what the client needs in the
revised draft.  Examples from the training corpus:

- `delete_buyer_financing_condition`
- `add_six_percent_reverse_break_fee_if_financing_risk_remains`
- `reduce_escrow_to_fallback_and_release_at_twelve_months`
- `reduce_general_cap_to_verified_customer_concentration_fallback`
- `reduce_general_rep_survival_to_fifteen_month_fallback`
- `add_deductible_basket_for_general_indemnity_claims`
- `limit_restrictive_covenants_to_acquired_business_and_transferred_relationships`
- `require_all_continuing_employee_process_service_credit_and_pto_allocation`
- `add_tsa_limited_to_six_months_with_cost_recovery_and_clean_termination`
- `add_mutual_section_1060_allocation_and_equal_transfer_tax_split`
- `add_seller_preferred_delaware_law_and_forum`
- `raise_cap_to_at_least_fallback`
- `seek_18_months_or_condition_15_on_escrow`
- `accept_breach_only_fallback`
- `add_10_percent_escrow_with_unresolved_agent_and_release`
- `require_all_material_consents`
- `add_hsr_clearance_condition`
- `require_specific_contract_consents`

For final positions in deviation matrices, use the template's specific
list.  The code must be one of the allowed values.

## Closing readiness

When the output requires a closing readiness assessment:

- **READY**: No HIGH-risk blockers, all required consents have clear
  paths to resolution, regulatory approval is on track or not required.
- **READY_WITH_CONDITIONS**: One or more MEDIUM-risk issues remain but
  they are tradeable (not structural blockers), or HIGH-risk issues
  have been downgraded by conditions.
- **NOT_READY**: One or more HIGH-risk blockers remain unresolved
  (missing required consents, regulatory clearance not obtained,
  structural missing terms like no escrow or no indemnity cap).

**Blockers** are items that prevent closing unless resolved.  Required
consents, regulatory clearances, and material-contract closing
conditions are always blockers when they are HIGH risk.  Missing
required terms that are structural (no escrow, no HSR condition, no
indemnity cap) are also blockers.

**Tradeable issues** are items that affect deal economics but can be
resolved through negotiation without blocking closing.  D&O tail
amounts, notice-only consents, and survival-period overages are
typically tradeable.
