# Asteria Fleet Control Code Reference

All Asteria audits require assignment of opaque three-character control codes.
The codes are domain-specific but follow consistent patterns across audits.
Each code scheme has exactly two or three allowed values; the correct code
must be inferred from the data evidence, not guessed.

---

## Identity Codes (IC)

Used for: focus_clusters, anchored_cases, quarantine_result, policy control
cases with IDENTITY family.

| Code | Assignment Rule |
|------|----------------|
| IC-25 | Single-row identity with a usable contact channel. The person appears in only one source row and that row has a usable email or phone. |
| IC-70 | Multi-row merged cluster where field-level precedence was applied to resolve canonical values from multiple source systems. All member rows have usable contacts. |
| IC-90 | Multi-row cluster where at least one member row is quarantined (no usable contact) OR where identifiers are contested across member rows. |
| IC-40 | Single row or cluster where no member row has a usable contact channel (fully quarantined identity). |

---

## Outreach Codes (OR)

Used for: readiness_partition, quarantine_result, inactive_exclusion, policy
control cases with OUTREACH family, anchored cases.

| Code | Assignment Rule |
|------|----------------|
| OR-35 | Active person with a usable contact channel AND consent status is GRANTED. This is the "channel-ready" state. |
| OR-80 | Active person with a usable contact channel but consent status is NOT GRANTED (PENDING, DENIED, or UNKNOWN). |
| OR-15 | Person whose canonical record status is INACTIVE, regardless of contact or consent. |
| OR-60 | Person with no usable contact channel (quarantined), regardless of status. |

For readiness_partition: `both`, `email_only`, and `phone_only` all map to
OR-35 (channel-ready). `not_ready` maps to OR-80 (the dominant blocking reason
for non-ready entities is non-granted consent).

---

## Field Provenance Codes (FP)

Used for: focus_decisions, anchored_cases, quarantine_result, policy control
cases with FIELD_PROVENANCE family.

| Code | Assignment Rule |
|------|----------------|
| FP-55 | Multi-source provenance. The canonical field values were resolved by applying field-level precedence across two or more source systems (e.g., name from HR Directory, contact from Identity Registry). |
| FP-20 | Single-source provenance. All relevant canonical values trace back to a single source system for the given entity. |
| FP-75 | No usable provenance. The entity is quarantined (no usable contact), making field-level provenance irrelevant. |

---

## Reference Basis Codes (RB)

Used for: reference_decisions in fuel audits (FUA IDs), reference_rows in
freight audits (FRA IDs). One code per scoped alias reference.

| Code | Assignment Rule |
|------|----------------|
| RB-42 | Primary/standard reference. The alias maps to a common, high-frequency canonical category (fuel type or service class) that forms the bulk of the collection. |
| RB-17 | Secondary/specialized reference. The alias maps to a less common canonical category. |
| RB-83 | Exceptional or edge-case reference. The alias maps to an unusual or rarely used canonical category. |

To determine which code applies, look up the `canonical_category` of the alias
in the `/api/reference/aliases` response. The categories with the highest
transaction/charge counts in the collection are primary, the next tier are
secondary, and the least common are exceptional.

---

## Source Basis Codes (SB)

Used for: transaction_decisions in fuel audits, source_retention in freight
audits. One code per scoped transaction/charge ID.

| Code | Assignment Rule |
|------|----------------|
| SB-61 | The transaction/charge appears **only** in the certified snapshot. It is a certified-only record. |
| SB-24 | The transaction/charge appears **only** in the provisional snapshot. It is a provisional-only record. |
| SB-79 | The transaction/charge appears in **both** the certified and provisional snapshots. The certified occurrence was retained (per the universal reconciliation rule) but the record has overlapping source evidence. |

To determine which code applies: for each scoped transaction/charge ID, check
whether it exists in the certified snapshot, the provisional snapshot, or both.
Use `POST /api/query` or the domain-specific endpoints scoped by `?snapshot_id=`
to check membership.

---

## Ledger Disposition Codes (LD)

Used for: transaction_decisions in fuel audits, ledger_routing in freight
audits. One code per scoped transaction/charge ID.

| Code | Assignment Rule |
|------|----------------|
| LD-72 | **Clean**. The transaction/charge is valid (not quarantined), has a recognized category, and the recognized category matches the expected category. No issues. |
| LD-31 | **Mismatch**. The transaction/charge is valid but the recognized canonical category differs from the expected category. |
| LD-14 | **Unrecognized**. The transaction/charge description matches zero recognized aliases. No canonical category can be assigned. |
| LD-88 | **Ambiguous**. The transaction/charge description matches aliases that resolve to more than one distinct canonical category. |
| LD-53 | **Quarantined — invalid measure**. The transaction/charge has an invalid physical measure (zero, negative, or null quantity/weight/distance) regardless of category recognition. |

The codes are mutually exclusive. If a transaction qualifies for multiple codes
(e.g., both unrecognized AND invalid quantity), apply the quarantine code
(LD-53) first, then LD-14/LD-88 for unrecognized/ambiguous, then LD-31 for
mismatch, and LD-72 for clean.

---

## Maintenance Source Codes (MS)

Used for: event_decision_panel in maintenance audits. One code per scoped event.

| Code | Assignment Rule |
|------|----------------|
| MS-47 | The event exists **only** in the certified snapshot. |
| MS-12 | The event exists **only** in the provisional snapshot. |
| MS-86 | The event exists in **both** certified and provisional snapshots (overlapping). |

---

## History Route Codes (HR)

Used for: event_decision_panel in maintenance audits. One code per scoped event.

| Code | Assignment Rule |
|------|----------------|
| HR-33 | **Valid**. The event passes all quality checks: timestamp is present and parsable, odometer is in valid range, labor hours are non-negative and within bounds, and the event is not a regression. |
| HR-19 | **Regression**. The event is valid (passes quality checks) but is flagged as an odometer regression (later event with lower odometer than a preceding event on the same asset). |
| HR-74 | **Rejected**. The event fails one or more quality checks (missing/invalid timestamp, invalid odometer, negative/extreme labor hours) and is fully excluded from the corrected history. |

The codes are mutually exclusive. Apply HR-74 first (any quality check failure
trumps regression), then HR-19 (regression on an otherwise valid event), then
HR-33 (clean).

---

## Certification Status

All audits produce a final certification:

| Status | Action | Trigger |
|--------|--------|---------|
| PASS | RELEASE | All quality thresholds met with zero exceptions. |
| PASS_WITH_EXCEPTIONS | REVIEW_EXCEPTIONS | Quality thresholds met but some exceptions exist within the allowed rate. |
| HOLD | BLOCK_AND_REMEDIATE | Quality thresholds exceeded; the data cannot be released without remediation. |

Thresholds are defined in the case scope (`case_scope.json`). Common patterns:
- For contacts: HOLD if `quarantine_rate > pass_with_exceptions_max_quarantine_rate`,
  PASS_WITH_EXCEPTIONS if `quarantine_rate > 0` but ≤ threshold, PASS if zero quarantine.
- For fuel/freight: HOLD if mismatch or quarantine rates exceed acceptable bounds
  (typically inferred from the business context — if exceptions are substantial
  relative to the valid population, hold the release).
- For maintenance: HOLD if odometer regressions exist (the certification gate in
  the case scope specifies this explicitly).
