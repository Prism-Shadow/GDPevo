---
name: court-closeout-packet
description: >-
  Produce a clerk-ready JSON closeout/disposition/financial packet for a court
  matter by reconciling local materials (hearing notes, audit memos, finance-queue
  or worksheet extracts, petition/budget summaries, form excerpts) against the
  read-only "Court Operations Portal" API, then emitting output that matches the
  task's answer_template.json exactly. Use for criminal sentencing closeouts,
  traffic-citation closeouts + payment plans, and post-sentencing/financial
  petition packets (installment orders, probation referrals, license-suspension
  orders). Triggers: a prompt that names target case/citation/petition ids, points
  at a portal base URL with GET /api endpoints, attaches payloads, and asks for one
  JSON object matching answer_template.json.
---

# Court closeout packet

You are a deputy clerk. Turn messy intake material + an authoritative court portal
into one exact JSON object. The whole job is **reconciliation**: local worksheets
and queues are drafts to be audited; the signed court record and the portal are the
truth. Getting the source-precedence right, posting only supported money, and
matching the template exactly is the entire score.

## Read these first
- `references/portal_reference.md` — every endpoint, the fields you use, and the
  decoys the portal deliberately plants.
- `references/reconciliation_rules.md` — the precedence ladder and all the domain
  rules (fees, exclusions, placeholders, charge summaries, payment math, totals).
- `scripts/finance_math.py` — deterministic installment + date arithmetic. Use it;
  do not hand-compute schedules.

## Workflow

1. **Parse the prompt.** Note the court/county, the hearing/disposition date, and
   **every target id** (case, citation, and/or petition). Note which portal
   endpoints the prompt lists — that hints at the answer shape.

2. **Read every payload** in `input/payloads/`, including `answer_template.json`.
   The template is the contract: its `required_top_level_keys`, nested keys,
   enums, ordering rules, and currency/date rules define exactly what to output.
   Read it before doing any work and re-check it at the end.

3. **Reach the portal.** Get the base URL from `environment_access.md`
   (`GDPEVO_ENV_BASE_URL`, the value for `<TASK_ENV_BASE_URL>`). No credentials.
   Always filter by exact id (`?case_number=`, `?citation_number=`,
   `?petition_id=`, `?jurisdiction_code=`); use `/api/search?q=` only to discover
   related rows, then confirm the exact id. Pull, per target: the CMS row
   (`cases`/`citations`/`financial-petitions`), its `charges`, and — using that
   row's `jurisdiction_code` — the `fee-schedules`, `payment-policies`, and
   `forms`. Map county→`jurisdiction_code` via `/api/jurisdictions` if unknown.

4. **Reconcile** each matter with the precedence ladder (see the rules file):
   signed court record > portal CMS > portal schedules/policies/forms > local
   worksheet. Every place a lower source conflicts with a higher one becomes an
   **audit finding**. Watch the decoys: `attorney_label_raw`, stale
   `charges.disposition`, expired fee rows, similar-name DOBs.

5. **Decide status & post money.** Signed order → disposed, post financials from
   the **current** schedule (court cost, imposed fine, PD user fee only if counsel
   is public_defender, drug/lab assessment only on an actual controlled-substance
   conviction, traffic standard-fine tier + surcharge). No signed order → hold,
   post nothing, add to exclusions. Never add account/late/collection/DMV/
   returned-check/traffic-school/restitution-not-ordered/attorney/reporter fees;
   list them as exclusions with reason and 0 included.

6. **Compute payment plans** (when the template has them) with
   `scripts/finance_math.py`: installment count + final catch-up payment, first-due
   (court-ordered, else base date + policy `first_due_days`), final-due (first +
   (total−1) months), return-to-court (final + policy offset), and budget/policy
   support classification. Restitution ordering per policy.

7. **Fill forms & placeholders.** Use portal `form_id`/`label`/placeholder text;
   citation number as the account reference when no case/account number exists.
   Every field required by a form but absent from the materials → the exact
   required placeholder string (e.g. `TBD from case file`); never invent or borrow.

8. **Assemble & format.** Build exactly the template's keys. Totals sum **posted**
   cases only; count held/excluded separately. Emit enum tokens (never prose),
   money to two decimals, ISO dates / `YYYY-MM-DDTHH:MM:SS` datetimes, `null`
   only where allowed. Apply every ordering rule.

9. **Self-check before returning.** Re-open `answer_template.json` and verify:
   all required keys present at every level; every enum value is in-list; arrays
   sorted per the ordering rules; currency has two decimals; nothing invented
   (every posted fee traces to a schedule row or an order); totals equal the sum
   of posted line items; held matters carry no money. Return **JSON only** if the
   template says so.

## Non-negotiables
- Do not invent identifiers, contacts, fees, balances, charges, or conditions.
- The signed court record overrides the portal for *what happened*; the portal
  overrides local worksheets for *identity, structured numbers, and amounts*.
- Post only current-schedule / court-ordered money; everything else is an
  exclusion, not a line item.
- The output must validate against `answer_template.json` — that is the spec, and
  it varies per task, so read it fresh every time.
