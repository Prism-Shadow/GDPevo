# Asteria Internal Code Systems

This reference lists every control code used across the training tasks, with the
decision logic needed to assign the correct code to each record. Codes are
domain-specific; only a subset applies to any given task.

---

## Identity Codes (IC-*)

Used in: contact certification, roster readiness

| Code | Meaning | When to assign |
|---|---|---|
| `IC-25` | Single-source, uncontested | The canonical entity draws from exactly one source system and no identifier conflicts exist. Used for anchored cases where all evidence rows are in the same cluster and share a single source. |
| `IC-40` | Quarantined — unreliable identity | The row or cluster has no usable contact channel, making identity unreliable. The quarantine_result code. |
| `IC-70` | Multi-source, field-level merge | The canonical entity was constructed from multiple source systems using field-level precedence rules. Canonical field values came from different sources. Used for focus clusters with multi-source membership. |
| `IC-90` | Multi-source, fully corroborated | The same identity appears across all available source systems with consistent identifiers. Used for anchored cases where seed rows span different clusters but the hub has linked them. |

**Decision flow for identity codes:**

For a focus cluster:
1. Check how many distinct `source_system` values appear among member rows.
2. If only 1 source → `IC-25`.
3. If 2+ sources AND field-level precedence was applied → `IC-70`.

For an anchored control case:
1. Collect all seed rows. Find their clusters.
2. If all seed rows belong to the same cluster → `IC-25`.
3. If seed rows belong to different clusters → `IC-90`.

For quarantine:
- Always `IC-40`.

---

## Outreach Codes (OR-*)

Used in: contact certification, roster readiness

| Code | Meaning | When to assign |
|---|---|---|
| `OR-15` | Inactive exclusion | The canonical entity's status is `INACTIVE`. |
| `OR-35` | Dispatchable | Active, consent `GRANTED`, at least one usable contact channel. |
| `OR-60` | Quarantined — no usable contact | No usable email AND no usable phone. |
| `OR-80` | Consent-blocked | Active, has a usable channel, but consent is not `GRANTED` (is `PENDING`, `DENIED`, or `UNKNOWN`). |

**Decision flow for outreach codes on a canonical entity:**

1. Check `status` first: if `INACTIVE` → `OR-15`.
2. Check contact channels: if no usable email AND no usable phone → `OR-60`.
3. Check consent: if `GRANTED` → `OR-35`.
4. Otherwise (usable channel exists, consent not GRANTED) → `OR-80`.

**Readiness partition codes:**
- `both` partition: entities with both channels → `OR-35`
- `email_only` partition: entities with email only → `OR-35`
- `phone_only` partition: entities with phone only → `OR-35`
- `not_ready` partition: active entities with no usable channel → `OR-80`

---

## Field Provenance Codes (FP-*)

Used in: contact certification

| Code | Meaning | When to assign |
|---|---|---|
| `FP-20` | Single-source provenance | All data for the entity/cluster originates from a single source system. |
| `FP-55` | Multi-source field-level merge | The canonical record draws different fields from different sources. |
| `FP-75` | Quarantined provenance | Data quality issues prevent reliable field attribution. |

**Decision flow:**

1. If quarantined → `FP-75`.
2. If all member rows share one `source_system` → `FP-20`.
3. If member rows come from multiple source systems → `FP-55`.

---

## Source Basis Codes (SB-*)

Used in: fuel audit, freight accrual

| Code | Meaning | When to assign |
|---|---|---|
| `SB-24` | Certified-only | The record appears only in the CERTIFIED snapshot. |
| `SB-61` | Multi-snapshot, certified retained | The record appears in both CERTIFIED and PROVISIONAL; certified version is the authoritative survivor. |
| `SB-79` | Provisional-only | The record appears only in the PROVISIONAL snapshot. |

**Decision flow:**

For each record ID, check which snapshots contain it:
1. CERTIFIED only → `SB-24`
2. PROVISIONAL only → `SB-79`
3. Both → `SB-61`

---

## Ledger Disposition Codes (LD-*)

Used in: fuel audit, freight accrual

| Code | Meaning | When to assign |
|---|---|---|
| `LD-14` | Quarantined — unrecognized category | The description/alias maps to zero canonical categories. |
| `LD-31` | Valid, category mismatch | The recognized category differs from the expected/reported category. |
| `LD-53` | Valid, matched, certified-only | Category matches, record is single-snapshot (certified). |
| `LD-72` | Valid, matched, provisional-only or multi-snapshot | Category matches, record was retained from provisional or multi-snapshot. |
| `LD-88` | Quarantined — ambiguous category | The description/alias maps to more than one canonical category. |

**Decision flow:**

1. If the record is quarantined for category reasons:
   - Unrecognized (zero matches) → `LD-14`
   - Ambiguous (multiple matches) → `LD-88`
2. If valid and category matches expected:
   - Certified-only source → `LD-53`
   - Provisional-only or multi-snapshot → `LD-72`
3. If valid but category mismatch → `LD-31`

Note: Invalid-quantity quarantines are not category quarantines. Those
transactions do not appear in ledger-disposition panels — only category-related
codes appear in ledger panels.

---

## Reference Policy Codes (RB-*)

Used in: fuel audit, freight accrual

| Code | Meaning | When to assign |
|---|---|---|
| `RB-17` | Clean, unambiguous alias | The alias maps to exactly one canonical category and the charge's actual class matches the reference mapping. |
| `RB-42` | Recognized, contested | The alias has a mapping in the reference data but the charge's actual class differs from the reference, or the mapping is otherwise contested. |
| `RB-83` | Unrecognized | No mapping exists for this alias in the reference data. |

**Decision flow:**

1. Query `/api/reference/aliases` for the alias.
2. No entry found → `RB-83`.
3. Exactly one entry found AND the charge's actual service class matches the
   canonical class → `RB-17`.
4. Exactly one entry found BUT the charge's actual service class differs →
   `RB-42`.

---

## Maintenance Source Codes (MS-*)

Used in: maintenance integrity

| Code | Meaning | When to assign |
|---|---|---|
| `MS-12` | Provisional-only | The event appears only in the PROVISIONAL snapshot. |
| `MS-47` | Certified-only | The event appears only in the CERTIFIED snapshot. |
| `MS-86` | Multi-snapshot | The event appears in both snapshots; certified version retained. |

**Decision flow:**

Same as source-basis codes, adapted for maintenance:
1. Certified only → `MS-47`
2. Provisional only → `MS-12`
3. Both → `MS-86`

---

## History Route Codes (HR-*)

Used in: maintenance integrity

| Code | Meaning | When to assign |
|---|---|---|
| `HR-19` | Odometer regression | The event's odometer reading is lower than a previous reading for the same asset. |
| `HR-33` | Clean, single-source | No regression detected; event comes from a single snapshot. |
| `HR-74` | Clean, multi-source | No regression detected; event appears in multiple snapshots. |

**Decision flow:**

1. Check if the event is flagged as odometer regression → `HR-19`.
2. If not regression and single-snapshot → `HR-33`.
3. If not regression and multi-snapshot → `HR-74`.

Note: Some scoped events may appear in `invalid_event_ids` (for timestamp,
odometer, or labor issues) but still receive HR codes. Check each scoped event's
odometer data relative to its asset's event sequence.

---

## Quick-reference assignment table

| Task domain | Code families used |
|---|---|
| Contact certification | IC, OR, FP |
| Fuel audit | SB, LD, RB |
| Freight accrual | SB, LD, RB |
| Maintenance integrity | MS, HR |
| Roster readiness | IC, OR, FP |
