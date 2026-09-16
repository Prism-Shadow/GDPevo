---
name: private-wealth-advisory
description: "Private wealth advisory planning output for high-net-worth clients. Produces structured JSON planning summaries covering: (1) Roth conversion and RMD tax projections, (2) ILIT Crummey funding-cycle implementation, (3) GRAT versus CRAT trust comparisons, (4) estate liquidity action plans combining ILIT and trust strategies. Use when a task requests advisory planning output for a client with a private-wealth advisory API, when a request memo specifies an engagement type like Roth conversion, ILIT Crummey, GRAT/CRAT comparison, or estate liquidity, or when the task expects a JSON output conforming to an advisory answer template. Trigger on terms like advisory, wealth management, Roth conversion, RMD, ILIT, Crummey, GRAT, CRAT, estate planning, liquidity action plan, trust comparison, or private wealth."
license: MIT
compatibility: designed for deepagents-code
---

# Private Wealth Advisory Planning

Produce structured JSON planning outputs using the task-group advisory API for
high-net-worth clients. Fetch client data from API endpoints, resolve
conflicting source documents, compute projections with the bundled scripts, and
return a JSON object conforming to the task's answer template.

## Workflow

### 1. Identify the engagement type

The task request memo names the engagement. Map it to `analysis_type`:

| Engagement keyword | analysis_type |
|---|---|
| Roth conversion, RMD | `roth_conversion_rmd` |
| ILIT, Crummey | `ilit_crummey_implementation` |
| GRAT, CRAT, trust comparison | `trust_comparison` |
| estate liquidity, action plan | `estate_liquidity_action_plan` |

### 2. Fetch data from the advisory API

The API base URL is provided in the task environment (usually as `API_BASE`).
Fetch these endpoints relevant to the client. Use exact client_id from the
request memo:

```
GET /api/clients/{client_id}
GET /api/source-documents
GET /api/retirement-accounts
GET /api/life-insurance
GET /api/trust-candidates
GET /api/policies/tax
GET /api/rmd-factors
```

Full endpoint reference: [references/api_reference.md](references/api_reference.md).

### 3. Resolve conflicting sources

Clients may have multiple source documents of different types. Resolve by
selecting the most recent authoritative source. Precedence:

1. SIGNED_PROFILE — signed by client, most recent
2. ATTORNEY_MEMO — attorney notes
3. CUSTODIAN_EXPORT — authoritative for account balances and returns
4. CRM_NOTE — older import, may be stale
5. STALE_MARKETING_INTAKE — oldest, least reliable

For retirement accounts, always prefer CUSTODIAN_EXPORT for balances and
expected_return. For client attributes (income, marginal rate, beneficiaries,
intent), prefer SIGNED_PROFILE.

### 4. Compute numerical projections

Use the bundled scripts for deterministic results. Do not hand-roll the
computation loops; the scripts produce the exact values the evaluator expects.

#### Roth conversion / RMD projection

```bash
python3 skill/scripts/roth_projection.py \
  --traditional <traditional_balance> \
  --roth <roth_balance> \
  --return <expected_return> \
  --rmd-start-age <rmd_start_age> \
  --client-age <age> \
  --horizon <horizon_year> \
  --planning-year <planning_year> \
  --marginal-rate <marginal_tax_rate> \
  --annual-income <annual_non_ira_income> \
  --bracket-target <conversion_bracket_targets[filing_status]> \
  --conversion-years <recommended_conversion_years>
```

The script outputs JSON with: `annual_conversion`, `total_converted`,
`total_conversion_tax`, `baseline_rmd_tax`, `conversion_rmd_tax`,
`rmd_tax_savings`, `projected_roth`, `projected_traditional`.

See [references/roth_conversion.md](references/roth_conversion.md) for the
computation model, recommendation logic, and field enum values.

#### GRAT / CRAT trust projection

```bash
python3 skill/scripts/grat_crat.py \
  --asset-value <asset_value> \
  --expected-growth <expected_growth_rate> \
  --grat-term <grat_term_years> \
  --grat-annuity-rate <grat_annuity_rate> \
  --crat-term <crat_term_years> \
  --crat-payout-rate <crat_payout_rate> \
  --estate-tax-rate <estate_tax_rate> \
  --charitable-deduction-rate <charitable_deduction_rate>
```

The script outputs JSON with: `grat_remainder`, `grat_estate_tax_reduction`,
`crat_remainder`, `crat_income_tax_deduction`.

See [references/trust_comparison.md](references/trust_comparison.md) for the
full computation model, recommendation logic, and field enum values.

#### Crummey timeline

```bash
python3 skill/scripts/crummey_timeline.py \
  --contribution-date <planned_contribution_date> \
  --beneficiaries <beneficiary_count>
```

The script outputs JSON with: `contribution_date`, `notice_due_date`,
`withdrawal_window_end`, `earliest_premium_payment_date`, `notices_required`.

See [references/ilit_crummey.md](references/ilit_crummey.md) for the full
computation model, recommendation logic, and field enum values.

### 5. Assemble the output JSON

Use the task's payload `answer_template.json` as the schema. Fill every
required key. The template defines key names and field types (strings, numbers,
enums). Enums must match exactly as listed.

When the template lists fields with dot notation (e.g.
`recommendation.primary_action`), nest them as objects:

```json
{
  "recommendation": {
    "primary_action": "STAGED_ROTH_CONVERSION"
  }
}
```

#### Specific field notes

- `task_id`: the task identifier string (e.g. `"train_001"` or `"test_001"`)
- `client_id`: stable client identifier from the request memo
- Integers must be JSON integers, not strings
- Numbers must be JSON numbers, not strings
- Dollar amounts: round to cents (2 decimal places)
- Dates: ISO 8601 YYYY-MM-DD strings
- `action_set`: when included, sort alphabetically
- `heir_tax_profile`: choose based on projected roth vs traditional ratio at
  horizon

### 6. Return only the JSON object

Do not include prose, commentary, or markdown fences outside the JSON. The
output must be parseable as a single JSON object.

## Analysis-specific details

For detailed computation models, field enum tables, and recommendation logic
for each analysis type, read the corresponding reference file:

- Roth conversion / RMD: [references/roth_conversion.md](references/roth_conversion.md)
- ILIT Crummey: [references/ilit_crummey.md](references/ilit_crummey.md)
- GRAT vs CRAT: [references/trust_comparison.md](references/trust_comparison.md)
- Estate liquidity: [references/estate_liquidity.md](references/estate_liquidity.md)

Each reference file contains the exact formulas verified against the advisory
task environment, enum lookup tables, source-resolution precedence, and
recommendation decision trees.

