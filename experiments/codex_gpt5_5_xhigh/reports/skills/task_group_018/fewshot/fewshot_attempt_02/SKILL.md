---
name: court-packet-reconciliation
description: Reconcile court hearing notes, finance queues, payment petitions, and portal records into clerk-ready JSON packets, including dispositions, fees, payment plans, placeholders, and form metadata.
---

# Court Packet Reconciliation

Use this skill when a task asks for a structured court closeout or packet answer from local notes plus the court portal.

## Workflow

1. Read `answer_template.json` first. Treat its keys, enums, ordering rules, and placeholder token as the contract.
2. Pull facts from the local payloads and, when provided, verify against the portal endpoints named in the prompt or environment file.
3. Resolve conflicts using this order:
   - signed order or explicit docket entry
   - hearing notes / sentencing notes
   - corroborating memo, petition, or intake sheet
   - draft queue / worksheet
   - stale or archived values only if the template or current policy explicitly requires them
4. Build only the fields the template asks for. Do not add commentary or extra keys.

## Reconciliation Rules

- Normalize identities, counsel labels, offense wording, and disposition status to the authoritative record.
- If counsel is actually appointed private, do not treat it as public defender work.
- If a field is required but not supported by the materials, use the exact placeholder string from the packet instructions and record it in the template's placeholder section when one exists.
- Never invent identifiers, contact details, office details, or license numbers.
- If a matter is continued, pending, or missing a signed order, keep it out of posted financial totals until the template says otherwise.

## Fees And Totals

- Use the current fee schedule or portal charge record, not an older worksheet amount.
- Exclude unsupported charges such as account-management, late, collection, DMV, returned-check, traffic-school, restitution without an order, or other items the materials do not support.
- Keep excluded amounts separate when the template includes exclusion fields.
- Sum only posted or disposed matters in batch totals.

## Payment Plans

- Use the approved monthly amount or policy-supported installment amount from the file.
- Compute installments from the supported total due after any down payment.
- The final payment is the remainder after full regular installments.
- Advance the final due date by the required interval from the first due date.
- Use the return-to-court date from the materials or policy; do not invent one.
- If a budget is supplied, compare disposable income to the policy band before classifying supportability.

## Output Rules

- Emit JSON only.
- Preserve the template's ordering rules.
- Use ISO dates and currency numbers rounded to two decimals.
- Keep form IDs and labels aligned with the portal or template metadata.
