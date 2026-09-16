# Control Code Families

Every Asteria data-quality task uses compact opaque control codes selected
from the fixed families below. The answer template declares the applicable
families via its schema `enum` constraints. Select one code per decision
entity based on the data characteristics of the relevant rows.

## Identity Codes (IC-*)

| Code | Typical meaning | When to assign |
|---|---|---|
| IC-25 | Single-source, clean identity | Entity resolved from exactly one source system with no cross-source conflict and no quarantine. |
| IC-40 | Quarantined identity | Entity placed in quarantine (no usable contact channel). |
| IC-70 | Multi-source merge, field-precedence resolved | Entity formed by merging rows from multiple source systems using field-level precedence rules; all conflicts resolved. |
| IC-90 | Multi-source, contested or edge-case | Entity with cross-source conflict that could not be fully resolved, or watchlist-contested identifiers. |

## Outreach Codes (OR-*)

| Code | Typical meaning | When to assign |
|---|---|---|
| OR-15 | Inactive exclusion | Inactive record excluded from readiness population. |
| OR-35 | Readiness-eligible, consent granted | Active entity with at least one usable channel and granted consent. |
| OR-60 | Quarantine, no usable channel | Entity with no usable email or phone. |
| OR-80 | No consent or blocked | Active entity with a usable channel but non-granted consent, or a blocked/contested outreach situation. |

## Field Provenance Codes (FP-*)

| Code | Typical meaning | When to assign |
|---|---|---|
| FP-20 | Consistent single-source provenance | All rows in the cluster come from the same source system. |
| FP-55 | Multi-source, field-level precedence applied | Cluster spans multiple source systems; canonical values derived by field-level precedence. |
| FP-75 | Unresolvable provenance or quarantine | Quarantined entity, or provenance cannot be confidently determined. |

## Reference Policy Codes (RB-*)

Used in fuel/freight `reference_decisions` and `reference_rows` panels.

| Code | Typical meaning | When to assign |
|---|---|---|
| RB-17 | Provisional alias | Alias mappings from provisional/reconciled data that have not been finalized. |
| RB-42 | Certified stable alias | Alias mappings validated against the certified snapshot. |
| RB-83 | Unrecognized or exception alias | Alias with no recognized mapping, or an exception case. |

## Source Basis Codes (SB-*)

Used in fuel/freight `source_basis` and `source_retention` panels.

| Code | Typical meaning | When to assign |
|---|---|---|
| SB-24 | Certified-only occurrence | The entity appears only in the certified snapshot. |
| SB-61 | Certified, retained over provisional | The entity appears in both snapshots; certified retained. |
| SB-79 | Provisional-only, unique | The entity appears only in the provisional snapshot and has no certified counterpart. |

## Ledger Disposition Codes (LD-*)

Used in fuel/freight `ledger_disposition` and `ledger_routing` panels.

| Code | Typical meaning | When to assign |
|---|---|---|
| LD-14 | Quarantine, unrecognized category | Charge/transaction quarantined because description maps to zero recognized categories. |
| LD-31 | Valid, category/class mismatch | Clean record with a recognized category, but expected differs from actual. |
| LD-53 | Quarantine, invalid measure | Quarantined for invalid quantity, weight, or distance. |
| LD-72 | Valid, clean match | Clean record with expected matching recognized category. |
| LD-88 | Quarantine, ambiguous category | Charge/transaction quarantined because description maps to multiple recognized categories. |

## Maintenance Source Codes (MS-*)

| Code | Typical meaning | When to assign |
|---|---|---|
| MS-12 | Certified snapshot, clean | Event appears in certified snapshot with no quality issues. |
| MS-47 | Certified snapshot, invalid field | Event in certified snapshot with a quality issue (missing/invalid timestamp, odometer, labor). |
| MS-86 | Provisional snapshot | Event appears only in the provisional snapshot. |

## History Route Codes (HR-*)

| Code | Typical meaning | When to assign |
|---|---|---|
| HR-19 | Primary route disposition | Event routed through primary history path. |
| HR-33 | Secondary route disposition | Event routed through secondary or alternate history path. |
| HR-74 | Exception route disposition | Event routed through exception or corrected-metrics history path. |
