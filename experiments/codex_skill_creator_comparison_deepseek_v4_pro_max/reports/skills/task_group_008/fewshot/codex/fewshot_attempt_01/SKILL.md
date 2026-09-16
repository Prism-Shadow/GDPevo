---
name: wealth-advisory
description: Private wealth tax and estate planning analysis via advisory API. Use when a prompt asks you to prepare structured wealth planning JSON output for a client engagement using an advisory API base URL (usually API_BASE). Covers Roth conversion RMD analysis, ILIT Crummey funding, GRAT vs CRAT trust comparison, and estate liquidity action plans. The advisory environment provides client records, source documents, retirement accounts, life insurance policies, trust candidates, tax policy constants, and RMD factors accessible via REST endpoints.
---

# Wealth Advisory Planning

Prepare structured JSON planning outputs for private wealth advisory engagements. The harness supplies an API base URL (typically `API_BASE`). Use `curl` to call the endpoints listed in [API Reference](references/api_reference.md).

## Workflow

1. Read `input/payloads/request_memo.md` to identify the client ID and engagement type.
2. Read `input/payloads/answer_template.json` to learn the required output schema.
3. Fetch all relevant API data for the client. Start with these calls in parallel:
   - `GET {API_BASE}/api/clients/{client_id}`
   - `GET {API_BASE}/api/source-documents` (filter by client_id)
   - `GET {API_BASE}/api/retirement-accounts` (filter by client_id)
   - `GET {API_BASE}/api/life-insurance` (filter by client_id)
   - `GET {API_BASE}/api/trust-candidates` (filter by client_id)
   - `GET {API_BASE}/api/policies/tax`
   - `GET {API_BASE}/api/rmd-factors`
4. Resolve conflicting source documents using the priority rules in [Computation Guide](references/computation_guide.md).
5. Compute all numeric values using the formulas for the analysis type in [Computation Guide](references/computation_guide.md).
6. Produce a JSON object matching the answer template. Use USD amounts rounded to cents and ISO dates (YYYY-MM-DD). Return only the JSON, no prose.

## Analysis Types

See [Computation Guide](references/computation_guide.md) for full formulas and decision logic.

- **Roth Conversion RMD** (`roth_conversion_rmd`): Staged Roth conversions to reduce RMD tax. Compute conversion plan, baseline vs conversion RMD projections, and legacy balances.
- **ILIT Crummey Implementation** (`ilit_crummey_implementation`): ILIT funding with Crummey notice cycle. Compute gift-tax exclusion capacity, premium gap, notice dates, and estate inclusion risk.
- **Trust Comparison** (`trust_comparison`): GRAT vs CRAT numerical comparison. Compute estate context, GRAT remainder, CRAT charitable remainder, and select a recommendation based on family transfer vs philanthropic priority.
- **Estate Liquidity Action Plan** (`estate_liquidity_action_plan`): Combined ILIT and trust transfer with estate liquidity. Compute estate gap, ILIT metrics, trust transfer, and an alphabetically sorted action set.

## API Data

Complete endpoint documentation is in [API Reference](references/api_reference.md). Key resources:

| Endpoint | Returns |
|---|---|
| `/api/clients/{id}` | Client profile: age, marital status, filing status, estate value, liquid assets |
| `/api/source-documents` | Conflicting source documents: CRM notes, attorney memos, signed profiles |
| `/api/retirement-accounts` | IRA balances, expected returns, RMD start age, conversion recommendations |
| `/api/life-insurance` | Life insurance policies: death benefit, premium, contribution dates |
| `/api/trust-candidates` | Trust parameters: asset value, growth rates, GRAT/CRAT terms and rates |
| `/api/policies/tax` | Tax constants: gift exclusion, estate exemption, tax rates, bracket targets |
| `/api/rmd-factors` | RMD divisors keyed by age (73-99) |
| `/portal/client/{id}` | Human-readable portal page (optional context, not machine-parseable) |

## Source Resolution

When source documents disagree, resolve by priority and recency. Full rules in [Computation Guide](references/computation_guide.md). Default hierarchy:

- For profile data (income, beneficiaries, intent, tax rate): SIGNED_PROFILE > ATTORNEY_MEMO > CRM_NOTE > STALE_MARKETING_INTAKE
- For account data: CUSTODIAN_EXPORT > SIGNED_PROFILE > CRM_NOTE
- Within the same source type, prefer the latest `effective_date`

## Output

Return only a JSON object that matches the schema in the answer template. Fields must use the exact enum values, ISO dates, and numeric types specified. All USD values rounded to cents.
