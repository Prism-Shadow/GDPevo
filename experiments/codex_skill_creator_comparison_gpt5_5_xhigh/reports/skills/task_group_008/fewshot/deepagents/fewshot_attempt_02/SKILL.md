---
name: private-wealth-advisory-json
description: Prepare structured JSON answers for private wealth advisory planning tasks that use the task-group advisory API, request_memo.md, and answer_template.json. Use for Roth conversion/RMD summaries, ILIT Crummey funding cycles, GRAT vs CRAT comparisons, and estate liquidity action plans where client facts must be reconciled across signed profiles, attorney memos, CRM notes, custodian exports, life insurance records, trust candidates, tax policy constants, and RMD factors.
---

# Private Wealth Advisory JSON

## Workflow

Read the task prompt, `input/payloads/request_memo.md`, and `input/payloads/answer_template.json` before calculating. Extract the `client_id`, `task_id`, required top-level keys, `analysis_type`, and any planning horizon stated in the memo.

Use the advisory API base from `API_BASE` when present. If the harness supplies the base another way, pass that URL explicitly. Fetch all relevant records for the client: profile, source documents, retirement accounts, life insurance, trust candidates, tax policy constants, and RMD factors.

For a fast deterministic draft, run the bundled helper with paths resolved relative to this skill:

```bash
python scripts/advisory_planner.py \
  --task-id test_001 \
  --memo input/payloads/request_memo.md \
  --template input/payloads/answer_template.json \
  --api-base "$API_BASE"
```

If the command cannot infer a value, add `--client-id`, `--analysis-type`, or `--horizon-year`. Treat the helper output as a draft to verify against the template and source records, especially if the prompt wording introduces a variant not covered by the template.

Return only the final JSON object. Use JSON numbers for currency, round USD fields to cents, use ISO dates, and sort `action_set` alphabetically when that field exists.

## Source Resolution

Prefer `SIGNED_PROFILE` for current household profile facts, beneficiary counts, tax rates, filing status, and planning goals. Use `CUSTODIAN_EXPORT` for IRA balances, Roth balances, expected returns, RMD start age, and recommended conversion years. Use `ATTORNEY_MEMO` for attorney-confirmed estate or trust asset facts when a source-resolution field asks for the asset source. Treat old `CRM_NOTE` facts as fallback only.

Use the life-insurance endpoint for policy dollars and contribution dates, then set policy source-resolution fields to the controlling profile source unless a later attorney memo clearly controls policy formalities.

## Manual Calculations

Read [references/calculation_rules.md](references/calculation_rules.md) when you need to audit, adjust, or reproduce the helper's formulas manually.
