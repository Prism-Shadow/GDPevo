---
name: finance-ops-reporting
description: Solve Crescent Finance Ops JSON reporting tasks from prompt, environment_access.json, request_memo.json, and answer_template.json. Use when asked to produce branch close, regional, compensation, payroll, or forecast reports from the staged API and return one strictly shaped JSON object.
---

# Finance Ops Reporting

## Workflow

1. Read `payloads/answer_template.json` first and treat it as the contract for keys, nesting, rounding, and list order.
2. Read `payloads/request_memo.json` to identify the report family, target ID, comparison periods, scenario, and any special treatment flags.
3. Read `payloads/environment_access.json` for `base_url` and the allowed endpoints. Use only those endpoints, plus `GET /api/manifest` when you need an index of branches, ensembles, productions, or other public entities.
4. Query the smallest set of objects needed. Prefer exact IDs from the memo; otherwise map names through the manifest or the relevant collection endpoint.
5. Assemble the final object with the exact keys, nesting, and list order from the template. Do not add prose or helper fields.
6. Round currency to 2 decimals. Round percentages and ratios to 4 decimals. Keep intermediate values unrounded until the end.
7. Reconcile totals, rankings, and counts against the source data before emitting the answer.

## Report Families

See [references/reporting-playbook.md](references/reporting-playbook.md) for endpoint selection and calculations by report type.
