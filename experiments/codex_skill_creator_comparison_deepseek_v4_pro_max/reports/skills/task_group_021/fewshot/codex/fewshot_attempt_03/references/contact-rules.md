# Contact Reconciliation Rules

## Source Systems and Precedence

Contact collections draw from 2–3 source systems. The available systems and
their relative precedence vary by collection. Always check the collection's
`source_systems` list in `GET /api/catalog/collections` before applying precedence.

### General Precedence Conventions

**Verified-flag tiebreak**: Rows with `verified_flag = 1` outrank rows with
`verified_flag = 0` or null, all else equal.

**Recency tiebreak**: When precedence and verified_flag are equal, prefer the
row with the most recent `business_updated_at`.

**Field-level precedence** (general defaults; verify against the collection):
- **Name** (`person_or_org_name`): HR Directory > Identity Registry > Dispatch > CRM > Compliance Master > Partner Portal
- **Email**: Identity Registry > HR Directory > Dispatch > CRM > Compliance Master > Partner Portal
- **Phone**: Identity Registry > Dispatch > HR Directory > CRM > Compliance Master > Partner Portal
- **City**: Compliance Master > HR Directory > Identity Registry > CRM > Dispatch > Partner Portal
- **Region/Depot**: HR Directory > Dispatch > Identity Registry > Compliance Master > CRM > Partner Portal
- **Consent**: Identity Registry > Compliance Master > HR Directory > Dispatch > CRM > Partner Portal
- **Record Status**: HR Directory > Identity Registry > Dispatch > CRM > Compliance Master > Partner Portal

Always load the collection's actual source systems and adapt precedence to the
specific systems present, preserving their relative order from this list.

## Clustering Rows into Canonical People

Rows represent the same person when they share any of:

1. **Same normalized email**: Unicode NFKC, trimmed, lowercased. Non-null and non-empty.
2. **Same phone digits**: Strip all non-digit characters; match on the resulting digit string. Non-null and non-empty.
3. **Same normalized name**: Unicode NFKC, trimmed. Names that differ only in diacritics, punctuation, or whitespace are considered matches.
4. **Same `master_hint`**: When populated, this field groups rows that the source system pre-identified as the same entity. If two rows share a non-null `master_hint`, they belong to the same cluster.

Build clusters transitively: if row A matches row B, and row B matches row C, then A, B, and C are the same person.

Rare edge: a row that matches no other row forms a cluster of size 1.

## Survivor Selection

For each cluster, select one row as the survivor (master ID):

1. Prefer rows with `verified_flag = 1`.
2. Among those, prefer rows from higher-precedence source systems (general: HR Directory > Identity Registry > Dispatch > CRM > Compliance Master > Partner Portal).
3. Tiebreak by most recent `business_updated_at`.
4. Final tiebreak: lowest `row_id` (lexicographic).

## Canonical Field Values

For each cluster, determine the canonical value for each field by applying
field-level source-system precedence:

1. Collect all non-null, non-empty values for the field across cluster members.
2. Sort candidate values by: (a) source-system precedence, (b) `verified_flag = 1` first, (c) most recent `business_updated_at`.
3. The top candidate is the canonical value.

For email: normalize to Unicode NFKC, trim, lowercase.
For phone: strip all non-digit characters; the canonical value is the digit string.
For name: preserve Unicode as-is (do not ASCII-fold).
For consent_status: normalize to uppercase; valid values are GRANTED, PENDING, DENIED, or UNKNOWN (treat null as UNKNOWN).
For record_status: normalize to uppercase; ACTIVE or INACTIVE.

## Quarantine

A row is quarantined when it has **no usable contact channel**: both `email`
is null/empty/whitespace AND `phone` is null/empty/whitespace (or digits-only
phone is empty after stripping).

Quarantined rows are included in canonical entity counts but excluded from
dispatchable/readiness counts.

## Readiness

An entity is **readiness-eligible** when:
- `record_status = 'ACTIVE'`
- Has at least one usable email or phone (not quarantined)

A channel is **ready** when:
- `consent_status = 'GRANTED'`

Readiness partitions:
- **both**: entity has usable email AND usable phone, and consent is GRANTED for both
- **email_only**: usable email only (no usable phone), consent GRANTED
- **phone_only**: usable phone only (no usable email), consent GRANTED
- **not_ready**: ACTIVE with usable channel(s) but consent not GRANTED, or INACTIVE

**Dispatchable** entities are those in the both, email_only, or phone_only partitions.
