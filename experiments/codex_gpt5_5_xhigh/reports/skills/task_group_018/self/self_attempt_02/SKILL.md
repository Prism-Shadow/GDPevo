---
name: court-packet-reconciliation
description: Reconcile court closeout, sentencing, traffic, petition, and post-disposition packet materials into strict schema-matched JSON. Use when a task combines hearing notes, docket entries, case files, intake worksheets, petitions, fee schedules, payment policies, form metadata, or portal records and requires conflict resolution, payment-plan math, unsupported-fee exclusion, placeholder handling for missing identifiers, and ordered structured output.
---

# Court Packet Reconciliation

## Workflow
1. Read the schema or answer template first. Note required keys, enums, ordering rules, date and currency formats, and any required placeholder text.
2. Read every provided local payload completely. Treat signed orders, entered docket notes, current case records, current fee schedules, payment policies, and form metadata as controlling over drafts, queue exports, scratchpads, or legacy worksheets.
3. If a court portal is provided, verify the matter against the relevant endpoints before finalizing:
   - case, citation, charge, docket, fee schedule, payment policy, form, and search endpoints as available
   - use search only to resolve identifiers or locate the current record
4. Resolve conflicts by source priority:
   - entered judgment, signed order, or docket entry
   - hearing notes or sentencing intake
   - current portal case, charge, fee, policy, and form records
   - local memo, petition, or worksheet
   - draft, archived, stale, or carry-forward values
5. Treat abbreviations and shorthand as non-authoritative until checked against the record. Confirm identity, counsel type, plea, disposition, departure status, and fee eligibility before posting.
6. If a matter is continued, deferred, pending, unsigned, or otherwise not finally entered, keep it out of the disposed register or final posting set and mark it according to the template.
7. Include only charges and fees supported by the current record and policy. Exclude stale, draft-only, unsupported, or not-in-order items, even if a worksheet carries them forward.
8. For payment plans, compute totals from the supported balance only. Use the approved payment amount, first due date, installment count, and any final remainder installment derived from the balance and policy.
9. Use the matter identifier as the account reference only when the local form or prompt says no separate account number exists.
10. When a required field cannot be completed from the case file, use the exact placeholder text specified by the materials. Never invent identifiers, contact details, or office details.
11. Keep output strictly inside the requested JSON shape. Preserve enum values exactly, sort arrays as instructed, round money to two decimals, and use ISO dates.

## Posting Rules
- Prefer the court record over local worksheets when they disagree.
- Prefer current fee schedules and payment policies over old rate tables, archived assessments, or scratch notes.
- Treat explicit no-departure language on the record as controlling.
- Treat counsel abbreviations like `PD` or `APD` as labels to verify, not final classifications.
- Use audit findings or exclusions to record genuine conflicts, not every source discrepancy.

## Budget And Payment Plans
- For budget review fields, compute monthly disposable income as income minus obligations.
- Compare the requested or selected payment amount against both the policy band and disposable income.
- Classify support based on the template's allowed values.
- For installment plans, use only the approved balance after excluding unsupported charges.
- If the balance does not divide evenly by the regular installment amount, record the remainder as the final payment amount.
- If a form says a citation, case number, or other matter ID can serve as the account reference, copy that rule exactly.

## Formatting Rules
- Use `YYYY-MM-DD` for dates.
- Use `YYYY-MM-DDTHH:MM:SS` only when a datetime is required.
- Keep values numeric where the schema expects numbers.
- Do not add commentary outside the JSON result.
