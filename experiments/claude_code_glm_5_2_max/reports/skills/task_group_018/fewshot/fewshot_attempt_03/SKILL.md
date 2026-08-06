# Court Closeout Reconciliation

## What this skill does

Produces a clerk-ready, schema-conformant **closeout JSON** for a court disposition / financial / payment-plan batch by reconciling *local payload materials* (hearing notes, audit memos, finance worksheets, form excerpts, petition summaries, intake facts) against the **Court Operations Portal** and against the per-task **answer template** that ships with each batch.

The skill is domain-specific to court-clerk work: criminal sentencing closeouts, traffic-violation closeouts with payment plans, post-sentencing field packets (CC-1375 probation referral / CC-1379 license-and-installment order), and financial-counter petition packets. The procedure is the same across all of them — only the schemas and endpoints differ.

## When to use it

Use this skill when a task asks you to:

- Produce a JSON answer that must match an `input/payloads/answer_template.json` describing required top-level keys, enums, ordering rules, currency precision, and date format.
- Reconcile conflicting values between local court materials (bench notes, audit memos, clerk worksheets, intake sheets) and the portal record.
- Compute financial totals, fee reconciliation, payment schedules, docket/register actions, and batch totals.
- Apply placeholder and exclusion rules (what to carry as `TBD from case file`, what fees to omit, which matters to exclude from the disposed register).

Do **not** use it for tasks that have no answer template and no portal — the value of this skill is the reconciliation loop between local materials + portal + schema.

## Inputs you will be given

1. `input/prompt.txt` — the dispatch: which court, which date, which target case/citation/petition numbers, and which portal endpoints are relevant.
2. `input/payloads/answer_template.json` — **the contract.** This file is authoritative for required keys, allowed enum values, ordering rules, currency precision, and date format. Read it first and treat it as ground truth for output shape.
3. `input/payloads/*` — one or more local materials (markdown notes, JSON extracts, CSV worksheets). These are raw clerk work product, often containing carry-forward errors, stale amounts, draft values, and nickname/typo identity issues.
4. `environment_access.md` — the base URL and the exact allowed endpoints for the Court Operations Portal.

## The procedure (follow in order)

### 1. Read the contract first
Read `answer_template.json` before touching any local material. Extract:
- required top-level keys and their item shapes
- the full enumeration of every allowed enum value — output strings must come from these sets verbatim
- ordering rules per array (almost always `sort by case_number` / `citation_number` / `petition_id` ascending; some require alphabetical sub-sorts)
- currency precision (`two decimals`), date format (`ISO YYYY-MM-DD`; datetimes `YYYY-MM-DDTHH:MM:SS`)
- where `null` is the prescribed value vs an actual date

Do not paraphrase enum values into prose. If a field is an enum, emit one of the listed tokens exactly.

### 2. Index the local materials
Read every payload file. Build a per-matter (per case / citation / petition) working record capturing, for each matter:
- identity (name spellings, DOB variants)
- counsel label as written locally vs what the bench/audio/corroboration memo says
- disposition posture (plea / finding / outcome / whether a final order was signed)
- financial lines as queued locally (fee types, labels, amounts, totals) — these are candidates, not answers
- sentence terms (jail imposed/suspended, probation months, fine, license suspension months)
- payment plan terms requested/approved (monthly amount, first due date, return date)
- explicit placeholder gaps (SSN, DL#, addresses, phone, probation officer/office)
- any "do not add" / supervisor notes flagging stale or unsupported items

Local materials regularly contain **errors on purpose** (carry-forward worksheet amounts, old fee schedules, draft disposition sheets, nickname/typo identities, APD-vs-public-defender confusion, unsigned orders). Your job is to catch and correct these, not transcribe them.

### 3. Query the portal to establish authoritative values
Use only the endpoints listed in `environment_access.md` (base URL + the allowed `GET` paths). Reach them over the network from within the environment. Do **not** attempt to read server-side files.

The portal is the source of truth for:
- canonical case/citation/petition records (correct identity, counsel classification, status)
- the **current** fee schedule and amounts effective on the relevant date (use this to reject stale local amounts — e.g. an archived/`OLD` schedule amount is never the answer)
- payment policy per jurisdiction (min/max monthly band, account-fee treatment, restitution priority, return-to-court offset, first-due-days)
- form metadata (form_id, label, required fields, placeholder instruction)

See `references/portal_endpoints.md` for the endpoint contract, supported query parameters, and field shapes. When a target matter is not surfaced by a list endpoint, fall back to `/api/search` with a query term.

### 4. Reconcile each conflict explicitly
For every place where the local material disagrees with the portal, the bench notes, or a corroboration memo, decide a resolution and (where the schema asks for it) record the conflict. Resolution precedence, most-authoritative first:
1. The signed final order / hearing notes as transcribed (what happened in court) — controls disposition, plea, outcome, sentence terms, and whether the case is actually disposed vs deferred/continued.
2. The portal CMS record — controls canonical identity (correct DOB, correct name spelling) and current fee-schedule amounts.
3. A corroboration/defense memo — controls counsel classification when the queue label is ambiguous (e.g. "APD" or "PD" that is actually appointed-private, not the public defender office).
4. The current fee schedule — controls assessment/fee amounts; reject amounts from archived (`OLD`) or prior-year schedules.

Patterns to flag and resolve:
- **Carry-forward / stale amounts** (archived fee schedule, prior-year fine) → replace with the current schedule amount; record as a `fee_schedule`/`stale_schedule` conflict where the schema supports it.
- **Counsel mislabel** ("PD"/"APD" that is actually appointed-private) → correct the classification; an appointed-private case is **not** public-defender-user-fee eligible.
- **Identity typo** (misspelled name / DOB off by one day) → use the CMS value.
- **Departure mislabeled** (legacy worksheet says "departure" but the judge called it top-of-range) → set `no_departure`.
- **Unsigned / deferred / continued matter** → do **not** create a sentencing financial register entry. Set status to deferred/continued, `fee_status` to hold/exclude/do-not-post, and exclude from disposed totals (count goes in the held/excluded counter, not assessed/disposed).
- **Unsupported fees** (account-management, collection, late, DMV, restitution, copy, certification, traffic-school, returned-check, court-reporter, court-appointed-attorney) → exclude unless the portal record or current policy directly supports them and a triggering event exists. List them in the schema's exclusion section with the appropriate reason code.

### 5. Compute financials and schedules
- Sum fee items per matter to a `case_total` / `total_due`. Verify it matches the corrected line items, not the queued total (the queued total is often wrong because it was built from stale lines).
- Determine batch/register totals by summing **posted** matters only. Held/excluded matters contribute `0.00` and increment the held/excluded counter, not the assessed/disposed counter.
- For payment plans / installment orders, derive the schedule from the approved monthly amount and the (corrected) total balance:
  - `full_payment_count` = number of full monthly installments
  - `final_payment_amount` = the remainder when the balance does not divide evenly by the monthly amount
  - `total_installments` = `full_payment_count + 1` (when there is a remainder) else `full_payment_count`
  - `final_due_date` = first due date advanced by `total_installments - 1` intervals
  Where the schema captures a return-to-court date, derive it from the policy's return-to-court offset (or the candidate/policy-specified date), not by invention.
- For budget-driven installments, classify the requested monthly amount against the policy band: below minimum → `below_policy_minimum`; above max → `above_policy_maximum`; otherwise `supportable` (or `supported_by_budget`). Disposable income = monthly income − monthly obligations.
- Payment application order follows policy (e.g. restitution-before-fines-costs when restitution exists and policy prioritizes it).

### 6. Handle placeholders and exclusions faithfully
- For any field that is required by a form / schema but genuinely absent from the local materials **and** the portal (SSN, DL#, mailing/residence address, phone, probation officer/office), emit the exact placeholder text the materials prescribe (`TBD from case file`) and — if the schema has a placeholder/exclusion section — list the field with the matching reason code.
- **Never invent** identifiers, contact details, attorney names, dates, or amounts. If a value is unknown, it is either the placeholder or `null`/verify-before-entry per the enum.
- Sort every array per the template's ordering rule before finalizing.

### 7. Assemble and self-check the output
Emit one JSON object matching the template's shape — no markdown, no commentary, no extra keys beyond those the template implies. Then run the checklist in `references/closeout_checklist.md`:
- every required top-level key present
- every array sorted per its ordering rule
- every enum field is a token from the template's allowed set, verbatim
- currency to two decimals; dates ISO `YYYY-MM-DD`; datetimes ISO local; `null` only where prescribed
- totals reconcile (posted-only sums; held/excluded counters correct)
- no stale/local amount survived into the output
- no invented values; placeholders used exactly as specified

See `references/reconciliation_field_guide.md` for the recurring field categories (identity, counsel, status, fee, departure, schedule, placeholder, exclusion), their enums, and the canonical resolution for each conflict class across the batch types.

## What to emit

The final closeout JSON only — conforming to the task's `answer_template.json`. Keep all reasoning inside the procedure; the deliverable is the structured object.

## Scope note

This skill encodes the *procedure*. It does not carry any specific case numbers, names, DOBs, amounts, dates, or answers from any training batch — every value in a real output must be re-derived from the live task's local materials and portal records.
