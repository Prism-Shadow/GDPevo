# Asteria Codebook

Use this reference to assign opaque Asteria codes from current task evidence. These are reusable meanings inferred from the staged examples; do not copy any prior task IDs, counts, rankings, or final answer records.

## Contact Control Codes

Identity:

- `IC-25`: Single-source or otherwise uncontested identity retained without an automerge conflict.
- `IC-40`: No usable-contact or quarantined identity result.
- `IC-70`: Same-person duplicate cluster resolved by automerge and field-level precedence.
- `IC-90`: Contested identifier or evidence that must not be automerged.

Outreach:

- `OR-35`: Outreach/dispatch ready: active, usable channel, and granted consent.
- `OR-60`: Blocked because no usable outreach channel remains.
- `OR-80`: Blocked because consent is not granted despite otherwise usable contact evidence.
- `OR-15`: Inactive exclusion.

Field provenance:

- `FP-20`: Single-source or direct authoritative field provenance.
- `FP-55`: Field-level precedence selected canonical values across multiple sources.
- `FP-75`: Quarantine/no usable field provenance.

## Reference And Ledger Codes

Reference rows:

- `RB-42`: Active reference row resolves to exactly one canonical value.
- `RB-17`: No active applicable reference match.
- `RB-83`: Ambiguous reference evidence, usually multiple active canonical matches.

Source basis:

- `SB-61`: Logical row had overlapping raw occurrences and the authoritative/certified snapshot occurrence was retained.
- `SB-24`: Non-overlap retained from the primary ledger/system-of-record feed.
- `SB-79`: Non-overlap retained from the secondary operational/import feed.

Ledger disposition:

- `LD-72`: Valid recognized class/category matching expected classification; include in normal ledger totals.
- `LD-31`: Valid recognized class/category mismatch; include in totals and exception exposure.
- `LD-14`: Unrecognized class/category alias.
- `LD-88`: Ambiguous class/category alias.
- `LD-53`: Invalid physical or quantity measure, or other quantitative defect that prevents ledger entry.

## Maintenance Codes

Maintenance source:

- `MS-47`: Maintenance ERP or authoritative retained maintenance source.
- `MS-12`: Mobile work-order source.
- `MS-86`: Legacy/export maintenance source.

History route:

- `HR-33`: Accepted into corrected reliable history.
- `HR-74`: Rejected for a hard validity issue such as missing/unparseable time, invalid odometer, or invalid labor.
- `HR-19`: Sequence-only odometer regression route; report as a regression rather than a hard rejection unless the contract says otherwise.

## Statuses

Always apply the current `case_scope.json` status thresholds, gates, and action maps. Typical patterns:

- Hard regressions, invalid ledger blockers, or unresolved accrual conditions produce `HOLD` with remediation routing.
- Quarantine rates within an exception threshold can produce `PASS_WITH_EXCEPTIONS`.
- No exceptions under the stated gate produces `PASS`.
