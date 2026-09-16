---
name: harborcrm-structured-json
description: Analyze HarborCRM event, trade-show, sponsor, import-batch, and CRM reconciliation tasks that require producing one JSON object from API data and a provided answer template. Use when a prompt references HarborCRM endpoints such as `/api/events`, `/api/tradeshows`, `/api/import_batches`, `/api/crm`, `/api/finance`, or `/api/policies` and asks for JSON-only output with filtering, classification, ranking, deduplication, normalization, counts, or follow-up summaries.
---

# HarborCRM Structured JSON

## Workflow

1. Read the prompt and `input/payloads/answer_template.json` first.
2. Treat the template as the contract for required keys, allowed values, list ordering, and numeric precision.
3. Use the runner-provided base URL. Query only the endpoints named in the prompt; use `/api/manifest` or `/api/policies` only when you need endpoint discovery or controlled values.
4. Identify the task family:
   - event / sponsor handoff
   - trade-show prospecting
   - import-batch cleanup
   - badge / campaign-member reconciliation
5. Build the final object in template order. Keep qualified records, exclusions, and summaries separate.
6. Normalize exactly as the schema asks. Lowercase emails only when requested, strip phones to digits only when requested, and use `null` vs empty string exactly as specified.
7. Apply prompt-specific ranking, sizing, and inclusion rules verbatim. Do not replace explicit instructions with generic heuristics.
8. Sort every array exactly as required, then recompute totals and counts from the final included records.
9. Return one JSON object only. Do not add prose, fences, or undeclared fields.

## Event And Sponsor Tasks

- Separate sponsor records from qualified non-sponsor leads.
- Preserve sponsor status, invoice or package amounts, balances, campaign-member actions, and follow-up tasks when the template asks for them.
- Exclude sponsor attendees, inactive or canceled sponsor records, non-business badges, and already-disqualified CRM records from lead lists.
- Keep `crm_action` fields aligned with whether the account or contact already exists in CRM.

## Trade-Show Prospecting

- Use exhibitor and meeting-interest data to decide qualification.
- Keep allowed platform enums, relationship types, and priority tiers exactly as written in the template.
- Sort platform lists in the enum order shown by the template.
- Keep near misses in the exclusion list with the controlled reason instead of dropping them.

## Import Cleanup

- Deduplicate on the key implied by the prompt or template, then keep the winning row as the cleaned record.
- Keep removed rows with explicit reasons such as duplicate, missing contact, or suppressed.
- Count surviving actions and campaign-member imports from the cleaned set only.

## Final Check

- Confirm that every required key is present.
- Confirm that no undeclared key appears.
- Confirm that every enum value is valid.
- Confirm that every list is sorted correctly.
- Confirm that summary counts match the emitted records.
