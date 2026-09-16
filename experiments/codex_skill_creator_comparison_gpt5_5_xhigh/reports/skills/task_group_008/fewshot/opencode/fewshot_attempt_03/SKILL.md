---
name: wealth-advisory-json
description: Use this skill whenever the user asks for a client-specific private wealth advisory JSON output using a request memo, answer_template.json, and an advisory API. It is for estate liquidity plans, Roth conversion and RMD projections, ILIT/Crummey administration, GRAT versus CRAT comparisons, trust-transfer recommendations, and similar wealth-planning tasks. Use it even when the user only says to prepare the structured planning output or return the final JSON.
---

# Wealth Advisory JSON

Use this skill to produce a final JSON object for private wealth advisory planning tasks. The local `answer_template.json` is the output contract; the API data and local request memo are the evidence. The answer should be client-specific and numerical, not a generic planning memo.

## First Pass

1. Read the task prompt, the request memo, and `input/payloads/answer_template.json`.
2. Extract `client_id`, engagement/topic, planning year, and any horizon year from the memo. If the memo gives a horizon, use it for projection fields.
3. Use the task-provided API base URL, usually `API_BASE`, and fetch only the advisory endpoints made available by the task environment.
4. Build a client data packet before calculating. You may use the bundled helper:

```bash
python scripts/fetch_case_data.py CLIENT_ID --out /tmp/advisory_case.json
```

The script reads `API_BASE`; if the harness gives the base URL another way, pass it with `--base-url`. If you are not running from the skill directory, call the script by its full path. If Python is not convenient, fetch the same endpoints manually.

## Data Sources

Use source authority field by field. Do not average conflicting values or blend old CRM data with current signed records.

- `SIGNED_PROFILE` normally controls household facts, profile values, goals, beneficiary count, filing status, marginal tax rate, planning year, liquidity, and estate value.
- `CUSTODIAN_EXPORT` controls retirement account balances, Roth/traditional splits, expected return, RMD start age, and recommended conversion period.
- `/api/life-insurance` controls proposed ILIT policy facts such as death benefit, premium, contribution date, owner, and existing-policy-transfer flag. When the answer template requires a policy source enum and the policy endpoint has no source type, map the governing policy/profile source from the source documents; signed profile is the default if no better document supplies policy authority.
- `/api/trust-candidates` controls GRAT/CRAT candidate parameters. In these tasks, trust-transfer asset facts commonly map to `ATTORNEY_MEMO` when the template asks for a controlling asset source.
- `ATTORNEY_MEMO` can control legal strategy, trust-transfer asset context, or attorney-coordination facts when those are the facts being requested.
- `CRM_NOTE` and stale intake records are fallback/background only unless no stronger source exists for a requested fact.
- `/api/policies/tax` and `/api/rmd-factors` are authoritative for planning constants and RMD divisors.

Set each `source_resolution` value to the source type that supplied the fact group actually used in the answer. Use only enum values allowed by the template.

## Calculations

Read [calculation-patterns.md](references/calculation-patterns.md) when the template includes Roth/RMD, ILIT, estate context, GRAT, CRAT, or estate-liquidity fields. The formulas there are reusable patterns from the staged examples and should be applied to new client data.

Keep money values as JSON numbers rounded to two decimals. Keep dates as ISO `YYYY-MM-DD` strings. Keep booleans as JSON booleans, not strings.

## Output Discipline

- Return only the final JSON object. No prose, code fences, citations, or notes around it.
- Include every key listed in `required_top_level_keys`; omit unsupported top-level sections only if the template does not require them.
- Use the exact enum strings and field names from the template.
- Do not invent extra narrative fields. Extra calculated fields are acceptable only when they appear in the answer family and are useful for the requested section; otherwise stay close to the template.
- Sort any list when the template says to sort it, especially `action_set`.
- Before finalizing, re-open the template and compare every required key, enum, date, number, and source-resolution field against the JSON you are about to return.
