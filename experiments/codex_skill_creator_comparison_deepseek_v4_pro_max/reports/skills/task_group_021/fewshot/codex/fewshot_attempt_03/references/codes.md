# Control and Decision Codes

This reference catalogs the Asteria Fleet internal control codes that appear across
audit answer contracts. Codes are assigned deterministically from data characteristics
discovered during reconciliation, not from task-specific lookup tables.

## Identity Codes (IC-)

Identity codes classify how a canonical entity was resolved from source rows.

| Code   | Meaning | Assignment Rule |
|--------|---------|-----------------|
| IC-25  | Single-source, uncontested | The entity is represented by a single source row or a small cluster with no material conflict. |
| IC-40  | Quarantined / no usable identity | The entity's rows have no usable contact channel (null/empty email and phone). |
| IC-70  | Multi-source, field-level precedence | The entity was resolved from rows across multiple source systems; canonical fields were selected by field-level precedence. |
| IC-90  | Multi-source, contested | The entity spans multiple source systems and the resolution required handling conflicting or ambiguous identifiers. |

## Field-Provenance Codes (FP-)

Field-provenance codes describe the source lineage of the canonical field values.

| Code   | Meaning | Assignment Rule |
|--------|---------|-----------------|
| FP-20  | Single-source provenance | All canonical fields derive from one source system. |
| FP-55  | Multi-source, precedence-applied | Canonical field values were drawn from multiple source systems using field-level precedence rules. |
| FP-75  | Quarantine provenance | The rows are quarantined; field provenance is from the quarantined source. |

## Outreach Codes (OR-)

Outreach codes classify the contact readiness state of an entity.

| Code   | Meaning | Assignment Rule |
|--------|---------|-----------------|
| OR-15  | Inactive exclusion | The entity's record_status is INACTIVE; no outreach is appropriate. |
| OR-35  | Channel-ready | The entity is ACTIVE, has at least one usable email or phone, and consent_status is GRANTED. |
| OR-60  | No usable contact | The entity has no usable email or phone channel (quarantined). |
| OR-80  | Not ready (consent or other blocker) | The entity is ACTIVE with a usable channel but consent is not GRANTED, or the entity is otherwise blocked from outreach. |

## Reference-Policy Codes (RB-)

Reference-policy codes classify alias-reference decisions.

| Code   | Meaning | Assignment Rule |
|--------|---------|-----------------|
| RB-17  | Conditional / limited-scope reference | The alias has a bounded valid_from/valid_to window or special conditions. |
| RB-42  | Standard reference | The alias is an active, broadly applicable reference with no special constraints. |
| RB-83  | Exception / edge-case reference | The alias covers an exception case or has an unusual mapping. |

## Source-Basis Codes (SB-)

Source-basis codes classify the evidentiary basis for retaining a transaction record.

| Code   | Meaning | Assignment Rule |
|--------|---------|-----------------|
| SB-24  | Data-quality-affected source | The transaction has a category mismatch, unrecognized description, or other quality flag but was retained from the certified snapshot. |
| SB-61  | Clean certified source | The transaction is a clean, valid record from the certified snapshot with no quality issues. |
| SB-79  | Cross-reference / secondary basis | The transaction required cross-reference data (aliases, conversions, FX) for resolution, or has an ambiguous/quarantine disposition. |

## Ledger-Disposition Codes (LD-)

Ledger-disposition codes classify how a transaction routes to financial ledgers.

| Code   | Meaning | Assignment Rule |
|--------|---------|-----------------|
| LD-14  | Exclude — unrecognized | The transaction's description matched no recognized category; exclude from accrual ledger. |
| LD-31  | Route with exception — mismatch | The transaction has a valid recognized category that differs from the expected category; route with an exception flag. |
| LD-53  | Normal route — clean | The transaction is clean and valid; route to the standard ledger. |
| LD-72  | Normal route — alternate | The transaction is clean and valid but routes to an alternate ledger account. |
| LD-88  | Exclude — ambiguous | The transaction's description matched multiple canonical categories; exclude pending resolution. |

## Maintenance-Source Codes (MS-)

Maintenance-source codes identify which operational system produced a maintenance event.

| Code   | Meaning | Assignment Rule |
|--------|---------|-----------------|
| MS-12  | Mobile Work Orders | The event originated from the Mobile Work Orders source system. |
| MS-47  | Maintenance ERP | The event originated from the Maintenance ERP source system. |
| MS-86  | Legacy Maintenance Export | The event originated from the Legacy Maintenance Export source system. |

To assign: query the event's `source_system` field by joining `v_maintenance_events` with `v_source_snapshots` on `snapshot_id`, or check which snapshot/system the event belongs to. Map **Maintenance ERP** to MS-47, **Mobile Work Orders** to MS-12, **Legacy Maintenance Export** to MS-86.

## History-Route Codes (HR-)

History-route codes classify how a maintenance event routes into fleet history.

| Code   | Meaning | Assignment Rule |
|--------|---------|-----------------|
| HR-19  | Regression-flagged route | The event is valid but is associated with an odometer regression in its asset's timeline. |
| HR-33  | Clean history route | The event is clean with no data-quality flags. |
| HR-74  | Rejected route | The event has a hard data-quality failure (missing/invalid timestamp, invalid odometer, or invalid labor) and is excluded from corrected metrics. |

## Assignment Process

For each code family, inspect the data characteristics of the entity or transaction
and assign the code whose rule best matches. When multiple rules could apply, prefer
the most specific match. The answer contract's enum values constrain which codes are
available per field — only assign codes from the allowed enum for that field.
