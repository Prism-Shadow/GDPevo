---
name: court-closeout-reconciliation
description: >-
  Produce a clerk-ready court-operations closeout packet as a single structured
  JSON object matching a provided answer template, by reconciling local case
  materials (hearing/bench notes, clerk audit or supervisor memos, finance queue
  or worksheet extracts, financial petitions, and local form excerpts) against
  the authoritative court operations portal (system of record). Use for criminal
  sentencing/disposition closeouts, disposition registers, fee reconciliation,
  traffic-citation closeouts, installment/extended payment plans, probation
  referrals, and license-suspension orders. Triggers when a task gives target
  cases/citations/petitions plus mixed local documents and a portal, and asks for
  audit findings, corrected dispositions, fee/register totals, payment schedules,
  form/placeholder handling, or excluded-charge lists in a schema-constrained JSON.
---

# Court closeout reconciliation

You are acting as a deputy/finance clerk closing out a batch of matters. The
inputs are (1) local documents that are messy, partial, and sometimes carry
draft, legacy, or shorthand errors, and (2) an authoritative court operations
portal (the system of record) exposing record collections such as jurisdictions,
cases, charges, docket entries, fee schedules, payment policies, forms,
citations, and financial petitions. Your job is to reconcile the two into one
JSON object that exactly matches the task's `answer_template`.

The work is 20% data gathering and 80% **reconciliation judgment**: deciding, per
field, which source wins, and applying court-clerk rules about what may be posted.

## Procedure

1. **Read the answer template first, before touching data.** Extract and obey:
   - the exact `required_top_level_keys` and the nested item shapes;
   - every `enum` — output only allowed enum values, never prose or synonyms;
   - `ordering_rules` — sort each list exactly as specified (usually by
     case/citation/petition number ascending, then a secondary key; sort
     placeholder/field/charge lists alphabetically);
   - formatting: ISO `YYYY-MM-DD` dates, `YYYY-MM-DDTHH:MM:SS` datetimes,
     currency as numbers to two decimals;
   - the required placeholder string for un-fillable fields (e.g. a literal
     "TBD from case file"), and the rule for when it applies.

2. **Pull the portal record for every target entity and every reference it
   needs.** Look each target up by its exact identifier, and also fetch the
   jurisdiction's current fee schedule, payment policy, and form metadata. Treat
   the portal as the system of record, but not as infallible — its per-charge
   fields can carry the same kind of stale/mislabeled noise the local docs do.

3. **Reconcile field-by-field using the source-priority model below.** For each
   target, list the conflicts across sources, decide the corrected value and
   *which source resolved it*, and record that decision if the schema asks for
   audit findings.

4. **Apply the clerk posting rules** (what fee applies, what gets held, what is
   excluded) — see `references/reconciliation-and-math.md`.

5. **Compute derived values** — fee/register/batch totals, installment schedules,
   and derived dates — using the formulas in the reference file. Compute totals
   only from matters that are actually posted (never from held/pending matters).

6. **Emit exactly the required structure.** Include every required key, sorted
   and formatted, with only supported values. Do not invent identifiers, fees,
   balances, conditions, or contact details that no source supports.

## Source-priority model (which source wins)

Different field *types* have different authorities. Resolve conflicts this way:

- **Disposition substance** — plea, guilt/finding, counts convicted vs
  dismissed/amended-away, sentence terms, whether a departure was pronounced,
  and whether a final order was signed — is governed by the **courtroom
  hearing/bench notes and the signed order** (what the judge actually did). The
  portal's per-charge disposition field may be wrong here (e.g. it reads
  "dismissed"/"nolle" for a matter the bench adjudicated guilty, or shows the
  pre-amendment charge); the courtroom record overrides it.
- **Fee amounts** come from the **current fee schedule** — the row effective on
  the disposition date. Reject any row that has ended (has an `end_date`) or is
  labeled archived/stale, even if a queue/worksheet carried that older number.
- **Payment-plan parameters** (monthly band, down payment, first-due offset,
  return-to-court offset, account-fee treatment, restitution priority) come from
  the jurisdiction's **payment policy**.
- **Identity** (name / DOB) is normally the **portal case record**; a
  corroborating paper memo or defense document establishes a correction when the
  queue/worksheet is wrong. When a memo/defense document is the thing that
  actually resolves an identity or counsel conflict, attribute the resolution to
  that corroborating memo — not to the portal — if the schema distinguishes them.
- **The financial/installment order for the current packet** takes its order-line
  values (e.g. a license-suspension term entered on the financial order) from the
  controlling **financial worksheet/petition for that packet** when it explicitly
  states a value, even if the criminal charge record differs. Absent such an
  explicit packet value, fall back to the charge/statutory value.
- **Draft, legacy, queued, or "morning worksheet" values lose** whenever they
  conflict with any authoritative source above.

When the schema records the resolution source, map it to the source that
*decided* the value: the current schedule for a fee correction; the hearing/bench
record for a disposition or departure correction; the corroborating memo for an
identity/counsel correction it established; a "verify/hold" action when a value
is genuinely missing or the order is unsigned.

## The most common, high-value clerk rules

- **Hold anything not final.** An unsigned / deferred / pending / continued
  matter must be held: do not post its financials, exclude it from the disposed
  register, leave its disposition date null, and (if asked) record a next-status
  check date and that financial posting is not allowed.
- **Counsel drives eligibility.** A public-defender user fee applies *only* when
  counsel is public defender. Appointed-private / county-pay counsel is not
  PD-fee eligible, and an ambiguous calendar abbreviation is not proof of public
  defender — verify the classification.
- **Match assessments to the conviction.** A drug/crime-lab assessment applies
  only to a controlled-substance conviction. If the count was amended to a
  non-drug offense, drop the assessment even if a worksheet carried it; if the
  worksheet omitted it but the conviction is a controlled substance, add it.
- **"Top of range" / presumptive / a plea-agreement cap is not a departure.**
  Enter only a departure the judge actually pronounced on the record.
- **Exclude unsupported money.** Account-management, collection, late-payment,
  DMV/reinstatement, returned-check, traffic-school, copy/certification,
  restitution-not-ordered, statutory-maximum substitutions, and stale-schedule
  amounts stay out of the balance unless a current schedule/policy or the order
  directly supports them.
- **Placeholders are exact and case-specific.** Use the required placeholder
  string only for fields a form needs but no source provides (identifiers,
  addresses, phone, driver-license number; and, when a probation referral is
  being prepared, the probation officer and office location). Do **not**
  placeholder a field that has a standard or derivable value. Only list a
  placeholder for a case that actually needs that field — a case with no
  probation referral carries no probation-office placeholders.

See `references/reconciliation-and-math.md` for the plea taxonomy, the exact
installment/date formulas, and the full determination checklist.

## Output hygiene checklist

- Top-level keys match the template exactly; nothing extra, nothing missing.
- Every enum field holds an allowed value; no free text where an enum exists.
- Dates ISO; datetimes ISO local; every money value a number to two decimals.
- Every list sorted per the ordering rules; alphabetical where specified.
- Totals recomputed from the per-item posted values and internally consistent.
- No invented facts; unresolved-but-required fields use the exact placeholder.
