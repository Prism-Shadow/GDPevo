---
name: apexcloud-retention-ops
description: Analyze ApexCloud Retention Operations API prompts that require JSON-only retention, revenue, receivables, churn, QBR, or action-board outputs. Use when a task asks you to query the task environment API, reconcile account data, rank renewal or churn risk, summarize monthly metrics, map overdue receivables to CRM accounts, or produce a structured board, packet, or validation readout from a provided template.
---

# ApexCloud Retention Ops

## Workflow

1. Read the prompt and the answer template first.
2. Mirror the template shape exactly. Keep scaffold keys such as `policy_codes` or `model_policy_codes` when present.
3. Use the task's base URL and only the allowed ApexCloud endpoints needed for the requested fields.
4. Normalize values before writing JSON:
   - currency: 2 decimals
   - percentages: 1 decimal
   - probabilities: 3 decimals
   - counts: integers
   - dates: `YYYY-MM-DD`
5. Follow the prompt's ordering rule. If it says "top N" or "rank", sort by the primary score or urgency with stable tie-breakers.
6. Copy controlled labels exactly as written. Do not paraphrase enum values.
7. Return JSON only. Do not add commentary, markdown, or extra keys.

## Data Map

Read [references/field-map.md](references/field-map.md) for endpoint families, common field sources, controlled vocabularies, and ordering conventions.

