---
name: court-packet-reconciliation
description: Reconcile court hearing notes, case records, fee schedules, payment policies, forms, petitions, and docket data into strict JSON clerk packets. Use when preparing criminal, traffic, probation, sentencing, closeout, or payment-plan outputs that must cross-check local materials against a court portal, resolve conflicting sources, recompute fees or schedules, preserve placeholders, and match a provided schema exactly.
---

# Workflow
1. Read the prompt, answer template, and every local payload before deciding anything.
2. Classify each source by role: hearing notes or sentencing intake, clerk memo or worksheet, finance queue or petition summary, form excerpt, and portal record.
3. Query the portal only for unresolved case, charge, docket, form, fee schedule, payment policy, or petition details.
4. Resolve conflicts by precedence:
   - signed order or current portal record
   - courtroom hearing notes or sentencing/probation intake
   - corroborating memo
   - clerk worksheet, queue export, or draft sheet
   - stale archive or carry-forward value
5. Treat missing or unsigned final orders as hold, pending, or excluded items. Do not post them into a disposed register.

# Financial Rules
- Recompute amounts from the current fee schedule and payment policy, not from archived worksheet amounts.
- Exclude charges that are stale, unsupported, not triggered, or not ordered.
- Keep unsupported add-ons separate from posted totals and identify them explicitly when the schema asks for exclusions.
- Compute installment counts, final installment amounts, and due dates from the approved balance, down payment, and regular payment amount.
- Use the case or citation number as the account reference when no separate account exists.

# Identity, Status, and Forms
- Correct names, DOBs, counsel type, plea, charge disposition, and departure status from the best authoritative source.
- Do not borrow identifiers or DOBs from similarly named cases.
- Use the exact placeholder text required by the materials for missing identifiers or contact details; do not invent values.
- Use conviction date, not release date, for suspension or referral consequences unless the schema says otherwise.
- Use current form IDs and labels from the portal, and keep required label names exactly as shown in the source materials.

# Output Rules
- Return JSON only.
- Match the schema exactly, with no extra keys.
- Sort arrays by the template rules.
- Use ISO dates and numeric currency values rounded to two decimals.
- Leave absent dates null only when the schema allows it.
