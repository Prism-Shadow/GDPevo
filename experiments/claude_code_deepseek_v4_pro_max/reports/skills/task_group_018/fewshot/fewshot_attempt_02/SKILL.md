# Court Clerk Closeout & Field Packet Skill

## Purpose

Prepare structured clerk-ready JSON outputs for court disposition closeouts, post-sentencing field packets, and financial reconciliation batches. This skill covers criminal, traffic, and civil docket processing where local case materials must be cross-referenced against a centralized Court Operations Portal to resolve conflicts and produce a single authoritative answer.

## When to Use

Invoke this skill when the task involves:
- Closing a criminal or traffic docket batch from hearing notes and finance queue extracts
- Preparing post-sentencing field packets with probation referrals, license suspension orders, and payment plans
- Reconciling financial entries against current fee schedules from a court operations portal
- Identifying audit conflicts between multiple data sources (finance queue, hearing notes, CMS, worksheets, audit memos)
- Producing structured JSON answers matching a court-provided answer template with enums, ISO dates, and two-decimal currency

## Workflow

### Phase 1 — Discovery (Read Everything First)

1. **Read the prompt** (`prompt.txt` or equivalent task instruction). Note:
   - The target cases, citations, or matter IDs.
   - The list of available API endpoints and the portal base URL.
   - The expected output schema (usually `answer_template.json`).
   - Any special instructions about unsupported fees, placeholder rules, or source priority.

2. **Read every payload file** in the input payloads directory. Typical payload types:
   - **Hearing notes / bench sheets**: The courtroom record — plea, finding, sentence, judge remarks. This is the *highest-authority narrative source* for what happened in court.
   - **Finance queue extracts / worksheets**: Pre-populated financial data. May contain stale, draft, or carry-forward values. Treat as *tentative* until verified against the portal.
   - **Audit memos / clerk review notes**: Flagged conflicts that need resolution. Pay close attention to every flagged issue.
   - **Form field excerpts / local form references**: Metadata about local forms, required fields, and placeholder conventions.
   - **Petition summaries / sentencing intake sheets**: Case detail records (defendant info, charges, sentences, probation details).
   - **The answer template**: This IS the output schema. Every required key, enum value, sort order, and format rule is defined here. Study it before producing output.

3. **Read `environment_access.md`** for the portal base URL and allowed endpoints. Ignore any `localhost`, `127.0.0.1`, or `env/setup.sh` references in the task materials — use the base URL from `environment_access.md`.

### Phase 2 — Query the Court Operations Portal

Query **only** the endpoints listed in the prompt or `environment_access.md`. Common endpoints and their uses:

| Endpoint | Use |
|---|---|
| `GET /api/cases` | Verify case records, defendant identity, status |
| `GET /api/charges` | Confirm charge details, offense codes, amendments |
| `GET /api/docket-entries` | Check for signed orders, entry history |
| `GET /api/fee-schedules` | Get current fee amounts (overrides any locally cached value) |
| `GET /api/payment-policies` | Verify policy rules for payment plans, fee exclusions |
| `GET /api/forms` | Confirm form IDs, labels, and required fields |
| `GET /api/citations` | Verify traffic citation records |
| `GET /api/jurisdictions` | Confirm jurisdiction codes |
| `GET /api/financial-petitions` | Verify petition status, submitted details |
| `GET /api/search` | Cross-reference defendants, cases, or docket entries |

**Query strategy**: Fetch data for every target case/citation from every relevant endpoint. Do not skip endpoints — the fee schedule may contain a current amount that overrides a locally cached figure, and the docket entries may reveal whether a final order was signed.

### Phase 3 — Cross-Reference and Identify Conflicts

Compare the local payloads against the portal data. Look for every type of discrepancy:

1. **Identity conflicts**: Name spelling, DOB mismatch between finance queue and hearing notes/counsel memo. The portal CMS data is authoritative for identity; if CMS is unavailable, use the corroborating memo or hearing notes over the finance queue.

2. **Counsel classification conflicts**: A "PD" label in the finance queue may actually be appointed private counsel. The hearing notes or clerk audit memo resolves this. Critical because it affects whether a public defender user fee applies.

3. **Fee schedule conflicts**: Any locally cached or archived fee amount (e.g., a 2023 drug assessment, an old SOF table) must be verified against the current portal fee schedule. The portal wins.

4. **Status conflicts**: A case marked "disposed" in the finance queue may have no signed final order. If the hearing notes or docket entries confirm no order was signed, the case must be held/excluded from the disposed register.

5. **Departure conflicts**: A worksheet may carry a departure label from a draft; the judge's on-record statement controls. Hearing notes override worksheet departure labels.

6. **Charge conflicts**: A finance queue or worksheet may list an original charge that was amended in court. The hearing notes record what was actually adjudicated.

7. **Financial omissions**: The finance queue may omit fees the judge ordered (e.g., a lab assessment mentioned from the bench, a public defender user fee on a case with public defender representation).

**Record every conflict** you find — each one becomes an audit finding or informs a correction in the final output.

### Phase 4 — Resolve Conflicts

Apply these resolution rules (derived from the hierarchy of evidence):

| Priority | Source | When to Use |
|---|---|---|
| 1 (highest) | Judge's on-record statement / hearing notes | Controls plea, finding, sentence, departure status, fee waivers, whether an order was signed |
| 2 | Portal CMS / fee schedule / docket entries | Authoritative for current fee amounts, identity/DOB verification, whether a signed order exists |
| 3 | Clerk audit memo / corroborating memo | Resolves counsel classification and identity when hearing notes are ambiguous |
| 4 | Signed sentencing order | Confirms final disposition; its absence means hold/exclude |
| 5 (lowest) | Finance queue / worksheet | Starting point only — every value is tentative and subject to override by higher sources |

**When sources disagree**: The higher-priority source always wins. Document the conflict, the conflicted value, the corrected value, and which source resolved it.

**When a value is genuinely missing** (e.g., DOB blank on bench card, no driver's license number in case file):
- Use the placeholder `"TBD from case file"` — do NOT invent values, do NOT borrow from similarly named defendants, do NOT guess.
- This applies to: SSN, DL number, mailing/residence address, phone number, probation officer name, probation office location.

### Phase 5 — Reconcile Financials

For each matter, compute the corrected financial entry:

1. **Start with the hearing notes**: What fine did the judge announce? What costs were ordered? What fees were mentioned from the bench?
2. **Verify every fee against the current portal fee schedule**: If the portal shows a different amount than any local source, use the portal amount.
3. **Apply policy rules**: Check payment policies from the portal. Exclude fees that have no triggering event (e.g., late fees when nothing is late, collection fees with no referral, DMV fees with no DMV action, account-management fees not in current policy).
4. **Calculate totals**: Sum the corrected fee items. For the register, aggregate across all disposed cases separately from held/excluded cases.
5. **Payment plan math** (when applicable):
   - `full_payment_count = floor(total_due / monthly_payment)` — the number of full installments
   - `final_payment_amount = total_due - (full_payment_count * monthly_payment)` — the remainder
   - If `final_payment_amount == 0`, the final installment equals the regular amount and `total_installments = full_payment_count`
   - Otherwise `total_installments = full_payment_count + 1`
   - `final_due_date` = `first_due_date` + `(total_installments - 1)` months
   - `down_payment` offsets `total_due` before computing installments when non-zero

### Phase 6 — Build the Output

1. **Follow the answer template exactly**. Match every required key, enum value, sort order, and format rule.
2. **Sort items** as specified (by case_number, citation_number, petition_id, or field name ascending).
3. **Use ISO dates** (YYYY-MM-DD). Use `null` for dates that should not be entered (e.g., no disposition date for pending/continued cases).
4. **Use two-decimal currency numbers** (e.g., `150.00`, not `150`).
5. **Use enum values verbatim** from the template — do not paraphrase or substitute prose.
6. **Return one JSON object** — no markdown wrapping, no explanatory text outside the JSON.
7. **Do not add unsupported fees, balances, conditions, identifiers, or contact information** that are not ordered by the court or supported by the portal record.

## Common Resolution Patterns (Reference)

### Identity / DOB Conflict
Finance queue has one name/DOB; hearing notes or audit memo has a correction. Resolution: Use the corrected identity from hearing notes or memo. If identity still uncertain, verify against CMS. If DOB is genuinely blank with no source, use `"TBD from case file"`.

### Counsel Classification: "PD" vs Appointed Private
Finance queue labels counsel as "PD" but defense memo says appointed private. Resolution: `counsel_type = "appointed_private"`. Do NOT post a public defender user fee for appointed private counsel.

### Fee Schedule: Stale Amount
Local worksheet has an archived/old fee amount. Resolution: Query the portal fee schedule. Use the current amount. Document the stale value and the corrected value.

### Departure: Worksheet vs Judge's Statement
Worksheet carries a departure label; judge said no departure. Resolution: Judge's statement controls. `departure_status = "no_departure"` or `"none"` as appropriate.

### No Signed Final Order
Finance queue shows "disposed" but hearing notes say order not signed / matter continued. Resolution: Status is `"deferred"` or `"pending"`, closeout action is `"hold_unsigned_order"`, financial entry is `"hold"` or `"do_not_post_pending"`, and the case is excluded from the disposed register totals.

### Charge Amendment
Original charge on worksheet differs from what was adjudicated. Resolution: The amended charge from hearing notes is the conviction count. The original charge counts as dismissed/amended away. Fee applicability follows the conviction charge type.

### Unsupported / Excluded Charges
Fees that appear in intake notes but are not supported: late fees (no default), collection fees (no referral), DMV fees (no DMV event), returned-check fees (no returned check), account-management fees (not in current policy), traffic-school fees (not ordered), restitution (no restitution order). Resolution: Exclude with the appropriate reason code.

### Missing Identifiers (Placeholder Rule)
When a required form field cannot be completed from any source: Use `"TBD from case file"`. Applies to: SSN, driver's license number, mailing address, residence address, phone number, probation officer name, probation office location. Never invent values.

## Portal Interaction Notes

- The portal is read-only (GET only). Do not attempt POST/PUT/DELETE.
- Always use the portal to verify current fee schedules before finalizing financial entries. A locally cached amount is NOT authoritative.
- Query the portal for each target case/citation individually when the API supports it. Use `/api/search` for cross-referencing when direct lookups are inconclusive.
- The portal may return jurisdiction codes, form metadata, and policy documents. Use these to confirm the correct form IDs, labels, and policy rules for the output.
