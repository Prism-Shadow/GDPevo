# Quick Reference: Conflict Patterns and Corrections

This file catalogs the recurring conflict patterns observed across training tasks and the correction rules to apply. Use this as a checklist when reconciling any court closeout.

---

## Pattern 1: Finance Queue Uses Archived Fee Amount

**Signal:** Fee line label contains "archived," "old local worksheet," or the amount differs from the current portal schedule for the disposition year.

**Correction:** Replace with the current portal-confirmed amount. Record as an audit finding with `resolution_source: use_fee_schedule`.

---

## Pattern 2: Finance Queue Labels Counsel as PD — But Hearing Notes Say Appointed Private

**Signal:** Queue says `PD C. Hill` or `APD`; hearing notes or defense memo clarify the attorney is appointed private counsel, not the public defender office.

**Correction:**
- Reclassify counsel as `appointed_private`.
- Exclude the public defender user fee from the fee reconciliation.
- Record as an audit finding with `resolution_source: use_hearing_notes` or `use_corrob_memo`.

---

## Pattern 3: Draft Disposition Sheet Says Guilty — But No Signed Order

**Signal:** Draft worksheet or intake page shows a plea and fine, but the hearing notes say the judge did not sign the order, or the matter was continued.

**Correction:**
- Case status = `deferred` / `continued` / `pending`.
- Closeout action = `hold_unsigned_order` or `no_closeout`.
- Fee status = `exclude` / `hold` / `do_not_post_pending`.
- Do **not** include financial entries for this case in register totals.
- Record as audit finding with `resolution_source: use_hearing_notes`.

---

## Pattern 4: Legacy Worksheet Carries Departure Label — Judge Said No Departure

**Signal:** Draft or legacy charge screen says "dispositional departure" or similar, but courtroom audio/hearing notes say the judge stated it was top-of-range, not a departure.

**Correction:**
- Set `departure_status` to `no_departure` / `none`.
- Record as audit finding with `resolution_source: use_hearing_notes`.

---

## Pattern 5: Finance Queue Has DOB or Name Spelling Error

**Signal:** Queue DOB differs by one day from hearing notes, or name spelling differs (e.g., "Simons" vs. "Simmons").

**Correction:**
- Use the hearing-notes value as the corrected value.
- Record as an audit finding (issue_type = `identity`) with `resolution_source: use_hearing_notes`.

---

## Pattern 6: Intake Sticky Notes / Scratchpad Mentions Additional Fees

**Signal:** Intake cover sheet has unchecked sticky notes asking about late-payment fee, collection fee, DMV fee, account-management charge, traffic-school fee, etc.

**Correction:**
- These are **not** charges unless the hearing record or current policy confirms them.
- Add each to the excluded charges list with the appropriate reason code (`not_in_hearing_order`, `not_current_policy`, `no_triggering_event`, `unsupported_post_disposition`).

---

## Pattern 7: Old Form Revision Contains Automatic Charge

**Signal:** An older form copy references an automatic fee (e.g., "$25 payment-plan service charge"), but the current revision does not make it automatic.

**Correction:**
- Do not include the charge unless current court policy separately requires it.
- If included in any scratchpad, exclude it with reason `stale_schedule` or `not_current_policy`.

---

## Pattern 8: Counter Worksheet Has Account-Maintenance Fee Row

**Signal:** Counter or finance memo carries an account-management/maintenance fee, but the supervisor flagged it for policy check, or current jurisdiction policy excludes it.

**Correction:**
- If policy excludes: `account_fee_treatment: excluded_by_policy`, amount = 0.00 in totals.
- If policy includes: `account_fee_treatment: included_by_policy`, include in totals.
- If unclear: `account_fee_treatment: verify_before_entry`.

---

## Pattern 9: Petitioner Requests Non-Standard Payment Application Order

**Signal:** Petitioner asks that restitution be paid before fines/costs (or vice versa), but no order or policy supports the request.

**Correction:**
- Use the jurisdiction's default payment application order from the portal policy.
- If the petition explicitly states an order and the policy allows discretion, use the petition's requested order.

---

## Pattern 10: Missing Identifiers on Required Form Fields

**Signal:** SSN, driver license number, address, phone, probation officer, or probation office location are null in the intake/sentencing data.

**Correction:**
- Enter the placeholder `TBD from case file` for each missing field.
- Do **not** fabricate values.
- List the case in the placeholder_cases / placeholder_fields section of the output with each missing field identified.
