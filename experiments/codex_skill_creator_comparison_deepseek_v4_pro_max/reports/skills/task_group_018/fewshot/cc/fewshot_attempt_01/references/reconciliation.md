# Reconciliation Methodology

## Core principle

Reconciliation means cross-referencing every available data source for each
target case, surfacing every discrepancy as an audit finding, resolving it with
a documented source, and producing a single unified answer.

## Sources and their authority

The available sources per case form a hierarchy. When sources conflict, the
higher-ranked source controls unless there is explicit evidence that the
higher-ranked source is stale or provisional.

| Rank | Source | Authority |
|------|--------|-----------|
| 1 | Portal CMS record (cases, charges, citations) | Binding for identity, plea, disposition, sentence, fees |
| 2 | Judge pronouncement in hearing notes | Controls over portal when the portal record is pre-hearing or draft |
| 3 | Corroborating defense memo/corrob memo | Corrects administrative errors in portal or queue |
| 4 | Finance queue extract | Carries draft worksheet values; frequently stale |
| 5 | Worksheet scratchpad / intake cover sheet | Least reliable; often has unchecked sticky notes |

## Step-by-step reconciliation procedure

For each target case or citation:

### Step 1: Gather all sources

Pull every record mentioning this case from:
- All local payloads (hearing notes, audit memo, finance queue, petition, worksheet)
- Portal `/api/cases` (or `/api/citations` for traffic)
- Portal `/api/charges`
- Portal `/api/docket-entries`
- Portal `/api/financial-petitions` (if available)

### Step 2: Identity check

Compare defendant name and DOB across all sources.

- If the portal CMS record has a complete and consistent identity, use it.
- If the portal has a null DOB and local materials have one, use local materials
  and flag as `use_cms_dob` when the portal eventually catches up.
- If the portal DOB is null and local materials are also missing DOB, use
  `use_placeholder_verify` with `identity_action` set accordingly.
- If the finance queue name/DOB differs from the portal CMS record AND a defense
  memo or hearing note confirms a correction, use the portal + memo resolution.
  Flag with `issue_type: "identity"`.

Never borrow a DOB from a similarly named defendant in search results.

### Step 3: Counsel audit

Compare counsel labels across the finance queue, hearing notes, and portal.

- Finance queue labels (e.g. "PD C. Hill") are often carry-forward values.
- Hearing notes may clarify: "Lena Ortiz appeared under county appointment."
- The portal `counsel_type` field (`retained`, `public_defender`,
  `appointed_private`) is the canonical classification.
- Judge clarification on the record overrides ambiguous labels like "APD."

Classify into one of: `public_defender`, `appointed_private`, `retained`.

Flag with `issue_type: "counsel"` when:
- The finance queue says "PD" but the defense memo or hearing note clarifies
  the attorney is appointed private.
- The portal label does not match the judge's clarification.

### Step 4: Status and final-order check

Determine whether the case is disposed and whether a final signed order exists.

A case is disposed when:
- A plea was accepted in open court AND
- The judge signed a sentencing order (handed to clerk) AND
- No continuation or status hold is noted.

A case is NOT disposed when:
- The hearing notes say "the judge did not sign the order."
- The matter was continued for status.
- Only a draft worksheet exists.
- The docket note says "no sentencing order was entered in open court."

For undisposed cases:
- Set financial amounts to 0.00.
- Set disposition date to null.
- Use `hold_unsigned_order`, `exclude_pending`, or `pending_exclude` status.
- Flag with `issue_type: "status"`.

### Step 5: Charge-level reconciliation

For each count in the charge record:

- Identify the conviction count. If a charge was amended (e.g., controlled
  substance amended to misdemeanor theft), the conviction is on the amended
  count only. The original count is dismissed/amended away.
- Count dismissed_or_amended_away_counts: charges that were present but not
  convicted (amended away, dismissed).
- Plea and disposition must match the hearing notes and portal charges.
- If hearing notes say "no fine announced" but the portal charge has a
  `fine_amount`, use 0.00 from the hearing notes.

### Step 6: Departure evaluation

- If the hearing notes explicitly say the judge found "top of the range" and
  "no separate departure finding," record departure_status as `no_departure`
  or `none`.
- If a legacy worksheet or charge screen shows a departure but the judge's
  pronouncement contradicts it, trust the judge. Flag with
  `issue_type: "departure"`.
- For misdemeanors where no departure evaluation was ordered, use
  `not_evaluated_misdemeanor`.

### Step 7: Fee reconciliation

See [fee-resolution.md](fee-resolution.md) for the complete procedure.

## Audit flag decision tree

For each discrepancy found, assign the appropriate flag:

| Situation | Flag |
|---|---|
| Name/DOB mismatch between sources | `identity` |
| Counsel label wrong (PD vs appointed private) | `counsel` |
| Case is continued, no final order | `status` |
| Stale or wrong fee amount | `fee_schedule` |
| Departure notation contradicted by judge | `departure` |
| Charge amended away from original (e.g. CS -> theft) | `amended_non_lab_conviction` |
| Lab fee omitted on controlled-substance case | `lab_fee_worksheet_omitted` |
| DOB blank in all sources | `dob_missing_verify` |
| "APD" on calendar but it's appointed private | `apd_label_not_public_defender` |
| Continued, no final order signed | `no_final_order_pending` |

## Resolution source selection

For each audit finding, select the resolution_source that describes how the
conflict was resolved:

- `use_cms` — the portal CMS record controls
- `use_hearing_notes` — the judge's pronouncement controls
- `use_corrob_memo` — the defense cover memo / corrob memo controls
- `use_fee_schedule` — the active portal fee schedule controls
- `hold_unsigned_order` — the matter is held pending a signed order
- `use_cms_identity` — portal identity data controls
- `verify_before_entry` — DOB or other field must be verified from case file
- `exclude_pending` — the case must not enter the register
