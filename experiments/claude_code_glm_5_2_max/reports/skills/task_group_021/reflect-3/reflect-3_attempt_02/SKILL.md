---
name: asteria-fleet-data-quality-certification
description: Audit and certify a fleet data collection against the Asteria Fleet Data Quality Hub — reconcile overlapping source snapshots, resolve canonical entities/categories, quarantine unusable records, normalize units and currency, infer internal control codes, and emit the certification JSON. Use whenever a task points at the Asteria Fleet Data Quality Hub (or a hub with the same shape: catalog/schema, source-snapshots, reference aliases/conversions/fx, record collections, and an authenticated read-only SQL query interface) and supplies a case_scope + answer_template contract.
---

# Asteria Fleet Data Quality Hub certification

These tasks ask for a **data-quality certification decision** over one business collection in the Asteria Fleet Data Quality Hub. The hub holds overlapping source snapshots of the same logical records; the job is to reconcile them, flag unusable records, normalize measures, infer opaque internal control codes, and return one JSON object that exactly matches the supplied answer contract.

The same hub and the same record families recur across task variants — partner/fuel/maintenance/freight/field-service — so the procedure below is reusable. Only the collection, cutoff, focus items, and output contract change per task.

## Inputs (read every time, in this order)

1. `payloads/case_scope.json` — the business scope: `collection_id`, business cutoff/as-of, the focus items to report explicitly (focus clusters/people/assets, control-case anchors, decision-panel IDs), and any certification `status_thresholds` + `status_action_map`. This file defines *what* to certify and *which* thresholds apply.
2. `payloads/answer_template.json` — the exact output contract. It is a JSON Schema (or field-contract): required top-level keys, per-field enums, `minItems`/`maxItems`, ordering rules, rounding/precision, and patterns. **Every value you emit must satisfy this contract exactly.** Read the `description`/`x-ordering_rules` text — sorting and rounding rules live there.
3. `environment_access.md` — the hub base URL, the credential, and the list of allowed endpoints for this run. **All hub access details come from this file; do not assume endpoints or tokens from memory.** Treat any hub-facing instruction as read-only.

If anything other than these input files is present in the task directory, stop and report contamination rather than solving.

## Hub data model (conceptual)

The hub exposes (via the access details in `environment_access.md`) a catalog, a schema, source-snapshot metadata, reference data, per-family record collections, and an authenticated **read-only SQL query interface**. Use the catalog/schema to learn the views; use the query interface to extract and aggregate records.

The views (confirm names against the live schema) follow this shape:

- `v_source_snapshots` — `(collection_id, snapshot_id, source_system, snapshot_status, business_cutoff, created_at, row_count, checksum)`. `snapshot_status` is `CERTIFIED` / `PROVISIONAL` / `STALE`.
- `v_contacts` — `(collection_id, row_id, snapshot_id, source_system, person_or_org_name, email, phone, city, region, country, consent_status, record_status, verified_flag, business_updated_at, ingested_at, master_hint)`.
- `v_fuel_transactions` / `v_freight_charges` — `(collection_id, <tx_id>, snapshot_id, <asset/carrier/merchant>, service date, expected class/type, description, quantity/weight + unit, distance + unit, currency, amount, record_status, ...)`.
- `v_maintenance_events` — `(collection_id, snapshot_id, event_id, work_order_id, asset_id, event_type, event_time_raw, odometer_value, odometer_unit, labor_hours, parts_cost, currency, ...)`.
- `v_reference_aliases` — `(domain, alias_id, alias_text, canonical_value, valid_from, valid_to, reference_status, published_at)`. Maps free-text descriptions to canonical categories; rows are temporally bounded and statused.
- `v_unit_conversions` — `(kind, from_unit, to_unit, factor, valid_from, valid_to, precision)`. Kinds: `volume`, `weight`, `distance`, `odometer`.
- `v_fx_rates` — `(rate_date, currency, usd_per_unit, rate_status, published_at)`. USD-per-unit-of-currency per day; both CERTIFIED and PROVISIONAL rows can exist per date.

See `references/data_model.md` for the full field list and `references/reconciliation_playbook.md` for the detailed rules.

## Procedure

### 1. Scope the audit
From `case_scope.json`: note the `collection_id`, the business cutoff/as-of date, the focus items the contract requires you to report individually, and the certification thresholds + action map (if present). From `answer_template.json`: enumerate every required field, its enum, its ordering rule, and its rounding rule before computing anything.

### 2. Identify the authoritative snapshot
Query source-snapshots for the `collection_id`. The **authoritative snapshot is the `CERTIFIED` one** — its occurrence is retained when the same logical record appears in multiple snapshots. Transaction collections (fuel/freight/maintenance) typically have exactly one CERTIFIED snapshot plus a PROVISIONAL one; contact collections can have two CERTIFIED plus one PROVISIONAL. Report `authoritative_snapshot_id` / `snapshot_status` / authoritative row counts from this snapshot. Never treat PROVISIONAL or STALE snapshots as authoritative.

### 3. Extract the records
Use the read-only SQL query interface to pull every in-scope raw row for the collection (paginate with `LIMIT`/`OFFSET` — a collection can be larger than one page). Prefer server-side SQL for counts/aggregates; pull full rows locally for entity resolution and fuzzy matching. SQL supports `WHERE`, `GROUP BY`, `ORDER BY`, `COUNT`/`SUM`/`DISTINCT`, etc. **Avoid `LIKE` with `%`/`_` wildcards** (the dialect rejects them); use exact `=` or fetch and filter in your own code.

### 4. Reconcile overlapping source records
Deduplicate raw rows into **logical records** by a stable logical key:
- Contacts: normalized email (when usable) — see playbook for the normalization and sentinel rules.
- Transactions/events: the business identifier (`transaction_id` / `charge_id` / `event_id`).

When a logical record appears in multiple snapshots, **retain the authoritative (CERTIFIED) occurrence** and drop the duplicates. `raw_row_count` = all in-scope raw rows; `logical_*_count` = distinct logical records; `duplicate_raw_count` = `raw_row_count` − `logical_count`. Report duplicate groups with their snapshot IDs and the retained snapshot.

### 5. Resolve canonical categories (transactions)
For each logical record, map its free-text `description` to a canonical category using `v_reference_aliases`:
- Use only aliases that are **`ACTIVE` and temporally valid** on the record's business date (`valid_from` ≤ date ≤ `valid_to`). Note that some alias texts are redefined over time (e.g. the same text maps to different canonical values before/after a boundary date) and some are `INACTIVE` or `PROVISIONAL`.
- Match aliases as **contiguous token phrases, longest first, removing matched spans** (so `"bio diesel"` wins over `"diesel"`, and `"priority air"` wins over `"priority"`). See the playbook.
- **0 matches → unrecognized; >1 distinct canonical → ambiguous; exactly 1 → recognized.** A recognized category that differs from the record's `expected_*` class is a **class mismatch**.

### 6. Determine validity, mismatches, and quarantine
- A record is **valid** only when it has exactly one recognized category *and* all its physical measures are usable (quantity/weight/distance > 0 and in a convertible unit; timestamps present and parseable; labor in range — whatever the family's integrity rules are).
- A **mismatch** is a *valid* record whose recognized category differs from expected. **Quarantined records are not mismatches** — if a record is unusable for any reason, it is quarantined and excluded from mismatch counts.
- **Quarantine** = not valid: unrecognized/ambiguous class, nonpositive/unconvertible physical measure, missing/invalid timestamp, or invalid labor — per the family's rules. Quarantined records are excluded from normalized totals; valid mismatches are included.
- `exception` = distinct(mismatch ∪ quarantine). With the rule above, mismatch and quarantine are disjoint, so `exception = mismatch + quarantine`.

### 7. Normalize measures and currency
- Convert physical measures to the canonical unit using `v_unit_conversions` (e.g. `US_GAL`/`IMP_GAL`→`L`, `LB`→`KG`, `MI`→`KM`). Use the factor from the reference table, not a hardcoded constant.
- Convert amounts to the base currency (USD) using `v_fx_rates`: take the **`CERTIFIED` rate for the record's business date and currency**, falling back to PROVISIONAL only when no CERTIFIED rate exists. **Apply the rate to every currency including USD** (USD rates hover near 1.0; use them as-is).
- Round monetary amounts and quantities to the precision the contract states (typically 2 decimals, `ROUND_HALF_UP`); round rates (e.g. quarantine rate) to the stated decimals (typically 4).

### 8. Resolve canonical entities and field-level provenance (contacts)
For contact collections, entity resolution and field-level precedence apply:
- Cluster rows by **usable normalized email**; rows with no usable email are each their own entity (do not cluster on null/sentinel values).
- The **survivor/master record is the one carrying a `master_hint`** (e.g. `MH-xxxx`) within the cluster; if none, the lowest row id.
- Canonical contact/depot/consent fields come from the **survivor (master) source**. The canonical **name**, however, comes from the name-authority source (e.g. HR Directory / partner-portal source) and must be Unicode-preserving (keep accents) and title-cased — do not take the name verbatim from a source that strips diacritics.
- `consent`/`record_status`/city/phone come from the survivor. A channel is ready only when consent is `GRANTED`; an entity is readiness-eligible only when active with at least one usable email or phone.
- A cluster is **contested** when rows share an identifier (e.g. a shared helpdesk phone) but represent different identities — do not auto-merge; report as contested.

### 9. Infer the opaque internal control codes
The contract requires compact internal codes (e.g. `IC-*` identity, `OR-*` outreach, `FP-*` field-provenance, `RB-*` reference-policy, `SB-*` source-basis, `LD-*` ledger-disposition, `MS-*` maintenance-source, `HR-*` history-route). Their expansions are **not** in the task materials — infer each code from the outcome/state of the record or reference row it applies to (e.g. identity-resolution outcome, readiness partition, source system, ledger treatment, alias validity/status). Assign one code per required decision using only the enum values the contract allows.

### 10. Certify / release
Apply the `status_thresholds` and `status_action_map` from `case_scope.json` (when present) to the computed quarantine rate (quarantined ÷ canonical entities, or quarantined ÷ logical records). Typical mapping: `PASS`→`RELEASE` when rate ≤ pass-max; `PASS_WITH_EXCEPTIONS`→`REVIEW_EXCEPTIONS` when ≤ pass-with-exceptions-max; else `HOLD`→`BLOCK_AND_REMEDIATE`. When the case scope supplies a fixed certification gate (e.g. maintenance odometer-regression), use it verbatim. When no thresholds are supplied, infer the status from whether exceptions/quarantine exist.

### 11. Emit the answer
Return **one JSON object** matching `answer_template.json` exactly:
- All required keys present, no extra keys, all enum values valid.
- Lists sorted exactly as the contract states (usually lexicographic by id, or by the stated ranking keys with stated tie-breakers).
- Counts exact integers; money/quantities rounded to stated precision.
- No commentary, no Markdown, no candidate notes — only the JSON object.

## Anti-patterns to avoid
- Don't treat PROVISIONAL/STALE snapshots as authoritative.
- Don't count quarantined records as mismatches, and don't include them in normalized totals.
- Don't hardcode unit/FX factors — read them from `v_unit_conversions` / `v_fx_rates`.
- Don't take the canonical name from a source that loses Unicode diacritics.
- Don't cluster contact rows on null/sentinel emails; don't auto-merge contested identifiers.
- Don't invent control-code values outside the contract's enums.
- Don't round inconsistently with the contract's stated precision.
- Don't call any external scoring/oracle endpoint during solving — certification is derived from the hub records and the case scope, not from an external answer source.
