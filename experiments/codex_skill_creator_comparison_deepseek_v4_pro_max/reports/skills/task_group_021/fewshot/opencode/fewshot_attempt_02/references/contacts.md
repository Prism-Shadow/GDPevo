# Contacts reference

## Relevant logical view

`v_contacts` — fields: `collection_id`, `row_id`, `snapshot_id`, `source_system`, `source_record_id`, `person_or_org_name`, `email`, `phone`, `city`, `region`, `country`, `consent_status`, `record_status`, `verified_flag`, `business_updated_at`, `ingested_at`, `master_hint`.

## Entity resolution (merging duplicates)

Contact rows from different source systems that represent the same person are identified by matching on email (lowercase normalized) or phone (digits-only). When two rows share the same normalized email or phone, they are the same canonical person and belong to the same cluster.

### Field-level precedence for canonical values

When a cluster has rows from multiple systems, pick the canonical value for each field using this precedence order:

| Field | Precedence (highest first) |
|---|---|
| `person_or_org_name` | HR Directory, then Identity Registry, then Dispatch, then Compliance Master, then Partner Portal, then CRM |
| `email` | Identity Registry, then Compliance Master, then Dispatch, then HR Directory, then Partner Portal, then CRM |
| `phone` | Identity Registry, then Compliance Master, then Dispatch, then HR Directory, then Partner Portal, then CRM |
| `city` | Compliance Master, then HR Directory, then Identity Registry, then Dispatch, then Partner Portal, then CRM |
| `region` (depot) | HR Directory, then Dispatch, then Identity Registry, then Compliance Master, then Partner Portal, then CRM |
| `consent_status` | Identity Registry, then Compliance Master, then Dispatch, then HR Directory, then Partner Portal, then CRM |
| `record_status` | Most common value across the cluster; if tie, prefer ACTIVE |

### Survivor row selection

The survivor row is the cluster member from the source system that contributed the most canonical field values. In case of a tie, prefer the row with `verified_flag = 1`, then the row from the highest-precedence source system for the name field, then the row with the most recent `business_updated_at`.

### Resolution outcomes

- `FIELD_LEVEL_PRECEDENCE_APPLIED` — cluster merged from multiple sources with different contributing systems for different fields
- `SINGLE_SOURCE` — all rows in the cluster come from the same source system
- `CONTESTED_NO_AUTOMERGE` — watchlist identifier case that remains unresolved because evidence rows lack matching contact signals
- `NO_USABLE_CONTACT` — all rows in the cluster have no usable email or phone

### Contested identifier watchlist

When an identifier case is in the watchlist and its evidence rows do not share a common email or phone, the case is reported as contested. When evidence rows do share a contact channel, they are merged normally and the case is not contested.

## Quarantine (contacts)

A row is quarantined when it has no usable contact channel:
- `email` is null, empty, or the literal string "null"
- AND `phone` is null, empty, or the literal string "null"

Quarantined rows are not eligible for readiness.

## Readiness

A canonical entity (person) is readiness-eligible only when its canonical `record_status` is ACTIVE and it retains at least one of:
- A non-empty canonical email
- A non-empty canonical phone (digits only)

A channel is "ready" only when `consent_status` is GRANTED. Readiness partitions:
- `both` — eligible, has usable email AND phone, consent GRANTED
- `email_only` — eligible, has usable email but no usable phone, consent GRANTED
- `phone_only` — eligible, has usable phone but no usable email, consent GRANTED
- `not_ready` — eligible but consent is not GRANTED, or has no usable channel

Readiness counts must be mutually exclusive across all readiness-eligible canonical entities.

## Control code assignment for contacts

See [control-codes.md](control-codes.md) for the code tables. Apply rules from the table based on:
- **IC codes**: whether the cluster is single-source or multi-source, and the composition of source systems
- **OR codes**: the outreach readiness partition and inactive status
- **FP codes**: which source system contributed the majority of canonical field values
