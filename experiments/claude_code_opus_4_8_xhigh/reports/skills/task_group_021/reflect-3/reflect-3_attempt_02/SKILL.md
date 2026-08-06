---
name: fleet-data-quality-reconciliation
description: >
  Solve "Asteria Fleet Data Quality Hub" reconciliation, cleanup, and
  certification tasks. Use when a task gives a prompt plus
  payloads/case_scope.json and payloads/answer_template.json and asks you to
  reconcile overlapping source snapshots for a collection (contacts /
  fuel / freight / maintenance) as of a business cutoff and emit one JSON
  object matching the answer contract (quality counts, duplicate/quarantine
  sets, normalized totals, focus rollups, rankings, opaque control codes, and
  a certification/close decision). Runtime connection details come from the
  task's own environment_access.md.
---

# Fleet Data Quality Hub — reconciliation & certification

You are auditing one **collection** of raw records that arrives as several
overlapping **source snapshots** and must produce a single JSON object that
reconciles them, computes integrity metrics, and states a release decision.
Every task in this family follows the same shape; only the domain differs.

## 0. Read the three contracts first, then act

1. `prompt.txt` — narrative; tells you the domain and any special counting rules.
2. `payloads/case_scope.json` — the machine-readable scope: collection id,
   business cutoff, focus items, ranking limits, status thresholds / gates,
   status→action map, and the lists of ids whose control codes you must return.
3. `payloads/answer_template.json` — the **binding output schema**. Treat it as
   law: required keys, `additionalProperties:false`, enum sets, array
   `min/max/uniqueItems`, patterns, and every `description` (they encode
   ordering, rounding, and inclusion rules). Build your answer to validate
   against it exactly.

Runtime access (base URL, auth header, the list of readable endpoints) is in the
task's **`environment_access.md`** — read it; do not assume paths or
credentials. The hub is **read-only**. There is **no feedback endpoint at test
time**: solve in one shot from the data. Do not look for, expect, or call any
grading/judge service while solving.

## 1. The hub data model

Access is an authenticated **read-only SQL query interface over logical views**
(plus per-family GET endpoints and a catalog/schema endpoint). Confirm the exact
view/field names from the catalog **schema** endpoint before querying. The
views you will typically see:

- `v_source_snapshots` — one row per (collection, snapshot): `snapshot_id`,
  `source_system`, `snapshot_status` (CERTIFIED / PROVISIONAL / STALE),
  `business_cutoff`, `created_at`, `row_count`.
- One raw-record view per family: `v_contacts`, `v_fuel_transactions`,
  `v_freight_charges`, `v_maintenance_events`. Each row carries `collection_id`,
  `snapshot_id`, `source_system`, a business key, the domain fields, a
  `record_status`, and `business_updated_at`.
- Reference views: `v_reference_aliases` (domain, alias_text→canonical_value,
  validity window, reference_status), `v_unit_conversions` (kind, from_unit,
  to_unit, factor, precision), `v_fx_rates` (rate_date, currency,
  usd_per_unit, rate_status).

The query interface returns `{columns, rows, truncated}`. Pull whole scoped
tables into memory and reconcile in code (Python). Always check `truncated`; if
set, page by ordered key ranges. `scripts/hub_toolkit.py` wraps all of this
(reads `environment_access.md`, runs queries, and provides the normalizers,
dedup, alias/unit/fx resolvers described below).

## 2. Universal reconciliation pipeline

Every task is a variation of these steps:

1. **Pick the authoritative snapshot.** Among the collection's snapshots within
   the business cutoff, the **CERTIFIED** one is authoritative. Report its
   `snapshot_id` (and status/row_count) wherever the contract asks.
2. **Scope the raw rows.** All rows across the in-scope snapshots within the
   cutoff / business period. `raw_row_count` counts these raw rows (duplicates
   included).
3. **Reduce raw rows to logical entities** by the business key
   (transaction/charge/event id) or by identity resolution (contacts). A key in
   >1 snapshot is a **cross-snapshot duplicate**; keep the **authoritative
   (CERTIFIED)** occurrence's values as the retained record.
   `duplicate_raw_count = raw_row_count − logical_count`.
4. **Classify each logical entity** (valid / mismatch / quarantine) per the
   family rules below.
5. **Normalize** measures and money for the valid set (units → canonical via
   `v_unit_conversions`; amount → USD via `v_fx_rates`).
6. **Aggregate**: counts, per-category/per-region totals, focus rollups,
   rankings.
7. **Assign control codes** for the scoped ids (see §5).
8. **Decide certification** from the thresholds/gates in `case_scope`.
9. **Emit** one JSON object; nothing else.

## 3. Family playbooks

Full detail (with the confirmed edge cases and traps) is in
`references/reconciliation_playbook.md`. Summary:

### Contacts (partner onboarding, dealer/field-service rosters)
- **Merge key = normalized email only.** Normalize: NFKC → strip → lowercase;
  treat placeholder tokens (`""`, `n/a`, `none`, `null`, `unknown`, `-`) as
  missing. **Do not merge on phone, name, or `master_hint`** — shared
  "helpdesk" phone numbers are shared across many people, and
  `master_hint` values like `SHARED-HELPDESK` / `NOISY-*` are traps that must
  **not** cause a merge. Same-name/different-email rows are different people.
- **Field-level precedence** (different fields can come from different sources):
  - `canonical_name`: from the CERTIFIED "portal/HR-directory" source
    (typically snapshot `…-s01`), **title-cased** to a proper display name that
    preserves Unicode/accents. Report that source as `name_source_system`.
  - `email`, `phone`, `city`, `region/depot`, `consent`, and the master/survivor
    row: from the CERTIFIED source that carries `master_hint` (typically
    `…-s03`, e.g. "Compliance Master" / "Identity Registry").
  - `canonical_phone_digits` = **national digits only** (strip formatting; do
    **not** prepend a country code).
  - The PROVISIONAL source (CRM / Dispatch) often has deliberately wrong city
    values — never source location from it.
- **Quarantine** = a row with **no usable email and no usable phone**.
- `canonical_entity_count` **includes** quarantined people. `quarantine_rate`
  as defined by the contract (usually quarantined_rows ÷ canonical_entities,
  rounded to the stated dp).
- **Readiness**: an entity is *eligible* if ACTIVE and it has a usable email or
  phone; a channel is *ready* only if consent is GRANTED. Partition eligible
  entities into both / email_only / phone_only / not_ready. `dispatchable` =
  ACTIVE + usable channel + GRANTED consent. Depot partitions
  (dispatchable / blocked_consent / blocked_no_contact / blocked_inactive) must
  sum to the depot total.
- `resolution_outcome`: multi-source cluster → FIELD_LEVEL_PRECEDENCE_APPLIED;
  single row → SINGLE_SOURCE; contested (shared-helpdesk/identifier collision)
  → CONTESTED_NO_AUTOMERGE; no usable contact → NO_USABLE_CONTACT.

### Transactional (fuel purchases, freight charges)
- Dedup logical txn/charge by its id across snapshots (keep CERTIFIED).
- **Category resolution** from the description via `v_reference_aliases` in the
  matching domain: consider only aliases whose `reference_status = ACTIVE` **and**
  whose validity window covers the row's **business date**. Match `alias_text`
  as a **whole word/phrase**; when a longer matched phrase contains a shorter
  one, the **longest match wins** (e.g. "premium unleaded" beats "unleaded").
  0 canonical values → **unrecognized**; ≥2 distinct → **ambiguous**; exactly 1
  → **recognized**. Watch for near-miss traps (e.g. a word that merely contains
  an alias substring, or a not-yet-effective / retired alias).
- **Quarantine** = unrecognized OR ambiguous class OR non-positive measure
  (quantity/weight/distance ≤ 0). **Valid** = recognized class AND positive
  measures. **Mismatch** = valid AND recognized class ≠ expected class.
  **Exception** = mismatch OR quarantine (disjoint sets).
- **Normalized totals over the VALID set only**: convert measure via
  `v_unit_conversions.factor`; convert amount via `v_fx_rates` using the
  **CERTIFIED** `usd_per_unit` for the row's currency **on its business date** —
  **apply the rate to every currency, including USD** (do not shortcut USD to
  1.0). Sum exact values, then round to the contract's dp. Group by the
  **recognized** class.
- Rankings: order by the specified exposure/exception measure desc, id asc,
  limited to the stated count.

### Maintenance events
- Population = **union of snapshots, deduped by `event_id`, retained =
  CERTIFIED** (using certified-only under-counts and fails). Report the
  certified snapshot as authoritative; `authoritative_row_count` = its row
  count; `scoped_raw_row_count` = raw rows in scope.
- **Per logical event** integrity flags: missing timestamp (null/empty),
  invalid timestamp (unparseable, e.g. impossible month/day), invalid odometer
  (negative), negative labor (<0), extreme labor (gross outliers), odometer
  regression. `invalid_event_ids` = events failing time/odometer/labor validity
  (**not** regressions). `valid_event_count = logical − invalid`.
- **Odometer regression / distance**: per asset, order the valid events
  chronologically, convert odometer to km; a reading below the running max is a
  regression. `total_distance_km` = Σ over assets of (last − first reliable
  reading), rounded as specified. Regressions are reported in
  `corrected_metrics`, not in `invalid_event_ids`.
- `duplicate_groups`: each key present in >1 snapshot; `snapshot_ids` sorted;
  retained = certified.
- Certification obeys the **gate** in `case_scope` (e.g. any odometer
  regression → HOLD / BLOCK_AND_REMEDIATE).

## 4. Certification / close decision

Apply the thresholds, gates, and `status_action_map` from `case_scope`
literally. When thresholds are given (e.g. a max quarantine rate), compare the
computed metric and map status→action through the provided map. When only a gate
is given, the gate condition forces the failing status.

## 5. Opaque control codes

Contracts ask for short coded values (e.g. identity / outreach /
field-provenance codes for contacts; reference-policy / source-basis /
ledger-disposition codes for transactions; maintenance-source / history-route
codes for events). Their plain-text meanings are intentionally withheld; the
**allowed value set is the `enum` in the answer template**.

Do **not** guess blindly. Each code family maps **one enum value per underlying
condition**, and the scoped ids are chosen to span those conditions:

- **Identity** codes ↔ the entity's `resolution_outcome`
  (precedence-applied / single-source / contested / no-contact).
- **Outreach** codes ↔ the readiness bucket (both / email_only / phone_only /
  not_ready). The contract's readiness_partition object *is* the key: whatever
  code you place on each bucket there must match the code you give elsewhere for
  an entity in that bucket.
- **Field-provenance** codes ↔ how many/which sources supplied the surviving
  fields (single-source vs multi-source precedence).
- **Source-basis / retention** codes ↔ snapshot provenance of the retained
  record (certified-only / provisional-only / present-in-both).
- **Ledger-disposition / history-route** codes ↔ the entity's disposition
  (clean / mismatch / unrecognized / ambiguous / invalid-measure, or
  valid / invalid / regression).
- **Reference-policy** codes ↔ the alias's state at the cutoff
  (active-usable / not-effective (future or retired/inactive) / provisional).

Method: enumerate the distinct conditions present among the scoped ids, map each
condition to exactly one allowed enum value **consistently** across the whole
answer (the same condition always gets the same code), and keep the mapping
internally consistent with the readiness_partition / decision panels that pin
it. Codes are the least determinable part of these tasks; get everything else
exact first.

## 6. Output discipline (where easy points are lost)

- Emit **one JSON object, no prose/markdown**.
- Honor every `required` key and `additionalProperties:false`; add nothing extra.
- **Sort** exactly as each `description`/`x-ordering_rules` says (lexicographic
  id lists; ranked arrays by their sort keys). Dedup where `uniqueItems`.
- **Round** to the stated decimal places; respect `multipleOf`.
- Use only values from the allowed `enum`s and only stable ids that exist in the
  data or the case scope.
- Re-validate your object against `answer_template.json` before finishing
  (`scripts/hub_toolkit.py` has a `validate()` helper).

## 7. Traps checklist

- Placeholder strings (`n/a`/`none`/`null`/empty) are **missing**, not values.
- Shared phone numbers and `SHARED-HELPDESK`/`NOISY-*` hints must **not** merge
  identities; same name ≠ same person.
- Alias matching is whole-word + longest-wins; a not-yet-effective or
  retired/inactive alias is **not** usable even if its text appears.
- FX applies to **all** currencies (including USD); measures need unit
  conversion before summing.
- Quarantined rows are excluded from normalized totals but valid class
  **mismatches are included**.
- Contacts: name from the s01 source (title-cased), everything else from the
  master-hint (s03) source; phone is national digits.
- Maintenance: reconcile the **union** (not certified-only); regressions are
  reported separately from rejected/invalid events.
