---
name: court-closeout-reconciler
description: "Prepare clerk-ready JSON court closeout, disposition register, payment plan, probation referral, and license/payment order packets from local payloads plus a Court Operations Portal. Use for criminal or traffic matters requiring reconciliation of case/citation status, charges, docket entries, fee schedules, payment policies, forms, financial petitions, placeholders, exclusions, and batch totals against an answer_template.json."
---

# Court Closeout Reconciler

## Core Workflow

1. Read the user prompt, then read `input/payloads/answer_template.json` before drafting any output. Treat the template as the contract for top-level keys, enum values, null handling, date formats, currency formats, and sorting.
2. Inventory and read every file in `input/payloads/`. Parse JSON/CSV as structured data, and use Markdown notes as evidence with headings tied to target matters.
3. Identify target matter keys from the prompt and payloads: case numbers, citation numbers, petition IDs, jurisdiction codes, hearing dates, disposition dates, and named forms.
4. Query the Court Operations Portal named in the prompt, or read `environment_access.md` if that file is present and the prompt uses a placeholder base URL. Use only the listed task-environment endpoints.
5. Reconcile evidence matter by matter. Record conflicts and exclusions explicitly when the requested answer shape provides fields for them.
6. Assemble JSON only. Do not include Markdown, comments, citations, or explanatory prose outside fields requested by the template.

## Portal Collection

Use portal data to verify, not to replace stronger local hearing facts. Useful endpoints commonly include:

- `/api/jurisdictions` for court names, jurisdiction codes, local policy references, and time zones.
- `/api/cases`, `/api/citations`, `/api/charges`, and `/api/docket-entries` for identity, status, charges, pleas, findings, sentences, and signed-order clues.
- `/api/fee-schedules` for current mandatory costs, assessments, surcharges, and stale schedule detection.
- `/api/payment-policies` for account fees, minimum and maximum payments, first-due rules, restitution priority, and return-to-court offsets.
- `/api/forms` for form IDs, labels, required fields, revision dates, and placeholder instructions.
- `/api/financial-petitions` for petition sequence, balances, requested payment amount, budget, default status, and probation/license fields.
- `/api/search` for narrow target lookup when full endpoint responses are large.

Fetch target records by exact identifiers whenever possible. If an endpoint does not support filters, fetch the endpoint once and filter locally. The helper script [scripts/court_packet_helpers.py](scripts/court_packet_helpers.py) can do this from the skill package root:

```bash
python scripts/court_packet_helpers.py fetch \
  --base-url "$TASK_ENV_BASE_URL" \
  --endpoint cases \
  --ids CASE_OR_CITATION_OR_PETITION_ID
```

## Evidence Priority

Apply this conflict order unless a local template or prompt gives a more specific rule:

1. `answer_template.json` controls the shape and allowed vocabulary.
2. Signed courtroom/hearing notes control what was accepted, found, continued, deferred, ordered, waived, or held.
3. Portal CMS records control verified identity, case/citation status, charge metadata, docket entries, current forms, current schedules, and policy values.
4. Corroborating local memos and form excerpts resolve shorthand, local labels, placeholder text, and clerk-specific handling.
5. Finance queues, old worksheets, scratchpads, sticky notes, and intake carry-forward values are tentative. Use them only when supported by current schedules, current policy, and the hearing/order record.

Do not invent identifiers, contact details, account numbers, attorney/probation office details, charges, fees, conditions, or balances. When a required form field is missing and the materials provide a placeholder rule, use that exact placeholder. Otherwise use null only if the template permits it.

## Disposition Rules

- Enter a disposed/registerable matter only when the hearing notes or docket show a final order, accepted plea/finding, or pronounced disposition.
- Hold or exclude matters with unsigned orders, continued status, incomplete plea paperwork, no final order, or pending disposition. Do not post financials for those matters unless the template explicitly asks for a held amount.
- Use hearing notes for amended counts and courtroom outcomes. If a controlled-substance or other special-assessment charge was amended away or dismissed, do not assess charge-specific fees for the old count.
- Classify counsel from the verified record plus clarifying notes. Appointed private counsel is not the same as public defender for user-fee eligibility.
- For missing DOB or identity fields, use verified CMS data if available. If genuinely missing and required, use the template's placeholder/verify action rather than borrowing from search results.

## Financial Rules

- Select fee schedules by jurisdiction, fee type, violation/statute/offense, mandatory flag, and effective date covering the disposition/hearing date. Ignore stale schedules and unsupported maximum notes unless the current schedule or order adopts them.
- Include only fines and costs pronounced in the hearing/order or mandated by the current schedule for the convicted/found violation.
- Exclude account-management, collection, late, DMV, returned-payment, restitution, attorney, reporter, copy, certification, program, and similar charges unless a current policy, fee schedule, triggering event, or order directly supports them.
- Keep unsupported or stale charges out of starting balances. If the template has an exclusions list, list each excluded charge/item using its allowed enum and sort rule.
- Compute batch totals from posted/assessed matters only. Held, continued, pending, or excluded matters normally contribute zero to posted totals.

## Payment Plans And Dates

Use approved/requested payment terms only after checking policy bands and budget support:

- Disposable income is income minus obligations when budget fields are present.
- A requested installment is supportable when it fits policy minimum/maximum and does not exceed available disposable income, unless the template has a different classification rule.
- Balance equals fines/costs plus restitution plus any policy-supported account fee, minus down payment. Do not include excluded fees.
- When restitution exists and policy or petition supports priority, apply payments to restitution before fines/costs; otherwise use the template's allowed application enum.
- Installment math: `total_installments = ceil(balance_after_down_payment / regular_installment_amount)`. Full installments are the number of regular payments before any smaller remainder. If there is no remainder, the final payment equals the regular installment.
- Final due date is the first due date advanced by `total_installments - 1` intervals. For monthly schedules, preserve the day-of-month when possible and clamp to month end if needed.
- Return-to-court dates come from the petition/order if supported; otherwise compute from policy offset after the final due date when the template requests it.
- License suspension usually starts from the conviction/disposition date when the order says so; do not substitute release or petition dates unless the materials direct that basis.

The helper can compute schedule and month-addition details:

```bash
python scripts/court_packet_helpers.py schedule \
  --balance 1234.56 \
  --installment 80.00 \
  --first-date 2027-02-10 \
  --interval monthly \
  --return-offset-days 45

python scripts/court_packet_helpers.py add-months --date 2027-01-31 --months 1
```

## Forms And Placeholders

- Use current portal form metadata for `form_id`, label, revision, required fields, and placeholder instructions. Use local form excerpts for exact visible labels when the portal does not expose them.
- Use citation number as account reference only when the local form/policy says no separate case or account number exists.
- For probation referral packets, prepare a referral only when supervised probation or a signed referral order is present. If no referral was ordered, use the template's not-ordered/null values.
- For license/payment order packets, include driver license placeholders only when the license number is required but absent from the case materials.
- Sort placeholder field lists exactly as the template requires, often by field name or case number with nested missing-field lists alphabetized.

## Output Check

Before finalizing:

- Confirm every required top-level key is present and no extra top-level keys are added unless the template includes them.
- Confirm every enum value exactly matches the template spelling.
- Confirm dates are ISO strings or null only where allowed; datetimes use local ISO format when requested.
- Confirm currency fields are JSON numbers rounded to cents. JSON may not preserve trailing zeros, but the numeric value must be cent-rounded.
- Confirm all requested lists are sorted by the template's rule.
- Recompute totals independently from the matter entries.
- Return JSON only.
