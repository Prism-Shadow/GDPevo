---
name: harborcrm-data-workflows
description: Produce exact JSON handoffs from HarborCRM API data for sponsor reconciliations, trade-show prospecting, and import-batch cleanup. Use when a prompt mentions HarborCRM, the runner-supplied base URL, event sponsors, invoices, badges, trade-show exhibitors, meeting interest, CRM account/contact matching, or import batches and requires an answer that must match a provided JSON template exactly.
---

# HarborCRM Data Workflows

Use this skill when the task is to turn HarborCRM API data into an exact JSON deliverable.

## Start from the template

- Read `input/payloads/answer_template.json` first.
- Treat required keys, enums, ordering, and nullability as the contract.
- Do not add fields.
- If the template shape changes, follow the template rather than reusing a previous answer shape.

## Identify the family

- If the template has `sponsor_statuses`, `qualified_lead_accounts`, `follow_up`, or `crm_action_counts`, use the sponsor-handoff workflow.
- If it has `qualified_exhibitors` / `excluded_near_misses` / `aggregate_counts` or `ranked_leads` / `excluded_exhibitors`, use the trade-show prospecting workflow.
- If it has `clean_contacts` / `duplicate_summary` / `removal_summary`, use the import-cleanup workflow.
- See [references/patterns.md](references/patterns.md) for the exact rules.

## Query only what you need

- Use the runner-supplied base URL from the prompt or environment note.
- Read `/api/policies` whenever the prompt mentions controlled enums, platform coverage, or qualification rules.
- Pull CRM records before deciding create vs update vs exclude.

## Normalize before comparing

- Emails: trim and lowercase.
- Phones: strip everything except digits.
- Dates: keep ISO `YYYY-MM-DD`.
- Money and counts: integer USD / integer counts.
- Preserve `null` only when the template allows it; otherwise use the template’s empty-string convention.

## Finish cleanly

- Sort exactly as the template asks.
- Emit JSON only.
- Recheck that every count is derived from the records you actually included or excluded.
