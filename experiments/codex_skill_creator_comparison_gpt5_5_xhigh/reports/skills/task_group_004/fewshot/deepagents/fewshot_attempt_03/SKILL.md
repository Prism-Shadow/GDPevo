---
name: apexcloud-retention-ops
description: Structured JSON reporting from the ApexCloud Retention Operations API and churn exports. Use when a prompt asks for a renewal-risk queue, retention board, QBR metrics packet, receivables and pipeline review, or churn model validation and candidate ranking from the task environment, billing snapshots, AR aging, tickets, NPS, opportunities, HR summary, event performance, or churn CSV files.
---

# ApexCloud Retention Ops

Use this skill for ApexCloud reporting tasks that must return JSON only.

## Workflow

1. Identify the requested report shape from the top-level keys in the template.
2. Read [references/playbook.md](references/playbook.md) for the matching workflow.
3. Pull only the endpoints the workflow needs from the task environment base URL in the prompt.
4. Preserve template keys, ordering, rounding, null handling, and controlled labels exactly.
5. Return JSON only.
