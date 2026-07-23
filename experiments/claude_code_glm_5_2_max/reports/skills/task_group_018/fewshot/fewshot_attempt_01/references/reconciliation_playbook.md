# Reconciliation Playbook

Decision rules for each conflict type encountered in a closeout batch. For every conflict: identify the *conflicted value* (what the local payload says), determine the *corrected value* (what the authority says), pick the *resolution source* token from the template's enum, and emit it in the audit section where the schema provides one. When the schema has no audit section, still apply the correction — the corrected value flows into the disposition/fee/form sections; do not silently carry the stale value.

## 1. Identity / DOB conflicts

**Trigger:** local worksheet/queue DOB or name spelling differs from the case file, or DOB is blank.

- Portal case record DOB is authoritative. Use it (`use_cms` / `use_cms_identity` / `use_cms_dob`).
- If the portal shows a corrected spelling (e.g. "Simmons" not "Simons") and a one-day DOB difference, treat the whole identity as corrected from CMS.
- If DOB is genuinely absent everywhere and required for entry → do **not** invent or borrow from a similarly-named party in search results. Use the placeholder string and a verify action (`use_placeholder_verify` / `verify_before_entry`) with a `dob_missing_verify` / `missing_identifier` flag. Financial posting may still proceed if a signed order exists, but the identity field stays a placeholder.
- Borrowing a DOB across parties is the single most common silent error — never do it.

`issue_type`/flag token to emit: `identity` / `dob_missing_verify`.

## 2. Counsel classification conflicts

**Trigger:** calendar/queue label ("APD", "PD", "RET") disagrees with the defense cover memo, appointed-counsel order, or the judge's on-record statement.

- Calendar abbreviations are unreliable. "APD" can mean **appointed private** (county-paid) — *not* the public defender office. `attorney_label_raw` on the portal is the raw label; `counsel_type` is the normalized value but may still reflect the calendar label.
- The **corroborating record** (defense memo, appointed-counsel order, judge's on-record clarification) controls. Correct to `appointed_private`, `public_defender`, or `retained` accordingly (`use_corrob_memo`).
- Downstream consequence: an **appointed-private** or **retained** defendant is **not** public-defender-user-fee eligible. If the queue added a PD user fee to an appointed-private case, drop the user fee (and, if the schema tracks it, note the exclusion). Conversely, a true PD case where the bench did not waive the user fee keeps the fee.

`issue_type`/flag token: `counsel` / `apd_label_not_public_defender`.

## 3. Charge / amendment conflicts

**Trigger:** the filed charge differs from the convicted charge, or a worksheet shows a count that was amended away.

- Hearing notes (bench record) authoritative for the **conviction count**. An amendment to a lesser/non-lab count replaces the filed count: the conviction offense is the amended one; the original count is dismissed/amended away.
- For disposition counts: `convicted_counts` = counts adjudicated guilty; `dismissed_or_amended_away_counts` = counts dismissed or amended away from the filed set.
- A controlled-substance filed count amended to misdemeanor theft means **no drug/crime-lab assessment** applies (assessment keys on the CS conviction). The reverse: a CS *conviction* with a lab note carries the lab fee even if the worksheet omitted it.

`issue_type`/flag token: `amended_non_lab_conviction` / `lab_fee_worksheet_omitted` (per schema enum).

## 4. Departure conflicts

**Trigger:** a draft/legacy worksheet labels the sentence a "dispositional/durational departure," but the record says otherwise.

- The judge's on-record statement controls. "Top of the range, no departure finding" → `no_departure` / `none`. A draft worksheet departure label is discarded (`use_hearing_notes`).
- For misdemeanors where departure isn't evaluated, use the template's misdemeanor token (`not_evaluated_misdemeanor`) rather than forcing a felony departure taxonomy.
- If the matter is held pending (no order), departure is `not_entered_pending` / `not_applicable`.

## 5. Fee-schedule conflicts

**Trigger:** local finance extract/worksheet uses an archived, prior-year, or stale amount; omits a mandatory fee; or adds an unsupported fee.

- **Current schedule effective on the disposition date** is authoritative (`use_fee_schedule`). Replace stale with current. Add omitted mandatory fees (e.g. PD user fee the bench did not waive; drug/crime-lab assessment on a CS conviction).
- A prior-year disposition uses that year's effective row; a current-year disposition rejects prior-year amounts. Match `jurisdiction_code` and effective window exactly.
- Unsupported add-on fees (account-management, collection, late, returned-check, DMV, restitution-without-order, copy, certification, court-appointed-attorney, court-reporter, traffic-school) → exclude with the matching reason code; carry `0.00`. The policy `account_fee == 0` means account-management is `excluded_by_policy` / `not_current_policy`.
- If a worksheet drafts a fine on a matter with no signed order, the fine is not posted at all (see §6), not merely excluded as a fee.

`issue_type`/flag token: `fee_schedule`.

## 6. Status / finality conflicts

**Trigger:** draft worksheet/queue marks a matter "disposed" and lists fines, but no sentencing/disposition order was signed in open court.

- **Signed final order controls finality.** No signed order → the matter is `deferred` / `continued` / `pending`, never `disposed`. (`hold_unsigned_order` / `verify_before_entry` / `exclude_pending`, depending on whether the schema wants a hold or an outright exclusion.)
- Downstream: **no financial register entry** for a held/excluded matter. Fee items empty, totals `0.00`, docket entry type = `disposition_hold` / `CONTINUED_NO_DISPOSITION`, `fee_status` = hold/`do_not_post_pending`, register action = exclude. Plea not accepted → `not_entered`; sentence not pronounced → imposed/suspended/probation all 0.
- A matter that is genuinely disposed but the worksheet date/status is wrong → correct the date/status from the record and post normally.

`issue_type`/flag token: `status` / `no_final_order_pending`.

## Cross-cutting: where each correction lands

- Audit section (if schema has one): one finding per conflict, with `conflicted_value`, `corrected_value`, `resolution_source`.
- Case audit / disposition section: corrected identity, counsel, status, plea, counts, departure, dates.
- Fee section: only supported, current, mandatory amounts; everything else excluded.
- Placeholder section: any required field still missing after reconciliation.
- Exclusion section: held/excluded matters and the reason they stay out of the register.

If a conflict cannot be resolved because the authority is itself ambiguous, prefer the verify/exclude token over a guess — emitting `verify_before_entry` is correct; emitting a fabricated value is not.
