---
name: private-wealth-advisory-json
description: Produce structured private-wealth advisory JSON from task prompts, answer templates, request memos, and the advisory API. Use for Roth conversion/RMD projections, ILIT Crummey funding cycles, GRAT versus CRAT comparisons, and estate-liquidity action plans that require source resolution across client profiles, source documents, retirement accounts, life-insurance records, trust candidates, tax policy constants, and RMD factors.
---

# Private Wealth Advisory JSON

## Workflow

1. Read the prompt, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json`.
2. Identify `client_id`, `task_id`, requested `analysis_type`, and any planning horizon in the memo.
3. Query the advisory API with `API_BASE` for:
   - `/api/clients/{client_id}`
   - `/api/source-documents`
   - `/api/retirement-accounts`
   - `/api/life-insurance`
   - `/api/trust-candidates`
   - `/api/policies/tax`
   - `/api/rmd-factors`
4. Filter broad endpoint responses to the requested `client_id`; do not use records for other clients in the answer.
5. Resolve conflicts by source quality, not recency alone: `SIGNED_PROFILE` controls profile, goals, beneficiary count, and tax rate when present; `CUSTODIAN_EXPORT` controls retirement balances; life-insurance planning records are reported as controlled by `SIGNED_PROFILE`; trust-candidate assets are reported as controlled by `ATTORNEY_MEMO`.
6. Calculate with the formulas in [references/advisory-formulas.md](references/advisory-formulas.md), round USD values to two decimals, emit numbers as JSON numbers, and return only the final JSON object.

## Helper Script

For these task families, prefer the bundled deterministic helper:

```bash
python skill/scripts/solve_advisory_task.py input --api-base "$API_BASE"
```

Use `--task-id` only if the script cannot infer the task folder name from the input path. Inspect the generated JSON before returning it, especially that it conforms to the provided template and any sorted-list requirement.

## Manual Notes

- If calculating manually, read [references/advisory-formulas.md](references/advisory-formulas.md) first.
- Copy the template's required top-level keys exactly; include additional computed fields only when they are part of the learned advisory pattern and fit the requested object.
- For `action_set`, sort enum strings alphabetically.
