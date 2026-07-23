# Conflict Resolution Ladder

Local closeout payloads are built to disagree. Pick the source for each field by this priority, then tag the choice with the resolution-source enum the template provides.

## Priority order (highest → lowest)

1. **Signed / on-record bench pronouncement** (`hearing_notes`, `hearing_closeout_note`, `sentencing_probation_notes` sentence/charge notes). The judge's stated finding on posture, disposition, departure, and sentence terms wins over every worksheet. "Judge stated this is the top of the range… no separate departure finding" overrides a draft "dispositional departure" label.
2. **Portal / CMS record** (`/api/cases`, `/api/search`, `/api/charges`, `/api/docket-entries`). Authority of record for: defendant identity (full name + DOB), resolved counsel type vs. raw counsel label, case status, disposition date, charge as filed/convicted, and docket text. Where a bench note is ambiguous (a "?" on the bench sheet), the CMS record resolves it.
3. **Fee schedule / payment policy / form metadata** (`/api/fee-schedules`, `/api/payment-policies`, `/api/forms`, `/api/financial-petitions`). The only acceptable source for fee *amounts*, policy bands, account-fee treatment, payment application order, and form ids/labels.
4. **Corroborating memo** (`audit_memo`, `clerk_review_notes`, `supervisor_note`, `review_note`). Tells you *which* local value is wrong and the reason — use it to pick between two local values, not to invent a new one.
5. **Queue / worksheet / intake / scratchpad / counter note**. Lowest authority. These are the starting numbers you reconcile *from*. They are frequently: stale ("archived amount," end-dated schedule row), draft ("draft guilty plea," "draft only"), carry-forward ("from morning docket sheet," "from older import"), or ambiguous ("PD C. Hill?"). Never post one unchanged without portal confirmation.

## Decision flags (map to the template's resolution-source enum)

- Confirmed corrected against CMS → `use_cms` / `use_cms_identity`
- Confirmed against bench pronouncement → `use_hearing_notes`
- Picked per audit/supervisor memo → `use_corrob_memo`
- Amount confirmed against current fee schedule → `use_fee_schedule`
- Field genuinely missing, must be verified before entry → `verify_before_entry` / `use_placeholder_verify`
- Matter unsigned/continued, kept out of register → `hold_unsigned_order` / `exclude_pending`

## Per-payload trust level

| Payload type | Trust | Use it for |
|---|---|---|
| hearing notes / closeout note / sentencing-probation notes | High (posture, sentence, on-record findings) | disposition, plea, sentence terms, departure, plan approval, license/probation notes |
| audit memo / clerk review / supervisor note / review note | High (directional) | which conflicting local value is wrong and why |
| CMS/portal record | High (system of record) | identity, counsel type, status, dates, charges, docket text |
| fee schedule / payment policy / form metadata (portal) | High (amounts/policy) | fee amounts, policy bands, form ids |
| intake facts / sentencing intake | Medium | conviction/sentence posture when no hearing note contradicts |
| payment petition / budget / petition summaries | Medium | requested terms + budget; court-approved terms override requested |
| finance queue extract / worksheet CSV / counter note / scratchpad | Low | starting numbers to reconcile; flag every line for verification |
| local form excerpt / form field excerpt | Medium (labels/structure) | required labels, account-reference rule, placeholder rule, form-family mapping |

## Hard prohibitions (recuring across exemplars)

- Do not borrow a DOB or identity field from a similarly-named defendant in search results.
- Do not post a fee the current schedule or a triggering event does not support (account-mgmt, collection, late, DMV, restitution, copy, cert, returned-check, traffic-school, court-reporter, court-appointed-attorney).
- Do not post a draft or unsigned disposition's fees — hold the financial entry.
- Do not let an old/superseded form footer or service charge become current policy.
- Do not invent any identifier, address, phone, license number, or contact — use the mandated placeholder.
