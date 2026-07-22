# Court Clerk Operations — Multi-Source Reconciliation

## Purpose

Process court closeout packets, disposition registers, and post-sentencing field packets by cross-referencing local case materials against a Court Operations Portal API. Produce structured JSON outputs that reconcile conflicts across data sources, apply current fee schedules, and flag items that must be held, excluded, or verified before entry.

## Entry Conditions

Invoke this skill when the task involves:
- Closing out a criminal docket, traffic docket, or disposition batch
- Preparing a post-sentencing field packet or financial/supervision packet
- Reconciling a finance queue or clerk worksheet against court records
- Any task that directs you to cross-reference local payloads with a "Court Operations Portal" API

## Core Workflow

### Phase 1 — Ingest All Sources

For every target case or matter, collect from three independent channels:

1. **Local payloads** — hearing notes, audit/corrob memos, finance queue extracts, worksheets, petition summaries, form-field excerpts, sentencing intake sheets. Never trust a single local document alone; each may contain carry-forward values, draft figures, or stale labels.

2. **Portal API** — query `/api/search?q=<case_number>` to retrieve the case record, charge record(s), docket entries, and any linked petitions in one call. Then drill into specific endpoints (`/api/charges`, `/api/docket-entries`, `/api/citations`, `/api/financial-petitions`) as needed.

3. **Reference data** — query `/api/fee-schedules`, `/api/payment-policies`, `/api/forms`, and `/api/jurisdictions` for the current jurisdiction. These ground every financial figure and form-field decision.

### Phase 2 — Reconcile Conflicts

When sources disagree, apply this hierarchy (highest authority first):

| Priority | Source | Overrides |
|----------|--------|-----------|
| 1 | Hearing/courtroom notes | Pleas, verdicts, sentences, departures, counsel appearances on the record |
| 2 | Audit/corrob memos | Identity corrections, counsel classifications, fee exclusions flagged by clerk supervisor |
| 3 | CMS portal identity fields | Defendant name spelling, DOB, attorney name (when not contradicted by notes) |
| 4 | Finance queue / worksheet | Lowest authority — often carries stale amounts, draft labels, or carry-forward values |

**Identity conflicts** — When name or DOB differs between sources (e.g., "Evan Simons" vs "Evan Simmons", DOB off by one day), prefer the CMS portal record unless an audit memo provides a verified correction.

**Counsel conflicts** — Calendar abbreviations (APD, PD) are unreliable. "APD" can mean "appointed private" paid by the county — not the public defender office. Check the hearing notes for who actually appeared and the portal for the counsel_type field. An appointed-private counsel does NOT trigger a public-defender user fee.

**Charge conflicts** — Portal charge records may be stale (showing pre-amendment offenses, pre-appeal dispositions, or draft departure labels). The hearing notes and sentencing intake control what the court actually ordered. If the hearing says "amended to misdemeanor theft" but the portal still shows a felony drug charge, the hearing controls.

**Status conflicts** — A finance-queue "disposed" status for a case the judge continued or deferred is a data-entry artifact. When the portal shows "deferred"/"pending" and the hearing notes confirm no final order was signed, the case is NOT disposed. Do not post financial entries for held cases.

**Departure conflicts** — Legacy/draft departure labels in the CMS charge record (e.g., "dispositional departure / mitigating treatment record") may contradict the judge's stated findings. If the judge said "top of the range, no departure," or the hearing notes are silent on departure, override the stale label with `no_departure`.

### Phase 3 — Apply Fee Schedules

Every financial entry must be grounded in a current fee schedule:

- Query `/api/fee-schedules` and filter by `jurisdiction_code`.
- Check `effective_date` and `end_date` — a schedule with `end_date` in the past is **stale** and must not be used. The portal may retain stale entries for audit history (e.g., 2023 drug assessment of $125 when the 2025 schedule shows $250).
- `mandatory: true` fees always post when the triggering condition is met (e.g., court costs on every disposed criminal case, drug assessment on controlled-substance convictions, crime lab fee on controlled-substance counts).
- `mandatory: false` fees (e.g., public-defender user fee) only post when the condition is met AND the case record confirms it (counsel is actually a public defender, not appointed private).
- Do NOT add account-management, collection, late-payment, DMV, returned-check, restitution, copy, certification, or traffic-school fees unless the portal record or current fee schedule directly supports them for the specific matter.

### Phase 4 — Build the Answer

Construct the JSON output to match the provided answer template exactly:

- **Sort order** — Follow the template's ordering rules (typically by case_number, citation_number, or petition_id ascending).
- **Enums** — Use the exact enum values from the template. Never substitute prose for an enum value.
- **Currency** — Numbers to two decimal places. Use `0.00`, not `0`.
- **Dates** — ISO 8601 YYYY-MM-DD. Use `null` only where the template explicitly permits it (e.g., for pending cases with no disposition date).
- **Missing identifiers** — When a required field (SSN, driver's license number, address, phone, probation officer name, probation office location) is absent from ALL sources, use the placeholder `"TBD from case file"`. Never invent or borrow values from similar cases.

### Phase 5 — Verify Completeness

Before finalizing, check:
- Every target case appears in the output with the correct status.
- Held/pending cases have `hold`/`exclude` fee status, $0.00 totals, and no disposition financials posted.
- Amended charges are reflected (the convicted offense, not the original filed charge).
- Register/batch totals sum correctly across all posted cases (exclude held cases from totals).
- No unsupported fees have leaked into any case total.
- Items identified as "do not add" or "exclude" by local intake documents are honored.

## Common Patterns

### Payment Plan Construction

When a petition or hearing order approves an installment plan:
1. Compute `amount_due = fines_costs_balance + restitution_balance + account_fee` (account_fee from policy, not from counter worksheets that may carry stale values).
2. `full_installment_count = floor(amount_due / monthly_payment)`.
3. `final_payment_amount = amount_due - (full_installment_count * monthly_payment)`.
4. `total_installments = full_installment_count + (1 if final_payment_amount > 0 else 0)`.
5. `first_due_date = submitted_date + policy.first_due_days`.
6. `final_due_date = first_due_date + (total_installments - 1) months`.
7. `return_to_court_date = final_due_date + policy.return_to_court_offset_days`.
8. Validate `monthly_payment` is within `[policy.min_monthly, policy.max_monthly]`.
9. Validate `monthly_payment ≤ disposable_income` (from petition budget).
10. Apply restitution priority per policy (restitution_before_fines_costs or fines_costs_only).

### Amended Charges

When a charge was amended at hearing (e.g., felony drug possession → misdemeanor theft):
- The convicted count is the amended offense, not the original filed charge.
- Any fee tied to the original charge (e.g., drug assessment, crime lab fee) does NOT apply to the amended conviction unless the new charge also triggers it.
- The original charge counts as "dismissed or amended away" in the count summary.
- Flag the amendment in audit findings.

### Excluded / Held Cases

A case stays out of the disposed register when:
- No final order was signed (judge continued the matter for status).
- The portal status is `deferred` or `pending` and hearing notes confirm no sentence was pronounced.
- Do not post financial entries. Set fee_status to `hold`/`do_not_post_pending`. Set totals to 0.00.
- Record the next status check date from the hearing notes.

### Unsupported Charges to Exclude

Common categories of charges that should be excluded from the starting balance:
- Stale fee-schedule amounts (old SOF tables superseded by current schedules).
- Fees for events that never occurred (late fees when not late, collection fees when not referred, DMV fees when no DMV action ordered, returned-check fees when no returned payment, traffic-school fees when not ordered).
- Statutory-maximum notes that are not actual fee-schedule entries.
- Account-management fees when the current policy sets `account_fee: 0.00`.

### Budget Analysis for Payment Petitions

When a petition includes a budget:
- `monthly_disposable_income = monthly_take_home_income - total_monthly_obligations`.
- If `requested_monthly_payment ≥ policy.min_monthly` AND `requested_monthly_payment ≤ policy.max_monthly` AND `requested_monthly_payment ≤ monthly_disposable_income` → `supportable`.
- If below policy minimum → `below_policy_minimum`.
- If above policy maximum → `above_policy_maximum`.
- If disposable income cannot support it → `unsupported_by_budget`.

### License Suspension Start Dates

The suspension start date depends on the basis:
- `conviction_date` — suspension runs from the conviction date (most common).
- `release_date` — when the sentence includes active confinement and the suspension starts upon release.
- `petition_date` — when triggered by the petition filing.

## API Reference

All endpoints are at `<TASK_ENV_BASE_URL>` (use the base URL provided in the task prompt, ignoring any localhost/127.0.0.1 references in staged materials).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/jurisdictions` | Court info, jurisdiction codes, policy refs |
| GET | `/api/cases?case_number=X` | Case records (identity, counsel, status) |
| GET | `/api/charges?case_number=X` | Charge details (offense, plea, sentence, departure) |
| GET | `/api/docket-entries?case_number=X` | Docket history and entry text |
| GET | `/api/citations?citation_number=X` | Traffic citation data |
| GET | `/api/fee-schedules` | All fee schedules with effective/end dates |
| GET | `/api/payment-policies?jurisdiction_code=X` | Payment plan parameters by jurisdiction |
| GET | `/api/forms?jurisdiction_code=X` | Form metadata, required fields, placeholder rules |
| GET | `/api/financial-petitions?petition_id=X` | Petition data (balances, budget, requested terms) |
| GET | `/api/search?q=X` | Multi-entity search (cases, charges, dockets, petitions) |

**Key API patterns:**
- Use `/api/search?q=<case_number>` as the first query for any case — it returns cases, charges, docket entries, and petitions in one response.
- Always check `jurisdiction_code` when querying fee schedules and policies; a schedule for the wrong county is irrelevant.
- `effective_date` and `end_date` on fee schedules determine currency; a `null` end_date means the schedule is still active.

## Edge Cases and Defensive Checks

- **Empty fee_items** — A held case with fee_status `hold` should have an empty fee_items array and case_total 0.00, not an array of $0.00 entries.
- **Misdemeanor vs felony departure** — Departure analysis may not apply to misdemeanors in some jurisdictions; use `not_evaluated_misdemeanor` or `not_applicable` when the template provides it.
- **Single-count cases with amendments** — The dismissed/amended count is 1 (the original charge was amended away), the convicted count is 1 (the amended charge).
- **Bench trials** — Plea is `not_applicable` for bench trial convictions; use `bench_trial_guilty` for the outcome.
- **No probation ordered** — When no CC-1375 or probation referral was signed, mark probation as `not_ordered`, not `none`.
- **Pro se / unknown counsel** — If no attorney appears in any source, use `unknown` for counsel_type and leave attorney_name as `null` or the placeholder the template expects.
- **DOB completely missing** — Use `"TBD from case file"` and flag with `dob_missing_verify`. Never borrow a DOB from a similarly named defendant.

## What NOT to Do

- Do not post financial entries for cases without a signed final order, regardless of what the finance queue says.
- Do not use stale fee-schedule amounts; always verify the `effective_date` and `end_date`.
- Do not treat "APD" as "public defender" — verify counsel_type from the portal or hearing record.
- Do not add fees the current policy sets to $0.00, even if counter worksheets or old form footers mention them.
- Do not invent identifiers, contact details, or fee amounts — use the exact placeholder the materials require.
- Do not apply drug assessments, lab fees, or other specialized fees to charges that don't trigger them.
- Do not include held/pending cases in batch totals or register sums.
- Do not substitute prose descriptions for enum values required by the answer template.
