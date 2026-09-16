---
name: court-closeout-reconciler
description: Reconcile court disposition closeout, sentencing, traffic, payment-plan, and post-sentencing packet tasks using local clerk/hearing payloads plus a Court Operations Portal API. Use when Codex must return schema-conformant JSON for case or citation dispositions, fee registers, payment petitions, form fields, placeholders, docket actions, and batch totals.
---

# Court Closeout Reconciler

## Core Workflow

1. Read the user prompt, `answer_template.json`, and every local payload before computing any answer fields.
2. Extract the target matter identifiers, jurisdiction, hearing or disposition date, and required portal endpoints.
3. Query the Court Operations Portal with exact identifiers. Prefer endpoint-specific filters over broad searches:
   - `/api/cases?case_number=...`
   - `/api/charges?case_number=...`
   - `/api/docket-entries?case_number=...`
   - `/api/citations?citation_number=...`
   - `/api/financial-petitions?petition_id=...`
   - `/api/fee-schedules?jurisdiction_code=...`
   - `/api/payment-policies?jurisdiction_code=...`
   - `/api/forms?jurisdiction_code=...`
4. Use `/api/search?q=...` only as a fallback or cross-check with an exact known case, citation, or petition identifier. Do not pull unrelated matters into the evidence set.
5. Build a per-matter evidence table from local notes, memos, worksheets, portal case/citation records, charges, docket entries, fee schedules, policies, forms, and petitions.
6. Reconcile conflicts using [reconciliation_rules.md](references/reconciliation_rules.md).
7. Use [court_math.py](scripts/court_math.py) for installment schedules, month-based due dates, license end dates, and budget-band checks when arithmetic is nontrivial.
8. Return JSON only, matching the template exactly.

## Source Precedence

- Treat signed final hearing notes, disposition notes, or docket/order status as controlling for plea, finding, conviction, sentence, continuance, and whether financial posting is allowed.
- Treat portal case/citation records as the preferred source for CMS identity, jurisdiction, status, counsel classification, case dates, and petition records unless a local correction is specifically corroborated.
- Treat current portal fee schedules, payment policies, and form metadata as controlling over finance queues, scratchpads, obsolete form footers, stale worksheets, and unchecked sticky notes.
- Treat local audit memos and supervisor notes as conflict flags. Use them to identify what must be verified, but post only values supported by final hearing/order facts, portal records, or current policy.
- Do not invent missing identifiers, contact details, account numbers, probation office details, attorney details, or judge details. Use the placeholder required by the template or payload, commonly `TBD from case file`.

## Portal Discipline

Query all target identifiers explicitly, including matters that appear pending, deferred, or held. Empty search results do not prove absence if an endpoint-specific route exists; for citations, call `/api/citations` directly.

For fee schedules, filter by jurisdiction and then select rows that are effective on the disposition or citation hearing date. Exclude expired rows unless the template asks to report stale or unsupported charges.

For forms and policies, filter by jurisdiction and use current metadata for form IDs, labels, required fields, placeholder handling, account fees, payment bands, restitution priority, first due dates, and return-to-court offsets.

## Output Rules

- Follow every required key, enum value, ordering rule, and null/placeholder instruction in `answer_template.json`.
- Use ISO `YYYY-MM-DD` dates and local `YYYY-MM-DDTHH:MM:SS` datetimes.
- Emit money as JSON numbers rounded to cents, not strings.
- Sort arrays by the template rule. If no rule is provided, sort deterministically by the matter identifier or field name.
- Include only supported fees in posted totals. Excluded, held, pending, and unsupported items should contribute `0.00` unless the schema asks for their original unsupported amount.
- Recompute all totals from the emitted line items after exclusions and holds are applied.
- Preserve schema-specific names. For example, do not substitute prose for enum values, and do not rename fields to a friendlier label.

## Math Helper

Run the helper from the skill directory, or reference the same script by its absolute path:

```bash
python3 scripts/court_math.py schedule --total 1250 --installment 100 --first-due 2026-02-15 --return-offset-days 60
python3 scripts/court_math.py add-months --start-date 2026-01-10 --months 12
python3 scripts/court_math.py support --income 1800 --obligations 1300 --installment 75 --min-monthly 50 --max-monthly 100
```

Use the helper output as arithmetic evidence, then map the field names to the active answer template.
