---
name: ma-deal-workbench-json
description: Use when solving M&A deal workbench tasks that require fetching deal workbench API records and returning schema-conforming JSON legal work product, including buyer or seller issue registers, SPA or APA deviation matrices, closing packages, transition reviews, and committee escalation summaries.
---

# M&A Deal Workbench JSON

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Extract the exact `deal_id`, client side, requested deliverable, required enums, stable IDs, rounding rules, ordering rules, and top-level JSON shape.
2. Read the environment access note for the base URL. Fetch only the named deal and directly relevant playbook or policy records. Do not browse unrelated deals.
3. Use `scripts/fetch_deal_context.py` to gather the standard workbench bundle when helpful:

```bash
python3 scripts/fetch_deal_context.py --base-url "$TASK_ENV_BASE_URL" --deal-id "$DEAL_ID" --output deal_context.json
```

Pass `--playbook-id` or `--policy-id` if the prompt names one and the deal record does not.
4. Before drafting final JSON, read [references/deal-workbench-json.md](references/deal-workbench-json.md) for field mapping, issue classification, calculation, and validation rules.
5. Build an evidence map from the fetched records: deal economics, current draft terms, playbook rules or policy thresholds, consents, material contracts, regulatory facts, employees, cap table, diligence findings, benchmarks, risk estimates, documents, and notes.
6. Compare current draft terms to the client-side playbook or committee policy. Treat absent protective terms as issues when the playbook, policy, prompt, or surrounding deal data shows they are required.
7. Return only valid JSON matching the template. Include no prose, markdown, comments, citations, or extra keys unless the template allows them.

## Output Discipline

- Use stable IDs from the API records or the template. Use an empty source-term array for missing draft terms.
- Preserve template enum spelling exactly.
- Use integer dollars, requested percent precision, requested month/date formats, and the prompt-specified value basis.
- Validate the JSON syntax and shape before answering:

```bash
python3 -m json.tool answer.json >/dev/null
```

Do not copy example-specific values between matters. Recompute every amount and classification from the current deal records and the template.
