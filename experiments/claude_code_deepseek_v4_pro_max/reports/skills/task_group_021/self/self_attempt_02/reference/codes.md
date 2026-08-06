# Asteria Control & Decision Code Reference

This reference catalogs every opaque code family and its enum members observed across the Asteria Fleet Data Quality Hub audit tasks. Use this together with `SKILL.md` Phase 7 (Assign Control and Decision Codes).

## Code Assignment Principle

Every code is **derived from the reconciled data evidence**, not guessed. For each entity being coded, examine:
1. Which source systems contributed rows.
2. Whether those sources agree or conflict on the field relevant to the code family.
3. The snapshot status of the retained/survivor row.
4. Any quality issues (quarantine, mismatch, regression, unrecognized).

## Code Families

### Identity Codes (IC)

Used for: focus-cluster decisions, anchored control cases with `IDENTITY` family, quarantine results.

| Code | Evidence Pattern |
|---|---|
| `IC-25` | All contributing source rows agree on the identity field; single-source resolution |
| `IC-40` | Multiple sources contribute and agree; field-level merge produced a consistent identity |
| `IC-70` | Multiple sources contribute with minor identity-field variance; merge resolved via precedence |
| `IC-90` | Identity contested across sources; no automated merge possible |

### Outreach Codes (OR)

Used for: anchored control cases with `OUTREACH` family, readiness partitions, quarantine results, inactive exclusions.

| Code | Evidence Pattern |
|---|---|
| `OR-15` | Entity has both usable email and phone, consent granted for both channels |
| `OR-35` | Entity has at least one usable channel with consent granted; the other channel is missing or consent is not granted |
| `OR-60` | Entity has a usable channel but consent is pending/denied/unknown |
| `OR-80` | Entity has no usable contact channels (both email and phone missing/invalid) |

### Field Provenance Codes (FP)

Used for: focus-cluster decisions, anchored control cases with `FIELD_PROVENANCE` family, quarantine results.

| Code | Evidence Pattern |
|---|---|
| `FP-20` | Single source system contributes all rows for this entity |
| `FP-55` | Two source systems contribute rows; they agree on the key field |
| `FP-75` | Two or more source systems contribute rows with disagreement; precedence rule applied |

### Reference Policy Codes (RB)

Used for: reference-alias decision panels (fuel audit, freight reconciliation).

| Code | Evidence Pattern |
|---|---|
| `RB-17` | Alias maps deterministically 1:1 to a single recognized category |
| `RB-42` | Alias maps to multiple possible categories; disambiguation required |
| `RB-83` | Alias has no recognized category mapping |

### Source Basis Codes (SB)

Used for: transaction/charge source-retention decision panels.

| Code | Evidence Pattern |
|---|---|
| `SB-24` | Retained occurrence comes from a `CERTIFIED` snapshot |
| `SB-61` | Retained occurrence comes from a `PROVISIONAL` snapshot |
| `SB-79` | Retained occurrence comes from a `STALE` snapshot; no better source available |

### Ledger Disposition Codes (LD)

Used for: transaction/charge ledger-routing decision panels.

| Code | Evidence Pattern |
|---|---|
| `LD-14` | Charge is valid, recognized, and has no mismatches or quality issues |
| `LD-31` | Charge is valid but has an expected-vs-actual class mismatch |
| `LD-53` | Charge is valid but has an unrecognized or ambiguous class |
| `LD-72` | Charge is quarantined for invalid physical measures or class |
| `LD-88` | Charge is a duplicate occurrence (not the retained copy) |

### Maintenance Source Codes (MS)

Used for: maintenance-event decision panels.

| Code | Evidence Pattern |
|---|---|
| `MS-12` | Event sourced from a `CERTIFIED` snapshot |
| `MS-47` | Event sourced from a `PROVISIONAL` snapshot |
| `MS-86` | Event sourced from a `STALE` snapshot |

### History Route Codes (HR)

Used for: maintenance-event decision panels.

| Code | Evidence Pattern |
|---|---|
| `HR-19` | Event is valid: all fields parse, no odometer regression, within valid ranges |
| `HR-33` | Event has an odometer regression relative to the preceding event on the same asset |
| `HR-74` | Event is invalid: missing/unparsable timestamp, invalid odometer, or invalid labor |

## Source Systems

Tasks reference these source systems. Codes are derived based on which systems contribute and whether they agree.

| Source System | Typical Data |
|---|---|
| `CRM` | Contact names, email addresses, phone numbers |
| `Compliance Master` | Contact identities, compliance status |
| `Partner Portal` | Partner-submitted contact information |
| `HR Directory` | Employee names, employment status |
| `Dispatch` | Contact phone numbers, depot/region assignment |
| `Identity Registry` | Government-issued identifiers, identity verification status |
| `Telematics` | Odometer readings, asset telemetry |
| `Shop Log` | Maintenance labor hours, work descriptions |
| `Carrier EDI` | Freight charge details, carrier-submitted service classes |
| `Fleet ERP` | Internal service-class assignments, cost-center coding |

## Channel Readiness Criteria

An entity is **readiness-eligible** when:
- `canonical_record_status` is `ACTIVE`
- At least one of `canonical_email` or `canonical_phone_digits` is non-null and non-empty

A channel is **ready** ("consent granted") when:
- The channel (email or phone) has a usable value AND `canonical_consent_status` is `GRANTED`

Readiness partitions:
| Partition | Conditions |
|---|---|
| `both` | Usable email AND usable phone, consent `GRANTED` |
| `email_only` | Usable email with consent `GRANTED`; phone missing or consent not `GRANTED` |
| `phone_only` | Usable phone with consent `GRANTED`; email missing or consent not `GRANTED` |
| `not_ready` | All other cases (inactive, no usable channels, consent not `GRANTED` for any usable channel) |

## Snapshot Status Priority

When resolving overlapping records, prefer snapshots in this order:
1. `CERTIFIED` — highest authority
2. `PROVISIONAL` — intermediate authority
3. `STALE` — lowest authority; use only when no better snapshot contains the logical entity

Within the same status tier, prefer the most recent `as_of` that is ≤ the business cutoff.
