# Issue Register Reference

Use this reference when the prompt asks for a **seller-side APA issue register** structured as a list of issue objects with priority ordering and summary metrics.

## Data Sources

For a standard issue register, pull:

1. `/api/deals/<id>` — headline value, parties, dates
2. `/api/deals/<id>/terms` — every draft term
3. `/api/playbooks/<playbook_id>/rules` — seller playbook (e.g., `PB_SELLER_A`)
4. `/api/deals/<id>/risk-estimates` — named estimates with low/high ranges
5. `/api/deals/<id>/employees` — employee count, PTO liability
6. `/api/deals/<id>/consents` — consent conditions on closing
7. `/api/deals/<id>/regulatory` — HSR requirement, effort standard
8. `/api/deals/<id>/benchmarks` — market comps for escrow, caps, survival
9. `/api/deals/<id>/notes` — negotiation context

## Issue Enumeration

Walk through every term in the playbook. For each rule:

1. Find the matching draft term by comparing the rule's subject matter against the term records.
2. If a match exists, compare the draft value to the preferred and fallback.
3. If no match exists, decide whether the deal facts (employees, consents, regulatory) make this a genuinely missing required term.

Common issue categories for seller-side APAs:

| Issue ID              | What to check                                                        |
|-----------------------|----------------------------------------------------------------------|
| `FINANCING_CONDITION` | Draft contains a buyer financing condition; seller playbook says delete. |
| `REVERSE_BREAK_FEE`   | Draft has no or inadequate reverse break fee for seller protection. |
| `ESCROW`              | Draft escrow % and release months exceed seller fallback.           |
| `INDEMNITY_CAP`       | Draft cap % exceeds seller fallback.                                 |
| `INDEMNITY_BASKET`    | Draft silent on deductible basket; seller requires it.              |
| `SURVIVAL_PERIOD`     | Draft survival months exceed seller fallback.                        |
| `NON_COMPETE_NON_SOLICIT` | Draft silent; seller needs scope-limited non-compete from buyer. |
| `EMPLOYEE_CONTINUITY` | Draft allows buyer to cherry-pick or rejects service credit/PTO.    |
| `TRANSITION_SERVICES` | Draft lacks TSA; seller needs limited-duration, cost-recovery TSA.  |
| `TAX_ALLOCATION`      | Draft silent on Section 1060 allocation or transfer tax split.      |
| `GOVERNING_LAW_FORUM` | Draft silent on governing law and forum.                             |
| `CONSENT_CONDITION`   | Draft consent condition is too broad for seller.                     |
| `MATERIALITY_SCRAPE`  | Double-materiality or full-scrape vs. seller single-scrape preference. |
| `HSR_COVENANT`        | Draft HSR covenant strength relative to seller position.             |

## Field Population Rules

- **draft_percent / playbook_preferred_percent / playbook_fallback_percent**: percent points from the term and playbook. Null if not applicable.
- **draft_amount_dollars**: `round(headline_value * draft_percent / 100)`.
- **preferred_amount_dollars**: `round(headline_value * playbook_preferred_percent / 100)`.
- **fallback_amount_dollars**: `round(headline_value * playbook_fallback_percent / 100)`.
- **delta_to_fallback_dollars**: `draft_amount - fallback_amount` when draft exceeds fallback; `fallback_amount - draft_amount` when draft is below. Positive integer.
- **delta_to_fallback_months**: same logic for month-based terms.
- **required_fee_percent / required_fee_dollars**: for reverse break fees, the fallback fee the seller needs.
- **shortfall_dollars**: `required_fee_dollars - draft_amount_dollars` when draft provides less than required.
- **employee_count / pto_liability_dollars**: pulled from `/api/deals/<id>/employees`.
- **service_credit_required**: true when playbook requires service credit and employees exist.
- **field_selection_allowed**: false when playbook rejects buyer cherry-picking.
- **hell_or_high_water_required / hsr_required / regulatory_effort_code**: from regulatory record.
- **governing_law / forum**: from playbook preferred (usually Delaware).
- **tax_allocation_method / transfer_tax_split**: from playbook tax rules.
- **covenant_limits**: object with `non_compete_months_max`, `non_solicit_months_max`, `scope`, `employee_non_solicit_exclusions`, or other playbook-derived fields. Null when not applicable.

## Summary Metrics Calculation

- **issue_count**: total issues in the register.
- **high_risk_count / medium_risk_count**: count by risk rating.
- **business_outcome_count**: distinct business outcomes represented.
- **headline_value_dollars**: from deal record.
- **total_quantified_exposure_low_dollars**: sum of all risk-estimate low values for quantified issues.
- **total_quantified_exposure_high_dollars**: sum of all risk-estimate high values for quantified issues.
- **total_negotiation_delta_dollars**: sum of all `delta_to_fallback_dollars` + `shortfall_dollars` across issues.
- **required_closing_consent_count**: count of consent records marked as closing conditions.
- **total_employee_count / total_pto_liability_dollars**: from employee endpoint.
