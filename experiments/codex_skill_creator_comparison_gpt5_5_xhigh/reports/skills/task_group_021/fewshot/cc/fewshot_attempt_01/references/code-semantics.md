# Asteria Compact Code Semantics

Use these reusable meanings when the answer contract lists opaque code values but not their expansions. Always confirm against the current task's records, schema, and allowed enum values.

## Contact Control Codes

Identity codes:

| Code | Use for |
| --- | --- |
| `IC-25` | Clean single identity, no contested merge, or identity evidence that remains independently resolved. |
| `IC-40` | Identity record excluded or quarantined because the entity cannot be made usable under the contact rules. |
| `IC-70` | Multiple public rows resolved as the same person/entity through automatic merge or field-level precedence. |
| `IC-90` | Contested identifier cluster, conflicting identity evidence, or no automatic merge. |

Outreach codes:

| Code | Use for |
| --- | --- |
| `OR-35` | Outreach-ready: active, at least one usable channel, and consent granted for the relevant channel. |
| `OR-80` | Blocked by consent or channel readiness policy despite identity being otherwise usable. Pending, denied, and unknown consent belong here unless the current task overrides that rule. |
| `OR-60` | No usable contact channel or quarantined for contact usability. |
| `OR-15` | Inactive record excluded from outreach or dispatch readiness. |

Field-provenance codes:

| Code | Use for |
| --- | --- |
| `FP-20` | Single-source or direct authoritative field provenance without cross-source field precedence. |
| `FP-55` | Canonical fields assembled by cross-source field-level precedence across merged duplicate rows. |
| `FP-75` | Field provenance is unusable, quarantined, or tied to a no-usable-contact exclusion. |

## Reference And Ledger Codes

Reference basis codes for alias or reference rows:

| Code | Use for |
| --- | --- |
| `RB-42` | Reference row maps unambiguously to exactly one recognized category or service class. |
| `RB-17` | Reference row has no recognized category or service-class match. |
| `RB-83` | Reference row is ambiguous and maps to more than one recognized category or service class. |

Source-basis or source-retention codes:

| Code | Use for |
| --- | --- |
| `SB-24` | Single retained source occurrence or normal retained basis with no cross-snapshot conflict. |
| `SB-61` | Retained from the authoritative or certified snapshot when duplicate source occurrences overlap. |
| `SB-79` | Retained from a non-authoritative, provisional, fallback, or alternate source basis as shown by snapshot metadata. |

Ledger-disposition or ledger-routing codes:

| Code | Use for |
| --- | --- |
| `LD-72` | Valid, recognized, expected category/class matches actual category/class and can enter normalized totals normally. |
| `LD-31` | Valid, recognized category/class differs from the expected category/class; include in totals and mismatch reporting. |
| `LD-14` | Unrecognized alias/category/class with zero usable matches; quarantine or exclude from accrual as directed. |
| `LD-88` | Ambiguous alias/category/class with more than one usable match; quarantine or exclude from accrual as directed. |
| `LD-53` | Invalid physical measure, quantity, amount, distance, weight, or other non-category data-quality blocker. |

## Maintenance Codes

Maintenance-source codes:

| Code | Use for |
| --- | --- |
| `MS-12` | Normal single retained maintenance source basis. |
| `MS-47` | Retained from authoritative/certified source when overlapping duplicate event records exist. |
| `MS-86` | Provisional, fallback, alternate, or non-authoritative maintenance source basis. |

History-route codes:

| Code | Use for |
| --- | --- |
| `HR-33` | Accepted into reconstructed maintenance history. |
| `HR-74` | Rejected for structural invalidity such as missing or invalid timestamp, invalid odometer, or invalid labor. |
| `HR-19` | Sequence-only odometer regression in an otherwise structurally parseable event. |

## Status And Routing

Use the task's `case_scope.json` thresholds and status/action map when present. Common mappings are:

| Status | Action/routing |
| --- | --- |
| `PASS` | `RELEASE` |
| `PASS_WITH_EXCEPTIONS` | `REVIEW_EXCEPTIONS` |
| `HOLD` | `BLOCK_AND_REMEDIATE` |
