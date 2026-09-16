---
name: advisory-planning-json
description: Generate structured JSON outputs for private wealth advisory planning tasks that use the task-group advisory API, including Roth/RMD conversion summaries, ILIT Crummey funding cycles, GRAT versus CRAT trust comparisons, and combined estate liquidity action plans. Use when the prompt provides API_BASE or an advisory API base URL, a client ID, request memo, and answer_template.json.
---

# Advisory Planning JSON

## Core Workflow

1. Read `prompt.txt`, `payloads/request_memo.md`, and `payloads/answer_template.json`.
2. Infer `client_id`, `task_id`, requested `analysis_type`, and any memo horizon year before querying the API.
3. Query only the advisory API records needed for that client. Prefer client-filtered calls such as `/api/source-documents?client_id=...`, `/api/retirement-accounts?client_id=...`, `/api/life-insurance?client_id=...`, and `/api/trust-candidates?client_id=...`, plus `/api/clients/{client_id}`, `/api/policies/tax`, and `/api/rmd-factors`.
4. Resolve conflicting facts by source priority: `SIGNED_PROFILE`, then `ATTORNEY_MEMO`, then `CUSTODIAN_EXPORT`, then `CRM_NOTE`, then `STALE_MARKETING_INTAKE`. Retirement account values control from `CUSTODIAN_EXPORT`; trust candidate asset assumptions control from `ATTORNEY_MEMO`; life insurance policy records are treated as `SIGNED_PROFILE` unless the record carries a source.
5. Return only the final JSON object. Use JSON numbers for money rounded to cents, booleans for boolean fields, and ISO `YYYY-MM-DD` strings for dates.

## Helper Script

Use the bundled solver for the known advisory task family:

```bash
API_BASE="${API_BASE:-http://task-env:9008/}" \
python3 skill/scripts/advisory_planning_solver.py --input-dir input --task-id test_001
```

If running from inside a task input directory, omit `--input-dir`. If the task id can be inferred from a parent directory named like `test_001`, omit `--task-id`.

The script prints the JSON answer to stdout. If it cannot infer a required value, inspect the template and API response, then apply the same formulas below manually.

## Calculation Rules

For Roth/RMD tasks:

- Annual conversion amount is the positive gap between the filing-status conversion bracket target and signed-profile annual non-IRA income.
- Use the retirement account's recommended conversion years. Convert at the beginning of each year, before any RMD, then calculate RMD on the reduced traditional balance and grow both traditional and Roth balances for the year.
- Baseline RMD tax uses beginning-of-year RMDs from the traditional balance before annual growth.
- First RMD year is `planning_year + max(0, rmd_start_age - age)`.
- Conversion tax is total converted times the signed-profile marginal tax rate. RMD tax savings are baseline RMD tax minus conversion-case RMD tax, rounded only at output time.

For ILIT Crummey tasks:

- Annual exclusion capacity is annual gift exclusion for the planning year times signed-profile beneficiary count.
- Premium gap is the positive excess of annual premium over exclusion capacity.
- Notice due date is 7 days after contribution; withdrawal window ends 30 days after notice due date; earliest premium payment is the next day.
- Risk is `LOW_IF_FORMALITIES_MET` when there is no existing policy transfer and no premium gap, `EXCLUSION_SHORTFALL` for only a gap, `THREE_YEAR_LOOKBACK` for only an existing transfer, and `THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL` when both apply.

For GRAT/CRAT and estate liquidity tasks:

- Exemption used is the current-year estate tax exemption times 2 for MFJ or married clients, otherwise times 1.
- Taxable estate is estate value minus exemption used, floored at zero. Estate tax exposure is taxable estate times the policy estate tax rate. Liquidity gap is estate tax exposure minus liquid assets, floored at zero.
- GRAT remainder is `asset_value * (1 + expected_growth_rate) ** grat_term_years - asset_value * grat_annuity_rate * grat_term_years`; estate tax reduction is that remainder times the estate tax rate.
- CRAT charitable remainder is `asset_value * (1 + expected_growth_rate) ** crat_term_years - asset_value * crat_payout_rate * crat_term_years`; income tax deduction is that remainder times the policy charitable deduction rate.
- Prefer GRAT when family transfer priority is high or at least as strong as philanthropy. Prefer CRAT when philanthropy is high and family transfer is not high.
