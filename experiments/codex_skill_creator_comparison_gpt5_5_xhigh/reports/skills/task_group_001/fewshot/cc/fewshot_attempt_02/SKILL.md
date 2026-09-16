---
name: harborcrm-workflows
description: Process HarborCRM API tasks that ask for event handoffs, trade-show prospecting, badge reconciliation, import-batch cleanup, sponsor finance follow-up, or any JSON-only CRM report built from HarborCRM endpoints and a provided answer template.
---

# HarborCRM Workflows

Read the prompt and answer template first. Treat the template as the contract; use its keys, enums, ordering rules, and number formats exactly.

## Procedure

1. Identify the task family and read the matching section in [references/workflows.md](references/workflows.md).
2. Fetch the base record and the endpoint collections named in the prompt.
3. Join records on the most stable shared key available: `event_id`, `show_id`, `batch_id`, `account_id`, `contact_id`, normalized email, company name, or `row_id`.
4. Normalize contact data before matching: trim whitespace, lowercase emails, and strip phones to digits only.
5. Classify each record with only the values allowed by the prompt, template, or policy docs.
6. Sort every list exactly as specified.
7. Compute counts, totals, and due dates from the final surviving records.
8. Return one JSON object only, with no prose outside the JSON.

## Family rules

- Event handoff and reconciliation: derive sponsor status from the order and invoice state, exclude sponsor attendees and non-business or disqualified records, use the event lead-opportunity amount for qualified non-sponsor leads, keep campaign-member and CRM-action fields aligned with the same classification, and compute follow-up dates from the event end date plus the offsets in the event record.
- Trade-show prospecting: qualify only exhibitors that actually build or OEM-build the target platform family; exclude distributors, service-only firms, sensor-only vendors, research-only firms, and other near misses named by the template.
- Import cleanup: keep one winning row per duplicate group, preserve the winner's provenance, remove suppressed or unusable rows separately, and make the cleaned-contact totals agree with the import-action counts.

## Final checks

- Use template field names exactly.
- Use template-controlled strings only.
- Keep money fields as integer USD.
- Keep dates as `YYYY-MM-DD`.
- Keep emails lowercase and phones digits-only.
- Omit any field the template does not declare.
