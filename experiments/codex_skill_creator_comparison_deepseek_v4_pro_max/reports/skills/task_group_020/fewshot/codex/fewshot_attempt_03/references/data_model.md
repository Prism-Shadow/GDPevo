# M&A Deal Workbench Domain Model

## Core Entities

### Deal
- `deal_id`: Stable project identifier (e.g., `PRJ_JUNIPER`)
- `headline_value`: Headline purchase price in USD, used as the default basis for percent-to-dollar calculations
- `currency`: Always `USD`
- `structure`: Asset purchase, stock purchase, or merger
- `buyer_name`, `seller_name`: Counterparty names

### Term
Terms are draft provisions in the current agreement. Each has:
- `term_id`: Stable identifier (e.g., `TERM_PRJ_JUNIPER_01`)
- `clause_ref`: Article or section reference
- Values: usually percent points, months, or dollar amounts depending on the term type
- May be absent from the terms endpoint (treat as missing required term when playbook/policy requires it)

### Playbook Rule
- `rule_id`: Stable identifier
- `issue_category`: maps to the issue types in answer templates
- `preferred_percent`, `preferred_months`, `preferred_amount`: seller/buyer ideal position
- `fallback_percent`, `fallback_months`, `fallback_amount`: fallback (worst acceptable) position
- `required`: boolean; when true, an absent term is a `missing_required_term` issue
- Used for seller-side and buyer-side playbook comparisons

### Policy Threshold
- `threshold_id`: Stable identifier
- `category`: maps to term categories in escalation memos
- `threshold_value`, `threshold_unit`: the limit beyond which escalation is required
- `threshold_amount`: dollar equivalent for percent-based thresholds
- `required_triggers`: mandatory conditions (e.g., `superior_proposal`, `intervening_event`)
- `approved_carveout_groups`: allowed MAE carveout groups
- Used for committee escalation analysis

### Consent
- `source_id`: Stable identifier (e.g., `CNS_PRJ_JUNIPER_01`)
- `contract_name`, `counterparty`: The agreement and counterparty
- `condition_type`: `closing_condition`, `notice_only`, or `post_closing_covenant`
- `risk_rating`: `LOW`, `MEDIUM`, `HIGH`
- `amount_at_risk`: Dollar exposure if the consent is not obtained

### Regulatory Record
- `hsr_required`: boolean
- `threshold_basis`: `size-of-transaction` or `below-threshold`
- `regulatory_approval`: `HSR only`, `HSR and industry review`, or `none expected`
- `hell_or_high_water_required`: boolean

### Employee Record
- `employee_id`: Stable identifier
- `employee_group`: Group classification (e.g., `field and operations`)
- `pto_liability`: Accrued PTO dollar amount
- `service_credit_required`: boolean
- `warn_risk`: boolean indicating WARN Act risk

### Risk Estimate
- `estimate_id`: Stable identifier (e.g., `RSK_PRJ_JUNIPER_01`)
- `type`: `closing_certainty`, `indemnity_leakage`, `transition_disruption`, or `not_quantified`
- `low`: Conservative exposure estimate in dollars
- `high`: Aggressive exposure estimate in dollars

### Benchmark
- `metric`: What is being measured (e.g., `fee percent of equity value`)
- `sample_size`: Number of comparable transactions
- `median`: Median value
- `upper_quartile`: 75th percentile value

### Cap Table Entry
- `holder`: Holder group name
- `security_class`: `common stock`, `preferred stock`, or `options`
- `fully_diluted_pct`: Ownership percentage (use 4 decimal places)
- `as_converted_shares`: Share count

## Key Relationships

- **Terms vs Playbook Rules**: Each issue category maps to one or more terms and one or more playbook rules. Compare draft term values against playbook preferred/fallback values.
- **Terms vs Policy Thresholds**: Each escalation category maps to terms checked against policy threshold values.
- **Consents vs Closing Conditions**: Only consents with `condition_type: closing_condition` become required closing consents or blockers. Notice-only consents should be excluded from required lists.
- **Material Contracts vs Closing**: Material contracts requiring consent become closing conditions.
- **Risk Estimates vs Issues**: Risk estimate types map to issue categories for exposure quantification.
- **Benchmarks vs Policy Deviations**: When available, benchmark data supports recommendations for policy deviations.
