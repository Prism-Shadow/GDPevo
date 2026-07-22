# Asteria Internal Control Code Reference

This reference describes the code families that appear across Asteria Fleet Data Quality Hub tasks. Codes are always drawn from the `enum` lists in the answer template — this document explains what each family represents and how to infer the correct code from evidence.

## Identity Codes (IC-*)

Reflect confidence in identity resolution across sources.

| Condition | Typical Code |
|---|---|
| All sources agree on identity; no conflicts in any field | Higher-confidence code |
| Multiple sources agree but minor field-level disagreements exist | Mid-tier code |
| Single source only; no corroboration | Lower-mid code |
| Sources conflict on key identity fields (name, email); contested | Lowest-confidence code |

## Outreach Codes (OR-*)

Reflect contact-channel readiness for outreach.

| Condition | Typical Code |
|---|---|
| Both valid email AND valid phone; consent granted | Highest-readiness code |
| Email only usable; phone missing or invalid | Email-only tier |
| Phone only usable; email missing or invalid | Phone-only tier |
| Neither email nor phone usable; or consent denied/revoked | Not-ready tier |

## Field Provenance Codes (FP-*)

Reflect which source system(s) supplied canonical field values.

| Condition | Typical Code |
|---|---|
| All canonical fields sourced from a single system | Single-source code |
| Canonical fields drawn from multiple systems with field-level precedence | Multi-source merged code |
| Majority of fields from one system; one or two from another | Hybrid code |

## Reference Policy Codes (RB-*)

Reflect how a reference alias resolved against the canonical reference table.

| Condition | Code |
|---|---|
| Alias matched exactly one recognized canonical entry | Unambiguous match |
| Alias matched more than one canonical entry | Ambiguous match |
| Alias matched zero canonical entries | Unrecognized |

## Source Basis Codes (SB-*)

Reflect the snapshot provenance of a retained transaction or charge.

| Condition | Code |
|---|---|
| Entity appears in exactly one snapshot | Single-source |
| Entity appears in multiple snapshots; retained from the authoritative one | Multi-source authoritative-retained |
| Entity appears in multiple snapshots with field-level conflicts | Multi-source with conflicts |

## Ledger Disposition Codes (LD-*)

Reflect the accounting treatment of a charge.

| Condition | Code |
|---|---|
| Valid charge, no mismatch, not quarantined — clean accrual | Clean routing |
| Valid charge with a category/class mismatch — accrual with note | Mismatch routing |
| Quarantined charge — excluded from accrual | Quarantine routing |
| Other disposition variations | Per evidence |

## Maintenance Source Codes (MS-*)

Reflect the source system that originated a maintenance event.

| Condition | Code |
|---|---|
| Event from the primary fleet management system | Primary source |
| Event from a secondary/partner system | Secondary source |
| Event from an ingested third-party log | External source |

## History Route Codes (HR-*)

Reflect whether a maintenance event enters the clean reliability history.

| Condition | Code |
|---|---|
| Event is valid, non-duplicate, no data-quality issues | Clean history |
| Event has minor data-quality flags but is retained | Flagged history |
| Event is excluded from history (invalid, duplicate, regression) | Excluded |

## Inference Principle

For each decision target, examine the raw evidence rows. Determine which conditions are met. Map the condition pattern to a code using the enum values in the answer template. When a condition fits multiple codes, prefer the more specific match. When genuinely ambiguous, lean toward the code representing lower confidence or higher scrutiny.
