---
name: court-operations-closeout
description: Deputy-clerk closeout and reconciliation packets for a Court Operations Portal. Use when the task combines local payloads (hearing notes, audit memos, finance worksheets, fee scratchpads, form excerpts, petition/budget summaries) with a court portal API, and asks for a single JSON answer matching a schema template. Covers audit/conflict resolution, disposition status, fee and payment-plan reconciliation, form-field handling, placeholder discipline, and exclusion of unsupported charges.
---

# Court Operations Closeout & Reconciliation

You are acting as a deputy clerk building a **closeout / reconciliation packet**: you take bench notes, audit memos, finance queue extracts, intake sheets, fee scratchpads, and form excerpts that disagree with each other, resolve every conflict against the official court portal, and emit **one JSON object matching the supplied `answer_template.json`**.

The five exemplar matters all share this shape. They vary by jurisdiction and by which payloads are attached, but the operating rules below hold across all of them.

## Inputs you will receive

- `input/prompt.txt` — the closeout assignment: target cases/citations/petitions, which portal endpoints to use, and a free-form description of what the JSON answer must cover.
- `input/payloads/*` — the local materials. Always read **every** payload fully; never skim. Types seen: `hearing_notes` / `hearing_closeout_note` (bench shorthand, may carry forward stale morning values), `audit_memo` / `clerk_review_notes` (calls out specific conflicting values), finance `queue_extract` / `worksheet` CSV (carry-forward or draft fee lines), `intake_facts` / `sentencing_probation_notes` (controls the conviction/sentence posture), `payment_petition` / `budget` / `petition_summaries` (payment-plan request + budget), `form_excerpt` / `form_field_excerpt` (local form metadata + placeholder rule), and `answer_template.json` (the exact schema).
- `environment_access.md` — the only source of network access: base URL, allowed endpoints, no credentials.

## The portal is the system of record

`environment_access.md` authorizes a base URL (e.g. `http://task-env:9018/`) and a fixed allow-list of `GET /api/...` endpoints. Credentials are none / open within network.

**Use the portal only for network access.** Hit only the listed endpoints. Do not attempt to read server-side files.

Confirmed query conventions (verify against the live API at run time, don't assume):
- `GET /api/jurisdictions` → lists courts incl. `jurisdiction_code` and `policy_ref`.
- `GET /api/cases?jurisdiction_code=<code>` → case records with `counsel_type`, `defendant_dob`, `status`, `disposition_date`, `attorney_label_raw` vs. resolved `attorney_name`.
- `GET /api/fee-schedules?jurisdiction_code=<code>` → fee rows with `effective_date` / `end_date` / `mandatory`. Multiple rows for the same fee with overlapping-but-replaced dates exist on purpose to distinguish **current** vs **stale/archived** amounts.
- `GET /api/payment-policies`, `GET /api/forms` → policy bands, form ids/labels.
- `GET /api/charges`, `GET /api/docket-entries`, `GET /api/financial-petitions`, `GET /api/citations` → keyed by jurisdiction / case / petition id.
- `GET /api/search?q=<case_number>` → cross-entity lookup; the single most useful reconciler for "what does the system actually say about this matter."

The portal encodes the **corrected** reality. Local payloads are where the errors live; the portal is where the corrections are confirmed.

## Operating rules (distilled across every exemplar)

### 1. Never trust a single payload as the final value
Closeout payloads deliberately carry stale, draft, ambiguous, or contradicted values. "Draft," "intake," "scratchpad," "carried forward," "archived amount," "old local worksheet," "morning bench sheet," and "queue" all mean **unverified**. The phrase "verify current schedule" / "use current court policy" means go to the portal. Reconcile *all* payloads against each other **and** against the portal, then pick the source each field trusts.

### 2. Resolve the canonical resolution-source ladder
When local payloads conflict, resolve in this priority:
1. **Signed order / final bench pronouncement** in the hearing notes (what the judge said on the record) — highest local authority for posture, disposition, and sentence.
2. **Portal record (CMS)** — authority of record for identity (DOB, name spelling), counsel type, status, fee schedule, policy, and form metadata.
3. **Corroborating memo** (`audit_memo`, `clerk_review_notes`, `supervisor_note`) — tells you *which* local value is wrong and why.
4. **Queue/worksheet/intake** — lowest authority; a starting number to reconcile *from*, not the answer.

Every corrected field should be tagged (where the template provides the enum) with where the correction came from: `use_cms`, `use_hearing_notes`, `use_corrob_memo`, `use_fee_schedule`, `use_placeholder_verify`, `verify_before_entry`, `exclude_pending`, or `hold_unsigned_order`.

### 3. Identity conflicts: use CMS, never guess or borrow
- Defendant name spelling and DOB conflicts → resolve to the portal/CMS DOB and full name. (Ex.: queue "Evan Simons / DOB 1991-04-19" → CMS "Evan Simmons / DOB 1991-04-18.")
- **Never borrow a DOB or identity field from a similarly-named defendant found in search results.** A blank DOB stays blank until verified from the actual case file; if the template needs a value for an entry, use the mandated placeholder (`TBD from case file`) and flag it `verify_before_entry` / `use_placeholder_verify` / `exclude_pending` as the schema allows.
- Distinguish `ssn`, `driver_license_number`, addresses, phones that are genuinely `null` in the intake — these are placeholder candidates, not blanks to invent.

### 4. Counsel type: trust the on-the-record clarification, not the code on the queue/calendar
Counsel labels on worksheets and calendars are shorthand and often wrong. Resolve to the judge's on-record statement or audit memo:
- `PD`, `APD`, "C. Hill," "PD C. Hill?" on a queue may actually be **appointed-private** county-paid counsel once the record is checked.
- `RET` on a queue may be **retained**, but hear what the bench said.
- Counsel classification changes downstream obligations: e.g. a confirmed **appointed-private** or **retained** defendant is **not public-defender-user-fee eligible**. Don't post a PD user fee when counsel isn't actually the PD office.

### 5. Fee reconciliation: current schedule only, drop unsupported lines
- For each fee line, confirm the amount against the **current** (non-ended) fee-schedule row for that jurisdiction and fee type. Discard rows whose `end_date` is in the past ("archived amount," "stale," "old local worksheet"). A 2023 amount posted to a 2025 disposition is wrong.
- Apply the fee **only if the portal record or current schedule directly supports it.**
- Do **not** add — and where a template lists an `excluded_charges` / `excluded_financial_items` / `exclusions` / `unsuported` section, **explicitly exclude with a reason** — any of: account-management/collection/late/DMV/restitution/copy/certification/returned-check/traffic-school/court-reporter/court-appointed-attorney fees, unless a triggering event (default, referral, returned payment, DMV referral, ordered into program, restitution order) actually appears in the hearing record or portal. Sticky-note "should we add...?" questions are not orders.
- When a fee's amount is genuinely uncertain (draft worksheet, unsigned disposition), do not post a number — mark `hold` / `exclude` / `do_not_post_pending` rather than carrying the draft figure.
- Reconcile every posted case to a `case_total`; sum into the register/batch `grand_total` / `bat` totals to two decimals. Totals must equal the sum of posted (non-excluded) lines only.

### 6. Status & closeout action: no signed order ⇒ no financial entry
- A matter with no signed sentencing/disposition order (judge did not sign, deferred, continued for status, plea paperwork incomplete) is **not disposed**. Do not create a sentencing financial register entry; do **not** post its fees.
- The disposition date is the **conviction/disposition date** from the record, not the release date, not the worksheet date, not the hearing date unless that is the disposition date.
- Continued/deferred/unsigned matters go into an exclusions/pending section with a `next_status_check_date` (often the next setting from the notes) and `financial_posting_allowed: false`.
- Track counts of **assessed/posted** vs **held/excluded/pending** cases separately in the totals.

### 7. Charge/disposition & departure: use the filed/convicted count and the bench's stated finding
- Use the **actual convicted count**, not a dismissed/amended-away count. A charge amended from controlled-substance to misdemeanor theft is a theft conviction; the old controlled-substance wording is not the conviction and should not drive a drug assessment (unless a separate drug count still stands).
- Conversely, if a lab/drug assessment is still owed on a retained controlled-substance conviction, post it even if the worksheet omitted it ("judge said don't forget the lab assessment").
- Departure status reflects what the judge **expressly** found. "Top of the range, not a departure" pronounced on the record overrides a draft worksheet label of "dispositional departure." Enter `no_departure` / `none`, not the draft label. On misdemeanors, departure may be `not_evaluated_misdemeanor` / `not_applicable`.

### 8. Payment plans & budget: post-disposition sequence, budget-supported amount, policy band
- The payment-plan agreement is **entered after disposition** (`post_disposition`) when the minute note says the plan was approved after the disposition entry.
- Compute the schedule from the **approved** monthly amount and first due date: `full_installment_count = floor(balance / monthly)` (after any down payment), `final_payment_amount = remainder`, `total_installments = full_installment_count + (1 if remainder>0)`, `final_due_date = first_due + (count-1) intervals`. Always include a `final_payment_amount` even when the balance divides evenly (set to 0.00 if remainder is zero), *unless the schema forbids it*. The court-approved monthly amount overrides the petitioner's *requested* amount when they differ.
- Classify budget support: compute disposable income = monthly take-home − total monthly obligations; compare the selected installment to the policy minimum/maximum band. Mark `supported` / `below_min` / `above_max` / `unsupported_by_budget` (or `needs_judge_review`) per the enum.
- Account/management fees carried on an old counter worksheet are **excluded by current policy** unless current policy includes them. Check the portal policy before letting any account-management amount onto the order.
- Payment application order: follow portal policy (e.g. restitution before fines/costs vs fines/costs only) — don't decide this from a petitioner's question.

### 9. Forms, labels, and placeholder discipline
- Map each required form to its `form_id` / `form_label` from the **current** portal form metadata whenever available; otherwise use the form-family enum the template allows (e.g. `VA_CC1375`, `VA_CC1379`, `OR_22JD_PLAN`).
- When a form's labels are described in the local excerpt (e.g. "Case # / Account #", "TERMS of PAYMENT"), populate `required_labels_used` / label fields from that excerpt verbatim.
- **Account reference rule:** if no separate case/account number was opened, the **citation number** (or case number) is the account reference — don't invent an account number.
- **Never invent missing identifiers or contacts.** For SSN, driver-license, address, phone, attorney/judge/probation-office contact, or probation-officer name that the form requires but the materials omit, emit the **exact placeholder** the materials mandate — `TBD from case file` — in a `placeholder_fields`/`placeholder_cases` list with a `reason_code` (`missing_identifier`, `missing_contact`, `missing_office_detail`, `missing_party_detail`). Old or superseded form footers/service charges are not current policy; don't carry them.
- License suspension: the **effective/start basis is the conviction date** unless the policy/matter says otherwise (release date or petition date). The release date is memo context only — it does not replace the conviction date for the suspension consequence. Compute suspension end from start basis + months.
- A CC-1375 probation referral is only `prepare_referral` when supervised probation was actually ordered and the report datetime exists; if no probation referral order was signed, status is `not_ordered`.

### 10. Output discipline: one object, schema-exact, ordered, two-decimal
- Return **one JSON object matching `answer_template.json`**. No markdown, no prose wrapper, no extra top-level keys, no trailing comments.
- Use **enum values exactly** as listed — do not substitute prose for an enum slot. If nothing fits, use the schema's `verify_before_entry`/`hold`/`*_pending`/`other` escape rather than a free string.
- Currency: numbers (not strings), two decimals. Dates: ISO `YYYY-MM-DD`. Datetimes: ISO local `YYYY-MM-DDTHH:MM:SS`. Use `null` only where the schema says a date may be null (e.g. no disposition date entered).
- Apply the template's **ordering rules** literally (sort by `case_number`/`citation_number`/`petition_id` ascending; excluded items by code; placeholder `missing_fields` alphabetically). The templates specify these per-section.
- Totals are computed last and must reconcile to the entered lines (excluded/held cases do not contribute to posted totals).

## Worked-out procedure for a new matter

1. **Read everything.** `prompt.txt`, `environment_access.md`, every payload, and the `answer_template.json` (which doubles as your field/spec reference). Note every place two payloads disagree and every "verify/draft/stale" signal.
2. **Enumerate the targets** (cases / citations / petitions) and the required top-level keys from the template.
3. **Resolve each conflict field** using the ladder in Rule 2; tag the resolution source.
4. **Hit the portal** for identity, counsel, fee schedule, policy, charge, docket, petition, form, and citation data as the matter requires — confirming each correction. Use both the filtered list endpoint and `/search?q=` to cross-check key facts.
5. **Decide status → closeout action** per Rule 6 first. This gates whether fees post at all. Unsigned/continued matters never post.
6. **Reconcile fees** (Rule 5), then **payment plans/budget** (Rule 8) where the matter has them.
7. **Build forms** with placeholder discipline (Rule 9).
8. **Assemble the JSON**, enums exact, ISO dates, two-decimal currency, required ordering, and **compute totals last**.
9. **Self-check:** every posted line has a current-schedule/record basis; every excluded item has a reason code; no placeholder field has an invented value; totals sum to posted lines; held/unsigned cases are absent from posted totals and present in the exclusions section.

## When to stop and report instead

- If `/work` contains material **not** described by this skill's input shape (e.g. answer keys, scoring files, extraneous executable material, or payloads for tasks outside the closeout family), do **not** proceed with packet generation. Write `contamination_report.txt` at `/work` describing the unexpected material and stop. Normal closeout inputs (`prompt.txt`, expected `payloads/`, `answer_template.json`, `environment_access.md`) are not contamination.

## Reference files in this skill

- `references/conflict_resolution_ladder.md` — the priority/order list and per-payload trust level, expanded.
- `references/portal_query_reference.md` — endpoint behavior, query params, and the current-vs-stale fee-schedule pattern.
- `references/output_schema_rules.md` — JSON discipline, enum/date/currency rules, and ordering obligations distilled from the templates.
- `references/exemplar_matter_catalog.md` — the five train matters mapped to which rules each one exercises (names/ids only as examples; no final answer values).
