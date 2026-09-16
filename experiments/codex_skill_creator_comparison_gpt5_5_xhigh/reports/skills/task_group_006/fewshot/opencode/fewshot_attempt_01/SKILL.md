---
name: procureops-control-file-reconciler
description: Reconcile ProcureOps API records and local task memos into strict JSON control files for nomination readiness packets, receiving closeouts, AP close reconciliations, change-control decisions, and AP release/hold reviews. Use this skill whenever a prompt mentions ProcureOps, `<TASK_ENV_BASE_URL>`, a local memo/payload folder, or an `answer_template.json` and asks for exact JSON only.
---

# ProcureOps Control File Reconciler

Use this skill for structured ProcureOps tasks that end in a single JSON object.

## Workflow
1. Read the prompt, the local memo or payload files, and the answer template together. Treat the template as the schema contract.
2. Use the ProcureOps API as the source of truth for live records. Use the runner-provided base URL from the task environment; do not hardcode it.
3. Identify the task family and follow [references/procureops-playbook.md](references/procureops-playbook.md).
4. Populate the JSON exactly as the template requires. Do not add prose, markdown, or extra keys.
5. Before finalizing, verify sorting, rounding, enum values, and source IDs against the template.

## Non-negotiable rules
- Prefer API records over memo wording when they differ.
- Use the memo for scope, aliases, cutoff dates, and local hints the API cannot express.
- Keep set-like arrays deduplicated and sorted ascending unless the template says otherwise.
- Preserve the template's row ordering rules for lists and tables.
- Round USD amounts to cents and ratios or percentages to the template precision.
- Copy enum values exactly from the template and the live records.
- Include every required source ID or evidence ID the template asks for.
- Return only the JSON object.

## Common endpoints
Use the endpoints named in the task environment for programs, suppliers, items, contracts, purchase requisitions, purchase orders, receipts, AP invoices, AP payments, approvals, budget snapshots, and vendor risk events.
