---
name: court-ops-closeout
description: >-
  Prepare a court clerk closeout / financial packet (criminal sentencing
  register, traffic-violation payment plan, or post-sentencing installment &
  supervision order) by reconciling local case payloads against the Court
  Operations Portal REST API and emitting one JSON object that exactly matches a
  provided answer_template.json. Use when a task gives target case / citation /
  petition identifiers, local payloads (hearing notes, memos, worksheets,
  budgets, form excerpts), an answer_template.json, and a Court Operations Portal
  base URL (`<TASK_ENV_BASE_URL>` / `GDPEVO_ENV_BASE_URL`).
---

# Court Operations closeout / financial packet

You are acting as a court clerk. Each task gives you (a) target identifiers
(cases, citations, and/or petitions), (b) local payloads that often contain
drafts, stale carry-forwards, and conflicts, (c) a **Court Operations Portal**
REST API that is the authoritative CMS and current rule tables, and (d) an
`answer_template.json` that defines the exact output contract. Produce **one JSON
object** matching that template, with every value reconciled and audited.

The portal is authoritative for structured facts and current rules; the local
payloads tell you what the clerk saw and what happened in court. Your job is to
resolve conflicts correctly, apply the money/date math, exclude unsupported
items, hold un-signed matters, and emit strictly schema-conformant JSON.

## Files in this skill

- `references/portal_api.md` — every portal endpoint, its fields, how to filter,
  and which field is authoritative for what.
- `references/reconciliation_rules.md` — the full decision rules (authority
  hierarchy, fees, installments, holds, placeholders, license/probation). Read
  this before deciding any contested value.
- `scripts/installments.py` — computes the installment breakdown and schedule
  dates (first/final due, return-to-court). Use it instead of hand arithmetic.

## Workflow

1. **Read the prompt.** Extract: the portal base URL (from `<TASK_ENV_BASE_URL>`;
   the real value is in the environment's `environment_access.md` as
   `GDPEVO_ENV_BASE_URL`), the target identifiers, the listed portal endpoints,
   and the path to `answer_template.json`.

2. **Treat `answer_template.json` as the contract.** Extract and write down:
   the required top-level keys, each item's required keys, every enum and its
   allowed values, the ordering rules, currency precision, date/datetime/time
   formats, and the exact placeholder string. The output must contain **only**
   the keys the template lists, use enum values **verbatim** (never substitute
   prose for an enum), and follow the formats exactly.

3. **Read every local payload** in `input/payloads/` (hearing/closeout notes,
   audit/finance memos, worksheets/CSVs, petition & budget summaries, form
   excerpts). Note draft/stale/carry-forward flags and any explicit conflicts or
   instructions ("do not add …", "verify current schedule", "order not signed",
   "use placeholder for missing …").

4. **Query the portal for the authoritative record** of each target and the
   reference tables. Use exact filters (`?case_number=`, `?citation_number=`,
   `?petition_id=`, `?jurisdiction_code=`) and `/api/search?q=<name>` for
   identity confirmation. At minimum resolve: the jurisdiction; the authoritative
   case/citation/petition record; charges; docket entries (to confirm a signed
   disposition vs. a hold); the current fee schedule; the payment policy; and the
   form metadata — whichever the task needs. See `references/portal_api.md`.

5. **Reconcile using the source-of-authority hierarchy** in
   `references/reconciliation_rules.md` §1. In short: CMS wins for identity and
   structured sentence data; the current fee-schedule/policy/form tables win for
   money rules and form metadata; **hearing notes win for what happened in open
   court** (accepted plea/finding, count amendments, a departure pronounced or
   expressly rejected, whether a final order was signed); a corroborating memo
   settles counsel classification; draft/stale/carry-forward values are never
   authoritative. Record each audit finding's resolution source accordingly.

6. **Apply the domain computations** (reconciliation_rules.md §§3–8):
   - **Fees**: start from current-window fee-schedule rows; include mandatory
     fees and only-when-triggered conditional fees (PD user fee only for public
     defenders; charge-specific assessments only on the qualifying conviction
     count); include a fine only if actually imposed; **exclude** every
     unsupported/stale/discretionary fee and itemize exclusions with the schema's
     reason codes.
   - **Installments**: validate the monthly amount against the policy band and
     the budget (income − obligations), then run `scripts/installments.py` for
     the breakdown and dates; apply the policy's restitution priority and
     account-fee treatment.
   - **Traffic fine tiers**: map the citation's `violation_code` to the current
     `standard_fine` row; add the county surcharge once.
   - **License suspension / probation referral**: start dates, months, end dates,
     and whether a referral was actually ordered.
   - **Holds**: any matter without a signed final order is held/excluded with
     zeroed financials and null dates, counted separately.
   - **Placeholders**: use the exact placeholder string for form-required fields
     absent from all sources; never invent identifiers or contacts.

7. **Assemble the output strictly to schema.** Include only allowed keys; use
   enum values verbatim; apply every ordering rule (sort the arrays as directed,
   e.g. by case_number/citation_number/petition_id, and any secondary key);
   format all money to two decimals and all dates/datetimes/times per the
   template; use `null` exactly where the schema allows it (e.g. no disposition
   date for a held matter).

8. **Self-check before returning** (see checklist below). Then output the JSON
   object only — no markdown, no commentary — unless the template says otherwise.

## Output discipline

- Exactly one JSON object, matching the template's structure and key names.
- Only the keys the template defines; every enum value drawn verbatim from the
  template's allowed list.
- Money: numbers to two decimals. Dates: `YYYY-MM-DD`. Datetimes:
  `YYYY-MM-DDTHH:MM:SS`. Times: `HH:MM`. Use `null` only where permitted.
- Arrays sorted exactly per the template's ordering rules.

## Self-check

- [ ] Every required top-level key and every required item key is present.
- [ ] Every enum field uses an allowed value verbatim (no prose substitutes).
- [ ] Arrays are sorted per the ordering rules (primary and any secondary key).
- [ ] Currency has two decimals; dates/times use the required formats; `null`
      used only where allowed.
- [ ] Identity/counsel/charge/departure/status values reflect the correct
      authoritative source, not a draft/stale worksheet value.
- [ ] No stale/archived amount used; no unsupported fee posted; every excluded
      item has the right reason code.
- [ ] Any un-signed / deferred / continued matter is held (zeroed financials,
      null dates) and counted as held/excluded, not disposed.
- [ ] Installment breakdown and all schedule dates match
      `scripts/installments.py`; monthly validated against band + budget.
- [ ] Totals are internally consistent (case totals sum to register/batch
      totals; disposed + held counts add up).
- [ ] No invented identifiers or contacts; missing required fields use the exact
      placeholder string and are listed where the schema asks.
