# Control codebook — decoding the opaque Asteria codes

Tasks require "opaque" control codes whose expansions are **intentionally withheld** from
the task materials. They are, however, a **fixed, closed vocabulary** with stable meaning
across the whole task family, so they can be assigned by rule. Below is each code family,
the property it encodes, and the assignment rule. Each rule was derived by joining the
hub's records to labeled control anchors and is consistent across the fuel, freight,
maintenance, and contacts training cases. **Always re-derive from the record evidence for
the specific IDs a task asks about** — the *rules* are reusable; the specific assignments
are not.

The allowed value set for a field is whatever the task's `answer_template.json` enumerates;
match your derivation to that enum.

---

## Retention basis — how a retained record's snapshot origin is coded
Same 3-way logic as de-duplication (§1 of reconciliation), two families, two code sets:

| Situation (after cross-snapshot dedup) | fuel/freight `SB-*` | maintenance `MS-*` |
|---|---|---|
| key present in **CERTIFIED snapshot only** | `SB-24` | `MS-12` |
| key present in **both** → retained from CERTIFIED (a duplicate) | `SB-61` | `MS-47` |
| key present in **PROVISIONAL snapshot only** | `SB-79` | `MS-86` |

(Fuel `transaction_decisions.source_basis_code`, freight `source_retention.decision_code`,
maintenance `event_decision_panel.maintenance_source_code`.)

---

## Reference/alias basis — `RB-*` (fuel & freight `reference_*` panels)
Classifies an alias row's authority *as of the business cutoff*:

| Alias condition | Code |
|---|---|
| `reference_status = ACTIVE` **and** effective at cutoff (`valid_from ≤ cutoff ≤ valid_to/none`) | `RB-42` |
| `reference_status = PROVISIONAL` | `RB-83` |
| not effective at cutoff: `reference_status = INACTIVE`, **or** window expired/not-yet-started | `RB-17` |

Only `RB-42` aliases are the ones actually used for canonical category resolution.
(Note: an alias future-dated `valid_from` *or* an INACTIVE-but-still-in-window alias both → `RB-17`.)

---

## Ledger disposition — `LD-*` (fuel & freight, 5 values)
The record's disposition in the reconciled ledger:

| Disposition | Code |
|---|---|
| valid; recognized class **matches** expected class (clean) | `LD-72` |
| valid; recognized class **≠** expected class (class mismatch; still in totals) | `LD-31` |
| quarantined — **unrecognized** class (zero alias match) | `LD-14` |
| quarantined — **ambiguous** class (≥2 alias matches) | `LD-88` |
| quarantined — **invalid physical measure** (non-positive quantity / weight / distance) | `LD-53` |

Precedence: a quarantine reason (LD-14/88/53) outranks mismatch (LD-31) outranks clean (LD-72).
Quarantine-reason → code: unrecognized→LD-14, ambiguous→LD-88, invalid weight/distance/qty→LD-53.

---

## History route — `HR-*` (maintenance, 3 values)
The event's routing in the reconstructed Q-history:

| Disposition | Code |
|---|---|
| valid event routed into corrected history (clean) | `HR-33` |
| **odometer regression** event (sequence regression; kept but flagged) | `HR-19` |
| **rejected/invalid** event (missing/unparsable time, invalid odometer, negative/extreme labor) | `HR-74` |

Precedence: invalid (HR-74) outranks regression (HR-19) outranks clean (HR-33).

---

## Identity code — `IC-*` (contacts, 4 values)
Classifies the identity-resolution disposition of the evidence group (a focus cluster,
an anchor's `seed_row_ids`, or a control case's `evidence_row_ids`):

| Disposition of the evidence group | Code |
|---|---|
| **contested / shared identifier** — rows reuse an identifier across *different* people, or carry a shared master_hint (e.g. `SHARED-HELPDESK`); must not auto-merge | `IC-25` |
| **single standalone row** — one row, one person, no collision, no merge | `IC-40` |
| **confident cross-source merge** — multiple rows from *distinct source systems* resolve to one person (field-level precedence applied) | `IC-70` |
| **same-person duplicate cluster** — multiple rows collapsing to one person *within/without clean cross-source precedence* (e.g. same-name duplicates, or conflicting-contact near-dups) | `IC-90` |

Decision order: shared/contested identifier → `IC-25`; else single row → `IC-40`;
else clean multi-source merge → `IC-70`; else duplicate cluster → `IC-90`.

---

## Outreach code — `OR-*` (contacts, 4 values)
The outreach/dispatch disposition of the resolved entity (same precedence as readiness §6):

| Disposition | Code |
|---|---|
| **no usable channel** (quarantine) | `OR-60` |
| **inactive** (has a channel but `record_status = INACTIVE`) | `OR-15` |
| **ready** — active + usable channel + consent `GRANTED` | `OR-35` |
| **blocked by consent** — active + usable channel + consent not granted (PENDING/DENIED/UNKNOWN) | `OR-80` |

So in `readiness_partition`: the `both`/`email_only`/`phone_only` (ready) buckets → `OR-35`;
`not_ready` → `OR-80`. `inactive_exclusion` → `OR-15`; a quarantine result → `OR-60`.

---

## Field-provenance code — `FP-*` (contacts, 3 values)
How the canonical record's fields were sourced:

| Provenance | Code |
|---|---|
| **field-level precedence applied** — canonical fields assembled from multiple sources (a real cross-source merge) | `FP-55` |
| **single-source** — all canonical fields from one source row (includes contested pairs that did NOT auto-merge, so each stays single-source) | `FP-20` |
| **quarantine / no usable contact** — provenance undefined because the entity has no usable channel | `FP-75` |

---

### Sanity mnemonic
- Snapshot origin drives `SB`/`MS`.
- Alias authority drives `RB`.
- Record validity+match drives `LD` (5-way) / `HR` (3-way).
- Contacts split into three orthogonal axes: **identity** (`IC`), **outreach/consent** (`OR`),
  **field provenance** (`FP`) — a single person gets one code from each axis where the
  contract asks for it.
