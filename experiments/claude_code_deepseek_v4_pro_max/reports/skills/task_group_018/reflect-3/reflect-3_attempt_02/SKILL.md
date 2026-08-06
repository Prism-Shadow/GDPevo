# Court Operations Reconciliation Skill

## When to Use This Skill

Use this skill when asked to prepare a court clerk closeout, disposition register, post-sentencing packet, or financial reconciliation across multiple case matters. The skill covers reconciling court records from multiple sources — case management systems (CMS), hearing notes, financial queues, audit memos, and payment petitions — into a single structured clerk-ready output.

---

## Core Methodology

### 1. Gather All Sources Before Deciding

Read every provided source document and query the portal for every relevant case, charge, docket entry, fee schedule, form, payment policy, and petition. Never base a decision on one source alone. The sources to collect include:

- **Portal/CMS**: case records, charge records, docket entries, fee schedules, payment policies, forms, petitions, citations
- **Local payloads**: hearing notes, audit memos, worksheets, financial queue extracts, petition summaries, sentencing intake sheets, form-field excerpts
- **Supporting documents**: clerk review notes, supervisor notes, corroborating memos

### 2. Resolve Conflicts with the Source Hierarchy

When two sources disagree on the same fact, resolve in this order of authority:

1. **Hearing notes / courtroom record** — what the judge pronounced in open court
2. **CMS / portal case record** — the official case management system
3. **Corroborating memos** — clerk audit memos, supervisor notes, defense cover memos
4. **Local worksheets / finance queue** — draft or carry-forward values, lowest authority

For fees specifically: **current fee schedule** > **stale/archived schedule**. Always verify the schedule effective on the disposition date, not a prior year's amount.

### 3. Identify and Document Every Conflict

For each matter, compare every field across all sources. Flag every mismatch as an audit finding with:
- The **case number** the conflict belongs to
- The **issue type** (identity, counsel, status, fee_schedule, departure)
- The **conflicted value** exactly as it appears in the lower-authority source
- The **corrected value** from the higher-authority source
- The **resolution source** explaining which source was authoritative

Common conflict patterns:
- **Identity**: DOB differs between finance queue and CMS
- **Counsel**: finance queue says "PD" but defense memo shows appointed private counsel
- **Status**: finance queue says "disposed" but no signed final order exists
- **Fee schedule**: queue carries a stale assessment amount; current schedule has a different value
- **Departure**: legacy charge screen carries a departure label the judge expressly rejected

### 4. Determine Case Status and Closeout Action

For each case, determine whether to enter a disposition or hold:

- **Enter disposition** when: status is disposed, a signed sentencing order exists, and the matter reached final resolution
- **Hold / exclude** when: no final order was signed, matter is deferred/pending/continued, or status checks are still needed
- A case that appears "disposed" in a finance queue but has no signed order should **not** have financial entries posted

### 5. Reconcile Fees Against the Current Schedule

For each disposed case, build the fee entry from scratch — do not carry forward the queue's amounts uncritically:

1. Start with amounts pronounced in court (hearing notes)
2. Cross-check against the **current** fee schedule for the jurisdiction and disposition date
3. If the queue uses a stale schedule, replace with the current amount
4. Apply counsel-type rules:
   - **Public defender** → include the PD user fee (unless waived on the record)
   - **Appointed private counsel** → do NOT include the PD user fee
   - **Retained counsel** → no PD user fee
5. Add mandatory court costs per the current schedule
6. Add mandatory assessments only when the conviction triggers them (e.g., drug assessment on controlled-substance counts, lab fee when judge orders it)

### 6. Exclude Unsupported Fees

Do not add fees that lack a trigger event or current-policy support. Specifically exclude:
- Late-payment fees when no payment is overdue
- Collection referral fees when no referral has been made
- DMV fees when no DMV action has been ordered
- Returned-check fees when no returned payment exists
- Account-management fees unless current policy explicitly authorizes them
- Restitution when no restitution order appears in the record
- Traffic-school fees when traffic school was not ordered
- Stale-schedule amounts that have been superseded

### 7. Compute Payment Plans

When a payment plan is ordered:

1. **Total due** = fines + costs + assessments + authorized fees − restitution (handled separately)
2. **Monthly payment** = the court-approved amount (from hearing notes or petition order)
3. **First due date** = disposition date + policy's `first_due_days` offset
4. **Number of full installments** = floor(total_due / monthly_payment)
5. **Final payment amount** = total_due − (full_installments × monthly_payment); if zero, the plan pays evenly
6. **Total installments** = full_installments + (1 if final_payment > 0 else 0)
7. **Final due date** = first_due_date + (total_installments − 1) months
8. **Return-to-court date** = offset from the petition date per policy

For budget review: compute `disposable_income = monthly_income − monthly_obligations`. Classify as `supported_by_budget` when the approved amount fits within the policy's min–max band and does not exceed disposable income. Classify as `below_policy_minimum` or `above_policy_maximum` when the amount falls outside the band.

### 8. Handle Missing Identifiers with Placeholders

When a required field lacks a value in all available sources, use the designated placeholder — never invent:
- Missing SSN, driver's license number, address, phone → `"TBD from case file"`
- Missing DOB (genuinely blank in CMS, not just unverified) → `"TBD from case file"`
- Missing probation officer or office location → `"TBD from case file"`

The placeholder rule is: **use it for identifiers, contact details, and office assignments that are missing from all case materials**. Do not use it for values you can derive from the record (amounts, dates, statuses).

### 9. Build the Structured Output

Follow these rules for every output:

- **Required keys**: Include every required top-level key from the answer template. Empty sections should be empty arrays `[]`, not omitted.
- **Sorting**: Sort items by the field specified in the template (typically `case_number` or `citation_number` or `petition_id` ascending).
- **Dates**: ISO 8601 `YYYY-MM-DD`. Datetimes: `YYYY-MM-DDTHH:MM:SS`.
- **Currency**: Numbers to exactly two decimal places (e.g., `150.00`, not `150` or `150.0`).
- **Enums**: Use the exact string values defined in the template's enum lists. Do not substitute prose or synonyms.
- **Null handling**: Use `null` for date fields that should not carry a value (e.g., disposition_date when no disposition was entered). Do not use empty strings for dates.

### 10. Compute Register / Batch Totals

For batch closeouts:
- **Assessed/Disposed count**: number of cases with financial entries posted
- **Held/Excluded count**: number of cases without a final order, excluded from the register
- **Category totals**: sum each fee type (fine, court_cost, assessment, user_fee) across all posted cases
- **Grand total**: sum of all category totals

For multi-matter payment-plan batches:
- **Combined amount due**: sum of all matters' `amount_due`
- **Unsupported charge total**: sum of all excluded charge amounts (tracked for audit)

---

## Cross-Domain Patterns

These patterns hold regardless of jurisdiction (Arkansas criminal, Oregon traffic, Virginia post-sentencing):

| Pattern | Rule |
|---------|------|
| Stale schedule amounts | Replace with current schedule; flag in audit |
| PD user fee | Post only when counsel_type is `public_defender` |
| "APD" label ambiguity | "APD" on a calendar may mean appointed private, not public defender — verify with defense memo or judge's record |
| Draft/disposition conflict | Hearing notes beat finance queue; CMS status beats worksheet status |
| Unsigned order | Hold all financial entries; do not post to register |
| Departure override | Judge's oral pronouncement overrides legacy charge-screen departure labels |
| Payment priority | Follow the jurisdiction's policy (`restitution_priority` field) |
| Account fee treatment | Default to `excluded_by_policy` unless current policy explicitly authorizes it |
| License suspension basis | Use conviction date unless the record specifies release date as the trigger |
| Probation referral | Only prepare CC-1375 when supervised probation was ordered and a report datetime exists |

---

## Workflow Summary

```
1. READ all local payloads and the answer template
2. QUERY the portal for every relevant case, charge, docket entry, fee schedule, form, policy, petition
3. For each matter:
   a. Reconcile identity (name, DOB) across all sources
   b. Reconcile counsel classification
   c. Determine actual case status and closeout action
   d. Reconcile charges: plea, disposition, sentence, departure status
   e. Reconcile fees: current schedule, counsel-triggered fees, assessments
   f. Compute payment plan math (if applicable)
   g. Identify unsupported fees for exclusion
   h. Document placeholder fields (if applicable)
4. BUILD the output object matching the answer template exactly
5. SORT every section as specified
6. COMPUTE batch/register totals
7. VERIFY: every required key present, all enums valid, all amounts to 2 decimals, all dates ISO
```
