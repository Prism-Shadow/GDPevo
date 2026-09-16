---
name: wealth-advisory-planning
description: Build client-specific private-wealth advisory JSON for Roth conversion and RMD summaries, ILIT Crummey funding cycles, GRAT versus CRAT comparisons, and estate-liquidity action plans from the staged advisory API. Use when a prompt asks for a strict JSON object that reconciles signed profiles, custodian exports, life-insurance policies, trust candidates, tax constants, and RMD factors.
---

# Wealth Advisory Planning

## Workflow

1. Read `references/environment.md` to connect to the advisory API.
2. Read `references/workflow.md` before calculating any fields.
3. Resolve source conflicts, compute only the schema fields for the current analysis type, and return JSON only.

## Output Rules

- Match the required keys exactly.
- Keep dollar amounts as JSON numbers rounded to cents.
- Emit dates as `YYYY-MM-DD`.
- Preserve the provided `task_id` and `client_id`.
