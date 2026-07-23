# Portal Endpoints Reference

The Court Operations Portal is the network source of truth. Reach it only via the base URL and allowed endpoint list in `environment_access.md` (default base: `http://task-env:9018/`). It is open within the network — no credentials. Use `GET` only. Do not attempt to read server-side files.

All endpoints return `{"count": N, "results": [ ... ]}` (search returns `query` too). Page/filter by combining query parameters on the relevant fields (`jurisdiction_code`, `case_number`, `fee_type`, `effective_date`, `q`, etc.). When an endpoint does not advertise a specific filter, fall back to `GET /api/search?q=<identifier>` and filter client-side by `result_type`.

## GET /api/jurisdictions
Canonical court/jurisdiction metadata. Use to resolve a court name → `jurisdiction_code` (each result carries the code in `<STATE>-<COUNTY/DISTRICT>` form, e.g. an Arkansas circuit county yields `AR-XX`, an Oregon judicial district yields `ORnn-<COUNTY>`, a Virginia circuit court yields `VA-<COUNTY>`). Filter by `state`/`county`/`court_name` and carry the exact `jurisdiction_code` into every downstream fee-schedule, payment-policy, and form lookup. Fields: `jurisdiction_code`, `court_name`, `county`, `state`, `court_level`, `clerk_office`, `policy_ref`, `phone`, `timezone`, `active`.

## GET /api/cases  /  GET /api/citations  /  GET /api/financial-petitions
Case-management authority for the matter itself.
- `cases`: `case_number`, `jurisdiction_code`, `defendant_first/last`, `defendant_dob`, `counsel_type`, `attorney_name`, `attorney_label_raw`, `attorney_name`, `status`, `disposition_date`, `filed_date`, `judge`, `prosecutor`, `source_system`, `source_updated_at`. This is the **authority for DOB and final status**.
- `citations`: traffic-citation detail — `citation_number`, violation code/speed tier, defendant, hearing date. Use for traffic closeouts.
- `financial-petitions`: petition metadata — `petition_id`, `case_number`, sequence (first / subsequent / default review), submitted date, requested payment, stated balances. Use for installment-order tasks.

Always prefer the `source_system: "AOC-CMS"` (or equivalent authoritative system) record when multiple appear for one identifier; suppress duplicates from "Intake queue" / scratchpads.

## GET /api/charges
Charge-level detail per case: count number, offense code, statute, class, plea, charge disposition, amendment history. Use to confirm the **conviction count** (after amendments) and to reject stale filed counts that were amended away.

## GET /api/docket-entries
Docket text and entry type per case: `entry_id`, `entry_date`, `entry_type`, `text`, `entered_by`, `source`. Use to confirm whether a sentencing/disposition order was entered (finality) and what the bench text actually said — controls departure and hold decisions.

## GET /api/fee-schedules
Fee/cost/assessment authority. Fields: `fee_id`, `jurisdiction_code`, `fee_type` (court_cost, fine, drug/crime-lab assessment, public_defender_user_fee, surcharge, etc.), `amount`, `effective_date`, `end_date`, `mandatory`, `priority`, `label`, `statute`, `violation_code`. **Authority for all posted amounts.** Rules:
- Use only entries whose `effective_date` ≤ disposition date and (`end_date` is null OR `end_date` ≥ disposition date).
- Match `jurisdiction_code` exactly — amounts differ by county.
- Reject labels containing "archived", "old", prior-year fee_ids, and any entry past its `end_date`. These are stale and move to exclusions.
- Where a local worksheet states a different amount, the schedule wins; record a `fee_schedule` audit finding (conflicted → corrected).

## GET /api/payment-policies
Installment plan policy per jurisdiction. Fields: `policy_id`, `jurisdiction_code`, `min_monthly`, `max_monthly`, `first_due_days`, `return_to_court_offset_days`, `account_fee`, `down_payment_required`, `restitution_priority` / restitution rule, `subsequent_petition_rule`, `notes`. Drives plan math and budget support classification. `account_fee` here governs whether an account-management fee is *supported by policy* — if the policy `account_fee` is 0, the fee is `excluded_by_policy`.

## GET /api/forms
Form metadata: `form_id`, `form_name`, `label`, `jurisdiction_code`, `required_fields`, `placeholder_instruction`, `revision_date`, `source_url`. Use to get the `form_id`/label tokens for output, the required fields that may need placeholders, and the exact placeholder instruction (which defines the placeholder string the materials use — confirm it matches `answer_template.json`).

## GET /api/search
Generic cross-type search: `?q=<identifier>` returns mixed `result_type` (`cases`, `charges`, `docket_entries`, `citations`, `financial_petitions`, `forms`). Use as a fallback when a dedicated endpoint doesn't expose the filter you need, or to pull everything for one identifier in one call. Set `q` to a case/citation/petition number.

## Query patterns that resolve the most common conflicts

- **Identity/DOB conflict** → `GET /api/cases?case_number=<id>` (or `/api/search?q=<id>` filtered to `result_type=cases`). The portal DOB wins; never borrow from a same-named row.
- **Counsel-label conflict** (e.g. "APD"/"PD" on paper vs. appointed-private on record) → portal `counsel_type` + the corroborating memo / on-record judge statement. Calendar `attorney_label_raw` is not authoritative.
- **Stale fee amount** → `GET /api/fee-schedules?jurisdiction_code=<code>` then filter to the right `fee_type` and disposition-date-effective row.
- **Plan / bandwidth limits** → `GET /api/payment-policies?jurisdiction_code=<code>` for min/max, first-due offset, return offset, account-fee support.
- **Form tokens / placeholder rule** → `GET /api/forms?jurisdiction_code=<code>`.
