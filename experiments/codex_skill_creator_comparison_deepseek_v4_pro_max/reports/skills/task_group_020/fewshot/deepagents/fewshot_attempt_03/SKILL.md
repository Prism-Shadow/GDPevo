---
name: m-a-deal-workbench
description: "M&A deal analysis using the deal-workbench REST API at a configured base URL. Use when the task involves deal records (PRJ_ identifiers), draft terms, playbook rules, policy thresholds, risk estimates, benchmarks, cap tables, consents, employees, material contracts, regulatory records, diligence findings, or deal notes. Covers seller-side playbook issue registers, buyer-side SPA economics and closing packages, M&A committee escalation memos, carveout APA transition reviews, and SPA deviation matrices. Trigger on any request mentioning M&A, deal workbench, purchase agreement, APA, SPA, issue register, closing conditions, playbook review, escalation memo, deviation matrix, or deal analysis against the deal-workbench API."
license: MIT
compatibility: designed for deepagents-code
---

# M&A Deal Workbench

Work with the deal-workbench API at the base URL provided in `<TASK_ENV_BASE_URL>`. Gather deal records, draft terms, playbook rules, policy thresholds, risk estimates, benchmarks, and supporting records. Produce structured JSON outputs conforming to the provided answer template.

## Workflow

1. Read the task prompt and the answer template (`input/payloads/answer_template.json`) to understand the required output shape, allowed enums, and computation rules.
2. Call the workbench APIs to collect all relevant records. Start with broad endpoints (`/api/deals/<id>`, `/api/deals/<id>/terms`, playbook rules, policy thresholds, risk estimates) then drill into supporting data (consents, employees, contracts, regulatory, cap table, diligence, benchmarks, notes).
3. Cross-reference draft terms against playbook rules or policy thresholds. Compare values (percentages, months, dollar amounts, boolean flags) and classify each term's status.
4. Compute dollar amounts from the deal's headline purchase price unless a source explicitly overrides it. Round currency to integer dollars, percentages to the decimal places required by the template, months to integers.
5. Build the output JSON strictly matching the template schema. Use only the allowed enum values. Do not include narrative outside the JSON.

## Resources

- [API Endpoints](references/api_endpoints.md) — Full catalog of workbench API routes, resource shapes, and SQL access.
- [Business Patterns](references/business_patterns.md) — Computation rules, playbook/policy comparison logic, risk classification, priority ordering, and issue classification.
- [Task Workflows](references/task_workflows.md) — Task-type-specific guidance for issue registers, closing packages, escalation memos, transition reviews, and deviation matrices.
