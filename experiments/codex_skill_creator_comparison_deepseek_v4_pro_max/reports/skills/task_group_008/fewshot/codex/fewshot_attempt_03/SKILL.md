---
name: private-wealth-advisory
description: Structured private-wealth planning for tax, Roth conversions, RMD projections, ILIT Crummey funding, GRAT/CRAT trust comparison, and estate liquidity action plans. Use when an advisor request memo asks for structured JSON output across any of these domains and references the advisory API at a supplied base URL (clients, source documents, retirement accounts, life insurance, trust candidates, tax policies, RMD factors). Triggers on prompts that mention client IDs (CLT-XXXX), analysis types such as roth_conversion_rmd, ilit_crummey_implementation, trust_comparison, or estate_liquidity_action_plan, and structured planning output.
---

# Private Wealth Advisory

Analyze private-wealth advisory engagements and produce structured JSON outputs for
advisors. Every engagement uses the task-group advisory API and one local request
memo per client. The API supplies client records, source documents, retirement
accounts, life-insurance policies, trust candidates, tax policy constants, and
RMD factors.

## Core Workflow

1. Read the request memo for the client ID, engagement type, and any planning
   horizon. Read the answer template for required keys and enum constraints.

2. Hit the advisory API at `{API_BASE}` (supplied by the harness) to pull all
   data. Always fetch the full list endpoints first; filter locally by
   `client_id`. Fetch clients, source-documents, retirement-accounts,
   life-insurance, trust-candidates, policies/tax, and rmd-factors.

3. Resolve conflicting source documents: the signed profile (`SIGNED_PROFILE`)
   with the most recent `effective_date` controls household facts (beneficiary
   count, income, tax rate, intent). The custodian export (`CUSTODIAN_EXPORT`)
   controls retirement-account balances and return assumptions. Attorney memos
   (`ATTORNEY_MEMO`) may control asset values when they are the most recent
   document with that fact. CRM notes (`CRM_NOTE`) and stale marketing intakes
   (`STALE_MARKETING_INTAKE`) are overridden by any newer signed or attorney
   source. Always annotate the controlling source in `source_resolution`.

4. Compute the analysis type-specific fields per the formulas in
   [references/formulas.md](references/formulas.md). Round all USD amounts to
   cents (two decimal places). Use ISO `YYYY-MM-DD` for dates.

5. Return only a JSON object conforming to the answer template. No surrounding
   prose.

## API Reference

All endpoints and their response shapes are documented in
[references/api_endpoints.md](references/api_endpoints.md). Read it before
building any API call.

## Computation Reference

All formulas for the four analysis types (Roth conversion, ILIT Crummey, trust
comparison, estate liquidity) are in [references/formulas.md](references/formulas.md).
Use that reference for every domain computation.

## Source Resolution Rules

When source documents disagree, resolve as follows in priority order:

1. **SIGNED_PROFILE** — choose the document with the most recent effective_date.
   Controls: beneficiary_count, annual_non_ira_income, marginal_tax_rate,
   philanthropic_intent, family_transfer_priority, age, filing_status,
   marital_status, liquid_assets, estate_value, planning_year.

2. **ATTORNEY_MEMO** — used when it is the most recent source with a given fact
   (particularly estate_value, family_transfer_priority, philanthropic_intent).
   The memo effective_date is always newer than CRM notes.

3. **CUSTODIAN_EXPORT** — always controls retirement-account facts:
   traditional_balance, roth_balance, expected_return, rmd_start_age,
   recommended_conversion_years. No other source may override these.

4. **CRM_NOTE** — stale imports overridden by any SIGNED_PROFILE or
   ATTORNEY_MEMO. Never use as the controlling source when a newer profile
   or attorney doc exists.

5. **STALE_MARKETING_INTAKE** — never the controlling source if any other
   document exists for the same client.

For each analysis output, fill `source_resolution` with the document type
that controlled the key facts used in the computation.
