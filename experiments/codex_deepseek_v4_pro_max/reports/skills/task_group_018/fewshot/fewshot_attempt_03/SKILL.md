---
name: court-operations-portal
description: Work with the Court Operations Portal REST API to prepare clerk-ready structured answers for criminal sentencing closeouts, traffic violation dispositions, post-sentencing field packets, and financial/payment-plan reconciliation. Use this skill whenever the task involves a Court Operations Portal at a base URL, local court payloads (hearing notes, audit memos, finance extracts, form excerpts, petition/budget worksheets), and a JSON answer template.
---

# Court Operations Portal — Clerk Reconciliation Agent

Follow these instructions when the task requires you to interact with a Court Operations Portal at a configurable `<TASK_ENV_BASE_URL>` and produce a structured JSON answer matching a provided `answer_template.json`.

## 1. Portal API Endpoints

The portal exposes RESTful GET endpoints. The set available in a given task is listed in the prompt. Understand what each returns:

- `/api/jurisdictions` — jurisdiction codes (e.g., `AR-RC`, `OR22-JEFF`) and fee/policy affiliations.
- `/api/cases` — case records indexed by case number. Returns defendant identity, counsel, status, charges, and disposition posture.
- `/api/charges` — charge detail per case: statute, offense code, plea, disposition, sentencing elements.
- `/api/docket-entries` — docket events per case (sentencing orders, continuances, holds).
- `/api/citations` — traffic/misdemeanor citation records (defendant, violation code, officer, event date).
- `/api/fee-schedules` — jurisdiction-specific fee tables for fines, court costs, assessments, surcharges, and user fees. **Always prefer the current schedule over archived amounts.**
- `/api/payment-policies` — payment-plan policy bands (minimum monthly, maximum monthly), account-fee treatment rules, payment-application ordering, and default first-due-date offsets.
- `/api/forms` — form metadata including form IDs, local labels, field groups, and whether a form applies to a given jurisdiction or case type.
- `/api/financial-petitions` — filed payment petitions: submitted dates, requested amounts, budget data, balances.
- `/api/search` — keyword or identifier lookup across cases, citations, and petitions.

**Query strategy**: Start by fetching jurisdiction, fee-schedule, and payment-policy data (shared across all cases). Then fetch case/citation records individually. Use `/api/search` to resolve ambiguous identifiers. Cache portal responses within the task; do not re-query the same endpoint+parameter combination.

## 2. Working with Answer Templates

Each task provides an `answer_template.json` in `input/payloads/`. Treat it as the **authoritative schema**. It defines:

- `required_top_level_keys` — the sections your answer must contain.
- `ordering_rules` — how to sort lists (typically by case_number, citation_number, or petition_id ascending).
- `enums` — the closed vocabulary for every categorical field. **Never substitute prose for an enum value.**
- `field_rules` / `instructions` — currency precision (two decimal places, numeric), date format (ISO `YYYY-MM-DD`), datetime format (`YYYY-MM-DDTHH:MM:SS`).

**Schema-first approach**: Before filling any values, read the template thoroughly and map each required key to the data sources that can satisfy it (portal, hearing notes, memo, etc.).

## 3. Data Sources and Reconciliation Priority

Every task provides local payload files and portal access. When sources conflict, use this priority hierarchy:

1. **Portal API (CMS)** — the system of record for case identity, docket entries, active fee schedules, payment policies, and form metadata. Treat it as authoritative for identity when no courtroom correction was made.
2. **Hearing notes / courtroom audio** — override the portal for judge-announced findings, plea changes from the bench, departure rulings, and in-court identity corrections.
3. **Corroborating memos / defense cover sheets** — override the portal or finance queue for counsel-type corrections (e.g., an `APD` abbreviation that actually means appointed private counsel).
4. **Finance queue / worksheet extracts** — use for initial fee lines but **always validate against the portal's current fee schedule**.
5. **Form excerpts / local intake sheets** — use for form field labeling, account-reference conventions, and stale-charge identification, but reconcile with portal form metadata.

### Resolution Source Values

When documenting corrections in an audit section, use these resolution-source enums consistently:

- `use_cms` — portal is authoritative.
- `use_hearing_notes` — courtroom notes override.
- `use_corrob_memo` — defense memo / audit memo override.
- `use_fee_schedule` — current portal schedule overrides stale worksheet amounts.
- `hold_unsigned_order` — no signed order exists; hold everything.
- `verify_before_entry` — data is genuinely missing; cannot enter until verified.
- `exclude_pending` — matter has no final disposition; exclude from register.

## 4. Fee Reconciliation Rules

### Fee Codes

Standard codes across jurisdictions include:

| Code | Meaning | Typical trigger |
|------|---------|-----------------|
| `fine` | Criminal or traffic fine | Announced at sentencing |
| `court_cost` | Mandatory court cost | Every disposed case |
| `drug_assessment` | Drug crime assessment fee | Controlled-substance conviction |
| `public_defender_user_fee` | PD reimbursement fee | PD-represented defendant, conviction entered |
| `crime_lab_fee` | Crime laboratory fee | Controlled-substance or lab-tested evidence case |
| `county_surcharge` | County add-on surcharge | Jurisdiction-specific |

### Exclusion Rules

**Exclude a fee** (do not post) when:
- No triggering event occurred (no late payment, no returned check, no collection referral, no DMV action, no traffic school order).
- The fee schedule source is stale (archived or pre-revision amount).
- The fee is not supported by current policy (e.g., a $25 account-management fee removed in the current revision).
- The case has no signed final order (status: hold / continued / deferred).
- A statutory maximum is cited but the hearing order did not invoke it.

### Fee Status Values

- `post` — enter the fee into the register.
- `exclude` — do not post; list in exclusions.
- `hold` — defer posting until a signed order is available.
- `do_not_post_pending` — case is not disposed.

## 5. Identity and Counsel Auditing

### Identity Conflicts

When names or DOBs differ between the finance queue, hearing notes, and portal:
- Check the portal record first (CMS is the system of record).
- If the hearing notes record a specific correction from the defense table, apply that correction and cite `use_hearing_notes` or `use_corrob_memo`.
- If a DOB is genuinely blank and no source can supply it, use `"TBD from case file"` with resolution `verify_before_entry`.
- **Never borrow a DOB from a similarly-named defendant** in search results.

### Counsel Classification

- `public_defender` — represented by the public defender office (e.g., labeled `PD`).
- `appointed_private` — private attorney appointed and paid by the county (labeled `APD` on calendar, "appointed private" in memo). **Do not conflate `APD` with public defender.**
- `retained` — privately retained by the defendant (labeled `RET`).
- `unknown` — truly cannot determine.

### Public Defender User Fee

Only post the PD user fee when:
- The defendant was represented by a **public defender** (not appointed private counsel).
- A conviction was entered.
- The current fee schedule includes the amount.

## 6. Payment Plan Mathematics

When a post-disposition payment plan is approved, compute the schedule as follows:

1. `total_due` = sum of all postable fees after exclusions.
2. `regular_installment_amount` = the court-approved monthly payment.
3. `full_payment_count` = `floor(total_due / regular_installment_amount)` — the number of full regular payments.
4. `final_payment_amount` = `total_due - (full_payment_count * regular_installment_amount)` — the remainder. If zero, the last regular payment is the final one.
5. `total_installments` = `full_payment_count + 1` (if `final_payment_amount > 0`) else `full_payment_count`.
6. `final_due_date` = `first_due_date + (total_installments - 1) months`.
7. `return_to_court_date` — use the petition's candidate date or compute as `final_due_date + 2 months`.

For `down_payment`, default to `0.00` unless the hearing order or petition specifies otherwise.

## 7. Probation Referral (CC-1375) and License Order (CC-1379)

These standard forms appear in post-sentencing packets:

### CC-1375 (Probation Referral)

- `cc1375_status`: `prepare_referral` if supervised probation was ordered; `not_ordered` if no referral was signed.
- `probation_term_months`: from sentencing intake or hearing notes. Use `0` when no probation was ordered.
- `report_datetime`: the scheduled report date-time from the probation notes, or `null` if not ordered.
- Missing officer/office details: use `"TBD from case file"`.

### CC-1379 (License Suspension and Installment Payment Order)

- `license_start_basis`: `conviction_date` by default (license suspension runs from conviction, not release).
- `suspension_months`: from sentencing intake or hearing notes.
- `suspension_end_date` = `suspension_start_date + suspension_months`.
- `driver_license_number`: use `"TBD from case file"` when the number is absent from all sources.

## 8. Placeholder Convention

When a form field is required by the template but the value cannot be found in any source (portal, hearing notes, memos, intake sheets):

- Use the exact string `"TBD from case file"`.
- Document the field in the `placeholder_fields` or `placeholder_cases` section with a `reason_code`.
- **Never invent** identifiers (SSN, driver license number), contact details (address, phone), or office details (probation officer name, office location).

## 9. Register and Batch Totals

When computing batch-level register totals:

- Sum only cases with `fee_status: "post"`.
- Count cases with `fee_status: "hold"` or excluded separately.
- Report: `assessed_case_count` / `disposed_case_count`, `held_case_count` / `excluded_pending_count`.
- Break down totals by fee code category (`fine_total`, `court_cost_total`, `assessment_total`, `user_fee_total`, `crime_lab_fee_total`) before summing to `grand_total` or `batch_total_due`.

## 10. Exclusions

Every closeout must identify what is **not** being posted:

- **Cases**: continued without final order, deferred with unsigned order.
- **Fees**: unsupported charges (no triggering event, stale schedule, not current policy).
- **Identifiers**: missing fields documented as placeholders.

List exclusions sorted by case_number or charge_code ascending, with a `reason_code` from the template's enum.

## 11. General Workflow

For any court closeout task, follow this sequence:

1. **Load the answer template** and identify all required sections, enums, and ordering rules.
2. **Read all local payloads** — hearing notes, audit memos, finance extracts, form excerpts, petition/budget sheets.
3. **Query the portal** — start with jurisdiction, fee schedules, and payment policies; then fetch case/citation records.
4. **Reconcile identity and counsel** — compare sources, resolve conflicts, document resolution.
5. **Determine dispositions** — for each case, establish the plea, finding, and disposition date from hearing notes + portal.
6. **Reconcile fees** — cross-reference finance queue against current portal fee schedule; exclude unsupported items.
7. **Compute payment plans** — if post-disposition plans are approved, calculate installment schedules.
8. **Handle forms** — populate CC-1375, CC-1379, or local form entries from portal form metadata + hearing notes.
9. **Document placeholders** — list every field that cannot be completed from available sources.
10. **Compute totals** — sum postable fees and produce register/batch totals.
11. **Output JSON** — single object, no markdown wrapping, all enum values from the template, sorted by the template's ordering rules.
