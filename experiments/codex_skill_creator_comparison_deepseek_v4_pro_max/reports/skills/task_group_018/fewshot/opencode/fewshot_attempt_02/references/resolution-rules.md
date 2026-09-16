# Evidence Hierarchy and Conflict Resolution

When local materials and portal records disagree, resolve conflicts with this
hierarchy. Earlier sources defeat later sources on the same factual question.

## Evidence Strength (strongest to weakest)

1. **CMS Portal record** — authoritative for: defendant name spelling, DOB,
   counsel type (counsel_type field), charge offense code, charge statute,
   charge severity, charge disposition on file.
2. **Hearing / bench notes** — authoritative for: what happened in open court
   (plea entered, finding, sentence pronounced, judge's on-the-record
   characterizations including whether a departure was ordered). These notes
   control when the portal charge record has not been updated for an amendment.
3. **Audit / clerk memo** — authoritative for: pointing out specific conflicts
   between other sources, and for instructions the clerk must follow (hold cases,
   verify DOB, check current fee schedule). The memo is not a primary source of
   facts but a guide to what needs reconciling.
4. **Finance queue extract** — low-confidence. Contains carry-forward values
   from draft worksheets and may have stale fees, wrong counsel codes, or
   incorrect defendant names/DOBs. Treat every queued value as needing
   verification against the portal.
5. **Worksheets / spreadsheets** — lowest confidence. Draft figures only. Never
   use worksheet financial amounts without confirming the current portal fee
   schedule.

## Specific Conflict Patterns

### Identity: name or DOB mismatch
- Use the CMS portal record (defendant_first, defendant_last, defendant_dob).
- When the portal DOB is genuinely absent and no other source has it, use
  "TBD from case file".
- When two local sources disagree on spelling (e.g., a finance queue uses a
  variant spelling while the portal shows the correct one), prefer the portal
  over either local source.

### Counsel: PD label vs appointed private
- The portal counsel_type field is authoritative.
- appointed_private means the county pays a private attorney; it is not a public
  defender case. Do not apply the public defender user fee.
- A finance queue label like "PD [name]" can be incorrect — always cross-check
  with the portal. The audit memo may also flag this conflict explicitly.

### Disposition: departure status
- When the judge explicitly says in courtroom notes that the sentence is
  "top-of-range" and no departure finding should be entered, the departure_status
  is no_departure, regardless of any legacy departure label in a worksheet.
- When the judge says nothing about departure and the offense is a misdemeanor,
  departure_status is typically not_evaluated_misdemeanor or
  not_applicable depending on the template enum.

### Status: disposed vs deferred/continued
- A case is only disposed when a signed sentencing order exists. If the hearing
  notes say the judge did not sign the order, or the matter was continued, the
  case is deferred/pending and financial posting must be held.
- Draft worksheets marked "disposed" do not override courtroom reality.

### Charges: amendment
- If the hearing notes state that a charge was amended (e.g., from a drug
  possession count to a non-drug count), the amended charge is the conviction
  charge. The original count was amended away.
- Assessments tied to the original charge type (e.g., drug assessment, crime
  lab fee) do not apply when the conviction is on a non-drug charge.

### Fees: stale schedule
- Always check the effective_date and end_date on portal fee schedule records.
  A record with end_date in the past is archival only.
- An audit memo saying "verify current schedule" means the old amount in the
  finance queue is likely stale.

### Fees: unsupported charges
- Fees not listed in the current portal schedule and not ordered by the court
  should be excluded. Examples: account-management fees, collection fees, DMV
  fees, late fees, traffic-school fees, returned-check fees — unless a current
  schedule or court order directly supports them.

### Fees: fee depends on counsel type
- The public defender user fee applies only when counsel_type is
  public_defender. If the defendant has appointed_private or retained counsel,
  exclude the PD user fee.

## Resolution Source Values

Map to the enum values provided by the answer template. Common values:
- use_cms — resolved by CMS portal record
- use_hearing_notes — resolved by hearing/bench notes
- use_corrob_memo — resolved by audit/clerk corroborating memo
- use_fee_schedule — resolved by current portal fee schedule
- hold_unsigned_order — case held because no signed order exists
- verify_before_entry — requires further verification before posting

## Audit Finding Granularity

Report one audit finding per distinct issue per case. If a single case has both
a counsel conflict and an identity conflict, report two separate findings. Sort
by case_number, then by issue_type.

## Examples

**Example 1 — Identity + Counsel conflict:**
Finance queue has a defendant name variant and a PD counsel label. Portal shows
a corrected spelling and appointed_private counsel with a named attorney.
→ Two findings: identity (use_cms) and counsel (use_corrob_memo).

**Example 2 — Fee schedule stale:**
Finance queue has a drug assessment from a stale prior-year schedule (e.g., a
2023 amount for a 2025 disposition). Portal current schedule shows a higher
current-year amount effective from the current year; the old record has a past
end_date.
→ Use the current amount; create a fee_schedule audit finding.

**Example 3 — No signed order:**
Hearing notes say judge did not sign the final order, or the matter was
continued to a future date. Finance queue has "disposed" status with draft fees.
→ Case is deferred/pending. Hold all financials. Exclude from the register.
Document the next status check date if known.

**Example 4 — Amended charge:**
Hearing notes say the State amended the charge from a controlled-substance count
to a non-drug count. The original drug count wording is not the conviction.
→ Conviction is on the amended charge. Drug assessment does not apply. Report
the amended-away count in dismissed_or_amended_away_counts.

**Example 5 — Judge overrides a departure label:**
A legacy worksheet or charge screen carries a "dispositional departure" label.
The judge's on-the-record statement says "top-of-range, no separate departure
finding."
→ departure_status is no_departure. Use use_hearing_notes as the resolution
source.
