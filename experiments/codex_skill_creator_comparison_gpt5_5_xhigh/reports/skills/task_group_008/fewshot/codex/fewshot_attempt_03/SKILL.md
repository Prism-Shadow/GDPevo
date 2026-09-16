---
name: advisory-planning-json
description: Produce private wealth advisory planning JSON from a task memo, answer template, and the advisory API. Use for Roth conversion/RMD summaries, ILIT Crummey funding cycles, GRAT versus CRAT comparisons, and estate liquidity action plans that require resolving conflicting client records and returning only structured JSON.
---

# Advisory Planning JSON

Use this skill when a private wealth advisory task asks for a JSON object based on a local memo/template and the advisory API.

## Workflow

1. Read the task prompt, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`.
2. Get the API base from `API_BASE` when present. Otherwise use the base URL supplied by the task harness.
3. Extract `client_id`, planning horizon if present, and `task_id` from the task directory name or pass it explicitly.
4. Query records with client filters instead of broad collection reads:
   - `/api/clients/{client_id}`
   - `/api/source-documents?client_id={client_id}`
   - `/api/retirement-accounts?client_id={client_id}`
   - `/api/life-insurance?client_id={client_id}`
   - `/api/trust-candidates?client_id={client_id}`
   - `/api/policies/tax`
   - `/api/rmd-factors`
5. Prefer running [scripts/advisory_planning.py](scripts/advisory_planning.py) from this skill directory:

```bash
python3 scripts/advisory_planning.py \
  --memo input/payloads/request_memo.md \
  --template input/payloads/answer_template.json
```

Pass `--api-base`, `--client-id`, or `--task-id` only when they cannot be inferred.

## Source Resolution

Resolve conflicting source documents by source authority before recency:

`SIGNED_PROFILE` > `ATTORNEY_MEMO` > `CUSTODIAN_EXPORT` > `CRM_NOTE` > `STALE_MARKETING_INTAKE`.

Use the selected source for the matching `source_resolution` field. Retirement account fields normally come from `CUSTODIAN_EXPORT`. Trust candidate asset fields normally resolve to `ATTORNEY_MEMO` when the trust record has no explicit source type. Life-insurance policy fields normally resolve to `SIGNED_PROFILE` when the policy record has no explicit source type.

## Calculation Rules

For Roth/RMD tasks:
- Annual conversion amount is positive bracket room: `conversion_bracket_target[filing_status] - annual_non_ira_income`, floored at zero.
- Conversion years come from the retirement account recommendation. Count positive years only when the annual conversion amount is positive and traditional balance remains available.
- Conversion tax is total converted times the controlling marginal tax rate.
- First RMD year is the planning year plus the years until `rmd_start_age`; if the client is already at or past RMD age, use the planning year.
- For each year, apply any conversion at the start of the year, then calculate same-year RMD from the post-conversion traditional balance, subtract the RMD, and grow remaining traditional and Roth balances at year end.
- Baseline RMD tax uses the same RMD timing but no conversions.

For ILIT Crummey tasks:
- Annual exclusion capacity is annual gift exclusion for the planning year times beneficiary count.
- Premium gap is annual premium less exclusion capacity, floored at zero.
- Notice due date is seven days after contribution. Withdrawal window ends thirty days after notice due date. Earliest premium payment date is the following day.
- Risk is low when there is no premium gap and no existing-policy transfer; otherwise combine exclusion shortfall and three-year lookback risk as applicable.
- Tax liquidity support is death benefit times estate tax rate.

For GRAT/CRAT tasks:
- Estate exemption used is one exemption for single clients and two for married/MFJ clients.
- Taxable estate is estate value less exemption used, floored at zero. Estate tax exposure is taxable estate times the estate tax rate. Liquidity gap is exposure less liquid assets, floored at zero.
- GRAT remainder is `asset_value * (1 + expected_growth_rate) ** grat_term_years - asset_value * grat_annuity_rate * grat_term_years`.
- GRAT estate tax reduction is GRAT remainder times the estate tax rate.
- CRAT charitable remainder is `asset_value * (1 + expected_growth_rate) ** crat_term_years - asset_value * crat_payout_rate * crat_term_years`, using the policy maximum term if lower.
- CRAT income tax deduction is charitable remainder times the charitable deduction rate.
- Prefer GRAT for stronger family-transfer priority; prefer CRAT for stronger philanthropic priority.

For estate liquidity action plans, combine the estate context, ILIT, and trust-transfer calculations. Include attorney review, ILIT notice cycle, GRAT, CRAT, and lifetime exemption actions only when supported, and sort `action_set` alphabetically.

## Output Checks

Return only JSON. Use JSON numbers for money, rounded to cents. Use ISO `YYYY-MM-DD` dates. Preserve the template's required top-level keys, allowed enum values, and special ordering notes such as sorted `action_set`.
