---
name: wealth-advisory-json
description: Produce JSON-only private wealth advisory planning outputs from the task-group advisory API, including Roth conversion and RMD summaries, ILIT Crummey funding checks, GRAT versus CRAT comparisons, and estate liquidity action plans. Use when a prompt asks for a client-specific structured planning object, exact schema compliance, source resolution across conflicting records, or any similar advisory memo that must be returned as JSON rather than prose.
---

# Wealth Advisory JSON Planner

Use this skill for client-specific advisory outputs that must exactly follow a JSON schema.

## Workflow
1. Read the prompt, request memo, and answer template first.
2. Identify the template family and the required top-level keys.
3. Query `API_BASE` for the controlling records and supporting policy data.
4. Resolve conflicts by source authority, not by recency. See [references/workflow.md](references/workflow.md).
5. Build the final object with the exact keys, enums, number types, and date formats from the template.
6. Return JSON only.

## Output rules
- Use JSON numbers for USD amounts and round to cents.
- Use ISO `YYYY-MM-DD` for dates.
- Preserve template key names exactly.
- Do not add prose, markdown fences, comments, or extra keys.
- Sort any template-specified ordered list exactly as requested.
- If a value is missing or conflicting, re-check the governing source instead of guessing.

## Source hierarchy
- Prefer signed profiles for intent, beneficiaries, and elections.
- Prefer attorney memos for legal directives when they explicitly govern the field.
- Prefer custodian exports for balances, holdings, and account facts.
- Treat CRM notes and stale intake as fallback context only.
- Record the controlling source in `source_resolution` whenever the template asks for it.

## Template families
See [references/workflow.md](references/workflow.md) for the field groups and endpoint map for each advisory template family.
