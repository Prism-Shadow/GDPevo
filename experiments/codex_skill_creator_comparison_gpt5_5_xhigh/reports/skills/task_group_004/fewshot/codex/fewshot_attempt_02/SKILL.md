---
name: apexcloud-retention-ops
description: Produce exact JSON reports from the ApexCloud Retention Operations API and churn export files. Use when a prompt references the task environment, asks for renewal-risk, QBR, receivables, retention-board, or churn-validation outputs, or needs data assembled from /api/accounts, /api/opportunities, /api/finance/ar-aging, /api/hr/summary, /api/events/performance, or /exports/churn/*.csv.
---

# ApexCloud Retention Ops

## Workflow
1. Read the prompt and answer template first. Treat the template as the schema contract.
2. Identify the report family, then follow [report-playbook.md](references/report-playbook.md).
3. Use the task environment from `environment_access.md` (`http://task-env:9004/`) for live data.
4. Return JSON only. Preserve key order, list length, enum vocab, sort order, dates, and numeric precision.
5. Derive every value from the live data or prompt constraints. Do not reuse example outputs.
6. Prefer posted billing snapshots for current ARR and overdue balance calculations when an as-of date is given.

## Rules
- Match template fields exactly; do not add commentary or extra keys.
- Use the prompt's controlled labels and date constants verbatim.
- Join A/R rows to accounts by legal name, display name, or aliases before marking `linked`.
- Keep any `policy_codes` block intact and select the code token that matches the workflow you used.
