# Reconciliation Rules

## Conflict Resolution Hierarchy

When two or more sources disagree on a fact, resolve using the priority chain below. Higher-numbered sources override lower-numbered ones.

### Priority 1 — Courtroom Hearing Notes / Bench Statements

The judge's oral pronouncements on the record override everything else. This includes:

- Disposition outcome (guilty, dismissed, deferred, continued)
- Departure status (whether a departure was expressly granted or expressly withheld)
- Plea accepted
- Sentence terms (fine amount, jail days, probation months, license suspension)
- Counsel identity corrections noted during the hearing

Even when a finance queue extract or a draft worksheet says something different, the hearing notes control.

Example: A legacy charge screen carries a "dispositional departure" label, but the hearing notes quote the judge saying "no separate departure finding." The corrected value is `no_departure`, source `use_hearing_notes`.

### Priority 2 — Clerk Audit / Corroboration Memos

Clerk memos that document cross-checks against the paper packet override finance queue extracts on:

- Identity facts: defendant name spelling, date of birth
- Counsel classification: whether counsel is truly public defender, appointed private, or retained

Example: The finance queue labels counsel as "PD" but the audit memo confirms the attorney is appointed private counsel paid by the county, not a public defender. The corrected value is `appointed_private`, source `use_corrob_memo`.

### Priority 3 — Current Portal Records

The Court Operations Portal provides authoritative current values for:

- Fee schedule amounts (override archived or stale amounts)
- Payment policy rules (override old worksheets or sticky notes)
- Form metadata and field requirements (override local excerpts if they differ)
- CMS case records for identity verification when higher sources are silent

Example: A finance worksheet uses a 2023 drug assessment amount of $125, but the current portal fee schedule shows $250. The corrected value comes from the portal, source `use_fee_schedule`.

### Priority 4 — Docket Entries / Minute Notes

When no final signed order exists, the case cannot be disposed. A draft worksheet showing "guilty / fine / costs" does not matter if the judge did not sign the order.

- Cases with no signed order: status is `deferred` or `pending_exclude`, financials are held at zero, no register entry is posted.
- Cases with a signed order: can proceed to disposition entry.

Example: A draft disposition sheet shows sentencing amounts, but the docket note says the final order was not signed. Closeout action is `hold_unsigned_order`, fee status is `hold`, case total is zero.

### Priority 5 — Finance Queue Extracts

Lowest authority. Use finance queue values only when no higher-priority source conflicts. Even then, verify amounts against the current fee schedule from the portal.

## Common Reconciliation Patterns

### Identity Conflict

When a name or DOB differs between the finance queue and a corroborating source:
- Use the hearing notes or audit memo for the correct value.
- Record the conflict as `issue_type: "identity"`, with the queue value as `conflicted_value` and the corrected value in `corrected_value`.
- Source: `use_corrob_memo` or `use_cms`.

### Counsel Classification Conflict

When counsel is labeled "PD" in the queue but the audit memo or hearing notes show otherwise:
- If the attorney is appointed private counsel paid by the county, classify as `appointed_private`.
- Do not post a public defender user fee for appointed-private cases.
- Record as `issue_type: "counsel"`.

### Fee Schedule Conflict

When a worksheet or queue carries an old or wrong fee amount:
- Query the current fee schedule from the portal for the jurisdiction.
- Record the discrepancy as `issue_type: "fee_schedule"`.
- Use the current schedule amount in the corrected reconciliation.

### Departure Status Conflict

When a legacy label or draft worksheet asserts a departure that the judge did not grant:
- The hearing notes control.
- If the judge expressly rejected a departure: `no_departure`.
- If the judge expressly granted a departure: `dispositional_departure` or `durational_departure`.
- If departure rules do not apply (misdemeanor, deferred case): `not_applicable` or `not_evaluated_misdemeanor`.
- Record as `issue_type: "departure"`.

### Status / Deferred Case Conflict

When a draft disposition sheet says "disposed" but no final order was signed:
- Record as `issue_type: "status"`.
- Corrected status: `deferred`.
- Closeout action: `hold_unsigned_order`.
- Fee status: `hold`, all amounts zero.

## Audit Flag Codes

When building audit structures, use these flag patterns:

| Flag | Meaning |
|------|---------|
| `apd_label_not_public_defender` | Calendar abbreviation "APD" is not the public defender; counsel is appointed private |
| `amended_non_lab_conviction` | Charge was amended away from a lab-eligible offense to a non-lab offense |
| `lab_fee_worksheet_omitted` | Worksheet omitted a lab fee that the judge ordered on the record |
| `dob_missing_verify` | DOB is genuinely blank; must verify from case file before permanent entry |
| `no_final_order_pending` | No final order was signed; matter is continued/pending |
