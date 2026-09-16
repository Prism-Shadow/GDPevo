# Asteria Decision Codes

Use these mappings as reusable semantics for Asteria compact code panels. Verify against the scoped row evidence before assigning a code.

## Contact Identity Codes

- `IC-25`: single-source or single-entity identity with no duplicate/contested merge.
- `IC-70`: confirmed duplicate or multi-row identity cluster auto-merged into one canonical person/entity.
- `IC-90`: contested identifier or identity evidence; do not auto-merge.
- `IC-40`: quarantined identity/contact result, usually no usable contact channel.

## Contact Outreach Codes

- `OR-35`: outreach ready or dispatchable: active, usable channel, and granted consent.
- `OR-80`: active with a usable channel but consent is not granted; keep out of ready/dispatchable counts.
- `OR-60`: no usable email or phone; quarantine/no-contact outcome.
- `OR-15`: inactive exclusion.

## Contact Field-Provenance Codes

- `FP-20`: no cross-source field precedence was needed, or the row remains single-source/non-merged.
- `FP-55`: field-level source precedence selected canonical values across a merged cluster.
- `FP-75`: no usable canonical contact field set; quarantine provenance.

## Reference-Basis Codes

- `RB-42`: active reference alias maps to exactly one canonical category/class at the business date.
- `RB-17`: alias/reference is not recognized as an active unique mapping for the business date.
- `RB-83`: alias/reference is ambiguous, with multiple applicable canonical mappings.

## Source-Basis Codes

- `SB-24`: retained single-source business record without cross-snapshot overwrite.
- `SB-61`: retained authoritative occurrence from a duplicate/cross-snapshot logical record.
- `SB-79`: retained non-ledger/feed occurrence or source evidence that is not the authoritative duplicate-retention path.

## Ledger-Disposition Codes

- `LD-72`: valid clean record that can enter the ledger/accrual without category/class exception.
- `LD-31`: valid expected-versus-recognized category/class mismatch; include in normalized totals but route as a mismatch.
- `LD-14`: unresolved zero-match alias/category/class quarantine.
- `LD-88`: ambiguous alias/category/class quarantine.
- `LD-53`: invalid physical measure quarantine, such as invalid quantity, weight, distance, or equivalent numeric basis.

## Maintenance Codes

Maintenance source codes identify the source system of the retained event. Derive the source-system-to-code mapping from the public row evidence in the current collection rather than from event ID shape.

History route codes:

- `HR-33`: accepted into corrected history.
- `HR-19`: sequence-only odometer regression route.
- `HR-74`: rejected event route for missing/unparsable time, invalid odometer, or invalid labor.
