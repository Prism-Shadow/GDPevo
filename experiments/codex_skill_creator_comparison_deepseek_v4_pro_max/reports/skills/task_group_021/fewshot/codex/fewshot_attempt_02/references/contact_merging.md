# Contact Merging Rules

## Overview

Contact-merging tasks reconcile rows from multiple source systems (HR Directory, Dispatch, Identity Registry for field-service rosters; CRM, Compliance Master, Partner Portal for partner onboarding) into canonical people. There is no explicit logical-record ID shared across systems—matching is done by identity similarity.

## Field-Level Precedence

When multiple source systems contribute different values for the same canonical person, select the value from the highest-precedence system per field. Tables show precedence order (highest first).

### Partner Onboarding Domain

| Field | Precedence |
|-------|-----------|
| email, phone | Compliance Master > CRM > Partner Portal |
| city | Compliance Master > CRM > Partner Portal |
| name | Compliance Master > CRM > Partner Portal |

The survivor row (the row used as the canonical record's anchor) is the highest-row-ID row from the highest-precedence source system that has a usable contact channel.

### Field-Service Roster Domain

| Field | Precedence |
|-------|-----------|
| name | HR Directory > Dispatch > Identity Registry |
| email, phone | Identity Registry > Dispatch > HR Directory |
| city | HR Directory > Dispatch > Identity Registry |
| depot / region | HR Directory > Dispatch > Identity Registry |
| consent | Identity Registry > Dispatch > HR Directory |
| record_status | HR Directory > Dispatch > Identity Registry |

The master ID (the row selected as the canonical record's anchor) is the highest-row-ID row from the highest-precedence source system among the merged members. Typically this is the Identity Registry row when one exists and provides email/phone, otherwise the Dispatch or HR Directory row.

## Merging Procedure

1. Start with all rows from all source systems in the collection.
2. Match rows into clusters by identity signals:
   - Exact email match (case-insensitive, normalized)
   - Exact phone match (digits only)
   - Name similarity (same canonical name after Unicode NFKC normalization and trimming)
   - Transitive closure: if A matches B and B matches C, all three are the same person
3. Within each cluster, apply field-level precedence to pick canonical values.
4. Assign resolution outcomes:
   - `FIELD_LEVEL_PRECEDENCE_APPLIED`: multi-source merge with field-level selection
   - `SINGLE_SOURCE`: all rows in the cluster come from the same source system
   - `CONTESTED_NO_AUTOMERGE`: identifier watchlist case where automated merge is not possible
   - `NO_USABLE_CONTACT`: no row in the cluster has a valid email or phone
5. For contacts with no usable channel (no valid email and no valid phone), quarantine the row.

## Identifier Watchlist

For field-service tasks, an identifier watchlist may specify cases where identity matching is contested. These cases have a dedicated `identifier_case_id` and a `source_row_anchor`. The anchor row's identity is contested with other rows matching the same identifier. If the contested case cannot be resolved automatically, mark it as `CONTESTED_NO_AUTOMERGE` and include its `identifier_case_id` in the `contested_cluster_ids` output.

## Quarantine Conditions

A row is quarantined (excluded from dispatchable/usable contacts) when:
- It has no valid email (null, empty, or unparseable) AND no valid phone (null, empty, or non-digit)
- The row is the sole representative of a canonical person with no usable channel

## Readiness and Dispatchability

For field-service roster readiness:
- A canonical person is dispatchable when: `record_status = ACTIVE`, has at least one usable channel (email or phone), and `consent_status = GRANTED`
- Per-depot readiness partitions active people by their blocking condition:
  - `dispatchable_person_count`: active + usable channel + GRANTED consent
  - `blocked_consent_count`: active + usable channel + non-GRANTED consent
  - `blocked_no_contact_count`: no usable channel (any status/consent)
  - `blocked_inactive_count`: INACTIVE + usable channel

For partner onboarding readiness:
- An entity is eligible when active and retains at least one usable email or phone
- A channel is ready when consent is GRANTED
- Partitions: `both` (email+phone ready), `email_only`, `phone_only`, `not_ready` (neither channel ready or entity ineligible)

## Control Codes for Contacts

Apply to evidence row patterns consistently:

| Evidence Pattern | Identity Code | Outreach Code | Field-Provenance Code |
|-----------------|---------------|---------------|----------------------|
| Single-source, clear identity | IC-25 | — | FP-20 |
| Quarantined (no usable contact) | IC-40 | OR-60 | FP-75 |
| Multi-source merged with precedence | IC-70 | — | FP-55 |
| Same-source merged | IC-90 | — | — |
| Active + usable channel + GRANTED consent | — | OR-35 | — |
| Active + usable channel + pending/denied consent | — | OR-80 | — |
| No usable contact channel | — | OR-60 | — |
| INACTIVE status | — | OR-15 | —
