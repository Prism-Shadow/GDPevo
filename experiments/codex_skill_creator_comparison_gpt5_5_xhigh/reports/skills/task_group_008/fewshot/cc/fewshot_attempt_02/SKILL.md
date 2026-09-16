---
name: wealth-advisory-planning
description: Generate strict JSON planning outputs for private wealth advisory tasks that use the staged task API and a local answer template. Use when a prompt asks for a client-specific Roth conversion/RMD summary, ILIT Crummey funding check, GRAT vs CRAT comparison, or combined estate-liquidity plan, especially when the task includes a request memo, answer template, and allowed API endpoints.
---

# Wealth Advisory Planning

Use the staged API and the local task files to produce one JSON object that matches the supplied answer template.

## Workflow

1. Read the prompt, request memo, and answer template.
2. Extract `client_id` and `task_id` from the local files or pass them explicitly.
3. Query only the allowed task-env endpoints:
   - `/api/clients/{client_id}`
   - `/api/source-documents`
   - `/api/retirement-accounts`
   - `/api/life-insurance`
   - `/api/trust-candidates`
   - `/api/policies/tax`
   - `/api/rmd-factors`
4. Resolve conflicts with source precedence:
   - prefer `SIGNED_PROFILE` for household facts and goals
   - use `ATTORNEY_MEMO` when it is the highest-priority legal/planning note
   - use `CUSTODIAN_EXPORT` for retirement-account balances and RMD settings
   - fall back to `CRM_NOTE` only when newer sources do not supply the field
5. Use [scripts/advisory_planner.py](scripts/advisory_planner.py) to assemble the output when possible.
6. Emit JSON only. Do not add prose.

## Model Rules

- For Roth conversion tasks, set annual conversion capacity from the filing-status bracket target minus annual non-IRA income, clamp at zero, and limit the annual amount so total conversions do not exceed the traditional balance.
- Project Roth and traditional balances year by year. Apply each year’s conversion before that year’s RMD, subtract the RMD before growth, and tax the distribution at the marginal rate.
- For ILIT tasks, use the signed beneficiary count for annual exclusion capacity, compare it to the annual premium, and derive notice dates from the planned contribution date.
- For GRAT/CRAT tasks, calculate remainder values from the expected growth rate, term, and payout or annuity rate. Use the tax policy estate-tax rate for GRAT tax reduction and the charitable-deduction rate for CRAT deduction.
- For estate-liquidity plans, include both the ILIT math and the trust-transfer comparison, sort `action_set` alphabetically, and keep source-resolution fields aligned with the controlling records.

## Output Discipline

- Match enum values exactly as the template defines them.
- Round money to cents and dates to ISO `YYYY-MM-DD`.
- Keep extra fields only when they are part of the observed template family.
- Prefer the newest higher-priority source when multiple records disagree.
