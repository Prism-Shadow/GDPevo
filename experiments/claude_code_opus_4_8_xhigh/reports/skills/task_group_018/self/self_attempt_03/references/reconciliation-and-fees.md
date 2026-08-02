# Reconciliation ladder, counsel/fee logic, and status gating

## The conflict-resolution ladder (detail)

Local drafts routinely disagree with the truth. For each field, resolve in this order and
record the correction wherever the template has an audit/exception list.

### Identity (name, DOB)
- Authoritative: portal case/citation record; a corroborating memo confirms it.
- A queue/worksheet misspelling or off-by-one DOB is corrected to the verified value.
- **Never** import a DOB or name from a *different, similarly named* party surfaced in
  search results.
- If a required identifier is missing from every source, use the exact placeholder and
  flag it for verification (do not guess).
- Resolution-source enums typically distinguish "use CMS/portal", "use corroborating
  memo", "use placeholder / verify".

### Counsel type and fee eligibility
- A calendar or queue abbreviation (e.g., a raw "PD" / "APD" label) is often wrong.
  Correct it using the judge's on-record clarification, the defense memo, and the
  portal's resolved `counsel_type`.
- Eligibility rule: a **public-defender user fee applies only to a true public
  defender**. `appointed_private` (county-paid private counsel) and `retained` counsel
  are **not** PD-fee eligible — remove any PD user fee a draft carried for them.
- Conversely, if the defendant *is* PD-represented, the bench did not waive the fee, and
  the current schedule includes it, then a draft that **omitted** it should have it
  **added** back.

### Disposition, plea, sentence, departure
- The signed courtroom result is authoritative over any draft/worksheet.
- Use the judge's explicit words: e.g., a draft "dispositional/durational departure" is
  corrected to **no departure** if the judge said the sentence was top-of-range with no
  separate departure finding.
- Misdemeanor counts may not require a departure evaluation at all — use the template's
  `not_evaluated_misdemeanor`/`not_applicable`-style enum rather than inventing one.

### Charges convicted (and conviction-linked fees)
- Record the count actually **convicted**. If a count was **amended** (e.g., from a
  controlled-substance count to misdemeanor theft), the conviction is the amended charge;
  the original count is dismissed/amended-away.
- A fee that attaches to a *specific* conviction (lab / drug-crime assessment) is posted
  **only if** the defendant was convicted of that offense. If the conviction was amended
  away from that offense, exclude the linked fee. If a controlled-substance conviction
  stands and the schedule/judge requires the lab assessment, post it even if a worksheet
  omitted it.

## Unsupported-fee catalog (exclude unless directly supported)

Post a line **only** when a signed order, the portal record, or the current schedule/
policy supports it. Otherwise route it to the exclusion list with the matching reason
code. Commonly-seen unsupported add-ons:

| Item | Why excluded (typical reason code) |
|---|---|
| Account-management / -maintenance fee | not current policy / policy `account_fee` = 0 |
| Collection referral fee | no triggering event / not in hearing order |
| Late-payment fee | no default/late event on the record |
| DMV / license-reinstatement fee | not ordered / no policy support |
| Returned-check fee | no returned-payment event |
| Traffic-school / program fee | not in hearing order |
| Copy / certification fee | no supporting order |
| Court-appointed-attorney fee | intake "do not add" / no order |
| Court-reporter fee | intake "do not add" / no order |
| Restitution | only if a restitution order exists; else 0/excluded |
| Obsolete footer/service charge (e.g., old plan service charge) | superseded by current policy |
| Statutory-maximum substitution | a standard current schedule applies instead |
| Stale prior-year schedule amount | superseded by the row effective on disposition date |

Rule of thumb: **"no triggering event, no signed order, or not in the current
schedule/policy" ⇒ exclude.** Match the exact `reason_code` enum in the template
(`stale_schedule`, `not_in_hearing_order`, `not_current_policy`, `no_triggering_event`,
`unsupported_post_disposition`, `no_order_or_policy_support`, `not_part_of_balance`, …).

## Status gating (unsigned / continued / deferred)

- Only enter a disposition and post financials when the matter is **disposed with a
  signed final order**.
- If the order was not signed, the matter was continued, plea paperwork was incomplete,
  or the sheet is marked "draft only":
  - Do **not** create a sentencing/financial register entry.
  - Use the template's hold/exclude action + docket code (e.g., `hold_unsigned_order`,
    `disposition_hold`, `exclude_no_final_order`, `CONTINUED_NO_DISPOSITION`).
  - Set `financial_posting_allowed = false`; count it in the held/excluded count, not in
    financial totals.
  - Provide a `next_status_check_date` when the record gives a next setting and the
    template asks for one.
- A "release from confinement" date is memo context only; it does **not** stand in for
  the conviction/disposition date.
