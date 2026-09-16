---
name: private-wealth-json
description: Structured JSON for private wealth advisory planning tasks. Use whenever the user needs a client-specific memo turned into exact JSON for Roth conversion and RMD summaries, ILIT Crummey funding cycles, GRAT vs CRAT comparisons, or estate liquidity plans, especially when a request memo and answer template are provided or source records conflict.
---

# Private Wealth JSON

Use this skill for advisory cases that require one exact JSON object and nothing else.

## Workflow

1. Read the request memo and answer template first.
2. Identify the analysis type, required top-level keys, and any stated planning horizon or dates.
3. If source data is needed, use the task-provided advisory API base URL and only the listed endpoints.
4. Resolve conflicts by source authority, not by averaging:
   - signed profile for goals, beneficiaries, and policy preferences
   - attorney memo for legal or planning assumptions and asset facts
   - custodian export for balances and holdings
   - CRM notes only if nothing better exists
   - stale intake only as a last resort
5. Populate every required field, keep enum strings exact, round USD to cents, and use ISO `YYYY-MM-DD` dates.
6. Return the final JSON object only. No prose, markdown, or code fences.

## Analysis types

Read [references/analysis-types.md](references/analysis-types.md) for the field map and type-specific rules.

## Final checks

- Match the template exactly.
- Keep `task_id` and `client_id` unchanged.
- Sort any `action_set` alphabetically.
- Make `conversion_years_positive` match `conversion_years`.
- Do not add extra keys or commentary.
