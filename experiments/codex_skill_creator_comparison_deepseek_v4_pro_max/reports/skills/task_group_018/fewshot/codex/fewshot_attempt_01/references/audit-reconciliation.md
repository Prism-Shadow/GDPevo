# Audit Reconciliation Patterns

## Reconciliation Priority Chain

When sources conflict, resolve using this priority order. Each step overrides the ones below it:

1. **Hearing notes** — judge's actual words from the bench
2. **Corroborating memos** — clerk or law-clerk research findings backed by paper-packet evidence
3. **Portal / CMS** — live case management system records
4. **Current fee schedule** — portal fee schedule for the jurisdiction

Lower-priority sources are stale until proven current.

## Conflict Types and Resolution Rules

### Identity Conflicts

Occurs when name spelling or DOB differs across sources (finance queue, hearing notes, portal). Resolution path:

1. If corroborating memo explicitly corrects identity with paper-packet evidence, use the memo's correction and set `resolution_source` to `use_corrob_memo`.
2. If no memo correction exists but hearing notes contain a bench-correction or question mark, use the hearing-notes version and set `resolution_source` to `use_hearing_notes`.
3. If both memo and hearing notes exist without correction, use the portal/CMS identity and set `resolution_source` to `use_cms`.
4. If DOB is genuinely blank in all materials, use the placeholder `TBD from case file` and set `resolution_source` to `verify_before_entry`. Never borrow DOB from a similarly named defendant.

### Counsel Conflicts

Occurs when the counsel label (PD, APD, RET) does not match the actual representation type. Common scenarios:

- **"APD" on calendar but hearing or memo states appointed private counsel**: The defendant pays nothing (county pays) but the attorney is not a public defender. Do not apply the public defender user fee. Use `appointed_private` classification. Resolution: `use_corrob_memo` or `use_hearing_notes` depending on which source provides the definitive correction.
- **"PD" label on finance queue but defense cover memo says appointed private**: Follow the corroborating memo. Use `appointed_private`. Resolution: `use_corrob_memo`.
- **Retained counsel confirmed**: No PD user fee applies. Resolution: `use_cms` or `use_hearing_notes`.

Public defender user fee only applies when counsel classification is `public_defender`.

### Fee Schedule Conflicts

Occurs when stale amounts appear in finance queues, old worksheets, or intake cover sheets. Resolution:

1. Query the current fee schedule from the portal for the jurisdiction.
2. Apply current amounts. Replace stale amounts.
3. Note the conflict as `fee_schedule` type with `resolution_source` = `use_fee_schedule`.

Common stale values: outdated drug assessment amounts, old statutory fine tables (e.g., 2022 SOF table vs. 2024 schedule), archived cost amounts.

### Status Conflicts

Occurs when a finance queue or worksheet marks a case as "disposed" but the hearing notes show no final order was signed. Resolution:

- If no sentencing order was signed in open court, the case is not disposed. Use `deferred` or `pending` status.
- Set `closeout_action` to `hold_unsigned_order`.
- Set `resolution_source` to `hold_unsigned_order`.
- Set all financial amounts to 0.00.

### Departure Conflicts

Occurs when legacy or draft charge screens carry a departure label that the judge did not pronounce. Resolution:

1. If the judge explicitly stated "no departure" or "top of range," use `no_departure`.
2. If the judge made no departure finding and the offense is a misdemeanor, use `not_evaluated_misdemeanor` or `none`.
3. If no plea was accepted (continued case), use `not_entered_pending`.
4. Set `resolution_source` to `use_hearing_notes` when the judge's bench statement controls.

## Resolution Source Enum Values

| Value | When to Use |
|---|---|
| `use_cms` | Portal identity records are authoritative |
| `use_hearing_notes` | Judge's bench statement controls the conflict |
| `use_corrob_memo` | Clerk memo backed by paper-packet evidence controls |
| `use_fee_schedule` | Current portal fee schedule controls the amount |
| `hold_unsigned_order` | No signed order exists; hold entry |
| `verify_before_entry` | Material is genuinely missing; DOB or other field must be verified from case file |

## Counsel Classification Rules

| Label in Source | Actual Classification | PD User Fee? |
|---|---|---|
| "PD" confirmed by hearing | `public_defender` | Yes |
| "APD" with memo stating appointed private | `appointed_private` | No |
| "RET" confirmed | `retained` | No |
| "APD" without clarification | Treat as ambiguous; prefer hearing-note evidence |

## Identity Correction Patterns

| Conflict | Resolution |
|---|---|
| Name misspelled in finance queue | Use portal name; or hearing-note correction if available |
| DOB one day off in queue vs. memo | Use corroborating memo DOB |
| DOB blank on bench card | Use `TBD from case file`; `identity_action` = `use_placeholder_verify` |
| Worksheet DOB blank with note "do not borrow" | Use `TBD from case file`; never borrow from similar names |
