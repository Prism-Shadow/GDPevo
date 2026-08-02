---
name: court-closeout-reconciliation
description: >-
  Reconciles court-clerk closeout and post-disposition packet materials (hearing/bench
  notes, finance queue extracts, clerk worksheets, sentencing intake sheets, payment
  petitions, form excerpts) against a read-only Court Operations Portal, then emits one
  JSON object that conforms exactly to a provided answer_template.json. Use when a task
  asks a deputy or circuit-court clerk to close out a criminal, traffic, or financial
  docket: identifying audit conflicts; correcting disposition, counsel, and identity;
  applying current fee-schedule and payment-policy amounts; computing installment-plan
  math; handling placeholders for missing identifiers; excluding unsupported fees;
  gating unsigned/continued matters; and rolling up register/batch totals. Triggers on
  court closeout, sentencing packet, disposition register, fee reconciliation, payment
  plan, CC-1375/CC-1379 forms, citations, financial petitions, or "match answer_template.json".
---

# Court Closeout & Post-Disposition Reconciliation

## What this skill is for

A family of court-clerk tasks. Each gives you: a `prompt.txt` naming a court, a set of
target matters (case / citation / petition IDs), and a deliverable; a set of local
`payloads/` (notes, extracts, worksheets, form excerpts, an `answer_template.json`); and
network access to a **Court Operations Portal** described in `environment_access.md`.

Your job is always the same shape: **treat the local materials as unverified drafts,
verify and correct them against the authoritative portal, drop anything unsupported, do
the financial math, and return one JSON object that matches `answer_template.json`
exactly.** The specific fields, enums, and matters differ every time; the method below
does not.

## Core principle

> Local materials (queue extracts, worksheets, bench shorthand, calendars, draft
> sheets, obsolete footers) are **carry-forward drafts and may be wrong**. Authority
> comes from the signed courtroom result and the portal. Never invent a value, and never
> post a fee, balance, condition, identifier, or contact that a signed order, portal
> record, or current schedule/policy does not directly support.

## Workflow

1. **Read `answer_template.json` first — it is the contract.** Note the exact
   `required_top_level_keys`, per-array ordering rules, every enum and its allowed
   values, required keys per item, and the currency/date/datetime/time formats. Build
   your output to this shape; do not add or drop keys.
2. **Read `prompt.txt` and every file in `payloads/`.** Extract: jurisdiction/court,
   the target matter IDs, the deliverable sections, and any explicit clerk rules ("do
   not add …", "do not invent …", "use the exact placeholder …", "hold until signed").
3. **Resolve portal access from `environment_access.md`** (base URL + allowed
   endpoints). GET only, no credentials. See `references/portal-api.md`.
4. **For each target matter, pull the authoritative record(s)** from the portal (cases,
   charges, docket-entries, citations, financial-petitions) plus the current
   fee-schedule, payment-policy, and form metadata for that jurisdiction.
5. **Resolve every field with the source-of-truth ladder** (below /
   `references/reconciliation-and-fees.md`), recording audit conflicts where the
   template asks for them.
6. **Do the financial math** — fee reconciliation and any installment schedule — using
   current schedule/policy figures (`references/financial-math.md`).
7. **Gate, placeholder, and exclude:** hold unsigned/continued matters, insert the exact
   placeholder for genuinely missing required fields, and route every unsupported item to
   the template's exclusion list with a reason code.
8. **Assemble, sort, format, total, and validate** against the contract
   (`references/output-contract.md`), then return.

## Source-of-truth ladder (which source wins per field)

- **Identity (name spelling, DOB):** portal/CMS record is authoritative; a corroborating
  memo (e.g., a defense cover memo) can confirm it over the queue. Never borrow a DOB or
  name from a *similarly named* party in search results. If a required identifier is
  genuinely absent everywhere, use the exact placeholder — do not guess.
- **Counsel type / fee eligibility:** an on-record clarification (judge statement,
  hearing notes, defense memo) and the portal's `counsel_type` beat calendar/queue
  abbreviations, which are frequently mislabeled. `appointed_private` and `retained`
  counsel are **not** public-defender-user-fee eligible; only a true public defender is.
- **Disposition / plea / sentence / departure:** the **signed courtroom result** (bench
  record, hearing notes, signed order) beats any draft/legacy/worksheet value. Honor the
  judge's explicit on-record statements (e.g., "top of range, no departure finding").
- **Charges convicted:** use the actual **conviction** count (e.g., an amended charge),
  not the originally filed or draft count. A fee tied to a specific conviction (lab /
  drug assessment, etc.) applies only if the defendant was convicted of that offense.
- **Fee amounts:** the fee-schedule row **effective on the disposition date**
  (`effective_date ≤ disposition_date` and `end_date` null or ≥ disposition date). Never
  use an archived/stale prior-year amount.
- **Payment-policy terms:** the portal `payment-policies` row for the jurisdiction
  (min/max monthly band, first-due offset, account fee, restitution priority,
  return-to-court offset).
- **Form metadata & labels:** the current portal form; reproduce visible field labels
  exactly as the local form excerpt shows them.

## Non-negotiable rules

- **Do not invent** identifiers, contacts, fees, balances, conditions, or dates.
- **Do not post unsupported fees.** Account-management/maintenance, collection,
  late-payment, DMV/reinstatement, returned-check, traffic-school, copy/certification,
  court-appointed-attorney, court-reporter fees, restitution not ordered, obsolete
  footer/service charges, statutory-maximum substitutions, and stale prior-year amounts
  are excluded unless a signed order / current schedule / current policy supports them.
  Route each to the template's exclusion list with the matching reason-code enum.
- **Gate on the signed order.** Only enter a disposition and post financials when the
  matter is actually disposed with a signed final order. Draft / continued / deferred /
  unsigned → hold or exclude, no financial register entry, `financial_posting_allowed =
  false`, and supply a next-status-check date if the template asks for one.
- **Placeholders are verbatim.** Use the exact placeholder string the materials specify
  (commonly `TBD from case file`), only for genuinely missing required fields, and list
  them with reason codes.
- **Enums are verbatim.** Never put prose in an enum field. If a value is genuinely
  unverifiable and the enum offers a `verify_before_entry` (or similar) option, use it
  rather than guessing.
- **Conditional sections only when ordered.** Prepare a form/section (e.g., a probation
  referral) only if the underlying order exists; otherwise mark it not-ordered/not-
  required and set the corresponding status boolean accordingly.
- **Totals cover posted matters only.** Held/excluded/pending matters are counted in
  their own count fields, not in the financial totals.

## References (read as needed)

- `references/portal-api.md` — endpoints, query conventions, response shape, and how to
  select the effective fee-schedule / payment-policy / form rows.
- `references/reconciliation-and-fees.md` — the conflict-resolution ladder in depth, the
  unsupported-fee catalog, counsel/fee-eligibility logic, and status gating.
- `references/financial-math.md` — fee reconciliation, installment-schedule math,
  budget/support classification, license-suspension dating, return-to-court settings.
- `references/output-contract.md` — a step-by-step checklist for conforming to
  `answer_template.json` (keys, enums, formats, ordering, totals, JSON-only output).
