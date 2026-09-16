---
name: apex-retention-ops
description: Analyze ApexCloud Retention Operations API tasks that ask for JSON retention queues, QBR packets, receivables reviews, pipeline summaries, high-touch action boards, or churn export rankings. Use when prompts mention ApexCloud, TASK_ENV_BASE_URL, account metrics, tickets, NPS, billing snapshots, A/R aging, opportunities, HR or event summaries, or churn CSV exports and require controlled enums, policy codes, ranking, or deterministic precision.
---

# Apex Retention Ops

## Workflow

1. Read the prompt and the provided answer template first.
2. Query only the task environment endpoints that the prompt calls for.
3. Preserve the template shape exactly, including any extra top-level keys.
4. Use the live API as the source of truth; do not infer values from memorized examples.
5. Format numbers to the precision the prompt requests and return JSON only.

## Core Rules

- Use billing snapshots for current ARR when the task asks for ARR or exposure.
- Use account profile fields for segment, region, renewal date, tenure, lifecycle status, and owner context.
- Use account metrics for monthly revenue and product usage.
- Use ticket and NPS endpoints for operational health; do not rely on rolled-up fields when the prompt asks for month-level detail.
- Use the reference file for the account linking, receivables, pipeline, and scoring rules.
- When a policy code field offers pipe-delimited choices, select the option that matches the standard operating rule in the reference.

## Resources

- [Rules and heuristics](references/apexcloud_rules.md)
- [Live fact helper](scripts/apex_retention_facts.py)

