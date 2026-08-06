---
name: court-operations-closeout
description: Reconcile a court clerk post-hearing/packet closeout from hearing notes, clerk memos, and finance/petition worksheets against a Court Operations Portal, then return one JSON object matching the task's answer_template.json. Use this whenever the working files are a court batch — criminal sentencing docket closeout, traffic violation hearing closeout, post-sentencing financial/supervision packet, or disposition register reconciliation — and the answer must be a single structured JSON object described by an answer_template.json schema.
---

# Court Operations Closeout Skill

This skill turns a batch of court paperwork plus a Court Operations Portal snapshot into one clerk-ready JSON answer that matches the schema in `answer_template.json`. It is domain-general across the closeout flavors (criminal register reconciliation, traffic payment plans, post-sentencing probation/license/payment packets). Read this entry file before doing anything else; the operating rules below are the workflow that worked across the training batches.

When this skill is invoked, expect a working directory laid out as:

- `environment_access.md` — the only source of network access (portal base URL + allowed endpoints).
- A set of train_tasks (or a single matter input) each with `input/prompt.txt`, `input/payloads/answer_template.json`, and one or more supporting payload files (hearing notes, clerk/audit memos, finance queue extracts, worksheets CSV/JSON, local form excerpts, petition/intake facts).

## Operating rules

Work these in order. They are the reusable method, not the values of any single batch.

### 1. Read everything before reasoning
Read `prompt.txt`, `answer_template.json`, and **every** payload file end-to-end before drawing any conclusion. Batches deliberately bury the decisive fact in a later payload or in a single line of a memo (a defense cover memo, a counter note, an obsolete footer, a supervisor note, a review reminder). Never answer from the first file alone. The `answer_template.json` is the contract that defines every key, enum, ordering rule, date format, and currency precision the grader checks — treat it as authoritative, more authoritative than the prompt prose.

### 2. The answer_template is the spec, not a hint
- Build the output object shape from `required_top_level_keys` and each section's required keys.
- Every enum field must take **only** a value from the schema's `enums`/`allowed` list — never substitute prose for an enum, and never invent an enum value.
- Apply every `ordering_rules`/`instructions.matter_order`/`*_sort` rule exactly (sort by `case_number`/`citation_number`/`petition_id`/`charge_code` as specified, ties by the stated secondary key).
- Apply the stated `date_format` (ISO `YYYY-MM-DD`; datetimes as ISO local `YYYY-MM-DDTHH:MM:SS`) and `currency_precision` (numbers to two decimals; use `null` for a date only where the schema explicitly allows it).
- If the schema defines a placeholder enum (e.g. `TBD from case file`), use that exact token and nothing similar.

### 3. Corroborate via the portal — do not trust any single worksheet
The finance queue / bench sheet / worksheet is always partially stale, drafted, or miscopied. For each case, fetch the corroborating portal records using only the endpoints in `environment_access.md` (e.g. `/api/cases`, `/api/charges`, `/api/fee-schedules`, `/api/payment-policies`, `/api/forms`, `/api/financial-petitions`, `/api/jurisdictions`, `/api/citations`, `/api/docket-entries`, `/api/search`). Use the portal to confirm identity (DOB, defendant name spelling), charge/offense code, fee-schedule amounts in effect for the disposition year, payment policy bands, and form metadata. Never read server-side files; the portal is HTTP-only. If a portal endpoint is unreachable, treat the unverified field per the hold/verify rules below rather than guessing.

### 4. Resolve conflicts in favor of the most authoritative, nearest-to-hearing source
When sources disagree, rank the resolution and record it:
- A bench statement / signed sentencing order / hearing closeout note beats a draft worksheet or carry-forward finance queue line.
- A clerk audit memo / corroborating memo / courtroom audio clerk statement beats a stale charge screen or old local worksheet.
- The current fee schedule (for the disposition's year) beats an archived/archived-amount fee line.
- When counsel is genuinely ambiguous (e.g. "PD C. Hill" label vs. a defense memo saying county-appointed private counsel), confirm from the record; **appointed_private** is not **public_defender** — and that distinction changes fee eligibility (a public-defender user fee does not apply to appointed-private or retained counsel).
- When identity (DOB) is genuinely blank or unverifiable, do **not** borrow from a similarly-named defendant in search results; use the schema's placeholder/verify action and flag it.

### 5. Do not post financials for a matter lacking a signed final order
A draft disposition sheet, an unaccepted plea, or a "draft only" worksheet does **not** create a register entry. If the matter was continued, deferred pending an unsigned order, or has no accepted plea/sentence pronounced in open court:
- Set the entry/register action to the hold/exclude/continued enum.
- Set fee status to `hold` / `do_not_post_pending` (per the schema's vocabulary).
- Exclude the case from the disposed/assessed register totals and count it instead in the held/excluded/pending count.
- Record it in the exclusions section with the stated reason and the next status-check date.

### 6. Exclude unsupported and stale financial items explicitly, never silently
Only post fees/dollars that are directly supported by the hearing order, the current fee schedule, or current payment policy. Explicitly exclude (in the schema's `excluded_charges` / `excluded_financial_items` / `exclusions` section, with the right reason code):
- Account-management / collection / late-payment / returned-check / DMV / restitution / copy / certification / traffic-school / court-reporter / court-appointed-attorney fees that have **no triggering event** in the hearing order and **no current policy support**.
- Stale/archived/obsolete fee amounts (e.g. a prior-year drug assessment, an old $1,000 fine table, a repealed $25 plan service charge) — replace with the current schedule amount, and note the stale item as excluded.
- A statutory-maximum note is not a billing instruction by itself unless the schedule/policy actually applies it.
- If a counter worksheet still carries an old account-maintenance fee row, exclude it pending the current-policy check.

### 7. Do not invent missing identifiers or contact details
For any field a form requires that is not in the case file (SSN, address, phone, driver license number, probation officer/office, account number), use the schema's exact placeholder (e.g. `TBD from case file`) and record it in the `placeholder_fields` / `placeholder_cases` section with the appropriate `reason_code`/`missing_fields`. For a traffic matter with no separate case/account number, the citation number is the account reference. List every such field; do not silently leave it blank and do not fabricate.

### 8. Compute totals and schedules from posted values only
- Money totals (case totals, register/batch totals, `combined_amount_due`, `grand_total`) are sums of the **posted** (held/verified) items only — never include excluded or hold-amounts in assessed totals, and never include held cases in the disposed count.
- Payment-plan math: `amount_due` minus `down_payment`, divided by `monthly_payment`, gives the number of full installments; the uneven remainder is the `final_payment_amount`; `total_installments` and `final_due_date` follow from the first due date and interval. Apply the policy band (minimum/maximum monthly) to classify the requested amount as supported / below-minimum / above-maximum / unsupported-by-budget.
- License suspension end date = start date + suspension months, where the **start basis** (conviction date vs. release date vs. petition date) is chosen per the hearing note and current form/policy.
- Every total is a currency number to two decimals.

### 9. Record audit findings as first-class output
Where the schema has an audit section (`audit_findings`, `case_audit`) or asks for conflict resolution, emit one entry per conflict with the conflicted value, the corrected value, the issue type, and the resolution source (which authority was trusted). Do not drop a conflict just because it resolved cleanly — the corrected value and its source are part of the deliverable.

### 10. Final checks before returning
- Object matches `required_top_level_keys`; no extra top-level keys; no markdown; pure JSON when the schema says so.
- All enum fields use only allowed values; all sort orders applied; dates ISO; money to two decimals; `null` used only where the schema permits.
- Every held/continued/deferred matter is out of posted totals and in the held/excluded count; every excluded fee is listed with a reason.
- Every placeholder field is listed; no identifier or contact detail was invented.
- Re-read the prompt's "Return…" sentence and confirm every requested artifact (audit conflicts, dispositions, fee reconciliation, docket summaries, register totals, payment plans, form/account handling, exclusions, placeholders) is present.

## Supporting references

These two files live alongside this entry file and give the reusable detail:

- `references/data-sources.md` — what each kind of payload file means, the trust ranking between bench/hearing notes, audit/corroboration memos, finance queue/worksheets, and form excerpts, and how to map a given payload type onto the schema.
- `references/schema-playbook.md` — a checklist for turning `answer_template.json` into the output object, the conflict-resolution hierarchy, the hold/exclude/placeholder rules, and the totals/schedule math, with the enum vocabularies summarized generically (no task-specific final values).

Use them when a step above needs more detail; do not skip step 1 to jump to them.
