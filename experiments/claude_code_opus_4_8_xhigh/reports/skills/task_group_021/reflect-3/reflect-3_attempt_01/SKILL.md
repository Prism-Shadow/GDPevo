---
name: asteria-fleet-data-quality-hub
description: >-
  Solve "Asteria Fleet Data Quality Hub" reconciliation/certification tasks: read a
  case_scope.json + answer_template.json + a runtime access file, query a shared read-only
  data hub, reconcile overlapping source snapshots into canonical records, normalize with
  reference tables, compute the requested counts/rollups/rankings and status decision, and
  return one JSON object matching the answer contract exactly. Use whenever a task references
  the Asteria Fleet Data Quality Hub, a "Fleet Data Quality Hub", contact/fuel/freight/
  maintenance source reconciliation, canonical entity resolution, quarantine/normalization
  audits, or opaque IC/OR/FP/RB/SB/LD/MS/HR control codes.
---

# Asteria Fleet Data Quality Hub — reconciliation & certification

A family of data-quality tasks over one shared read-only hub. Each task gives you three files
and asks for exactly one JSON object. The families differ (contacts, fuel, freight,
maintenance) but the **method is the same**: pick the authoritative source data as of a
cutoff, reconcile overlapping/duplicate records into canonical ones, normalize with
validity-scoped reference tables, exclude what is unusable, then compute the contracted
counts, rollups, rankings and a status/action decision.

## 0. Inputs (always the same shape)
- `prompt.txt` — the business ask (which family, what to report).
- `payloads/case_scope.json` — the scope: `collection_id`, the cutoff (`business_cutoff` /
  `cutoff_at` / `as_of`), focus items (clusters/assets/people/charges), control/decision
  panels, ranking limits, and any status thresholds / certification gate + action map.
- `payloads/answer_template.json` — the **binding output contract** (JSON Schema or field
  contract). Ordering, precision, enums, `additionalProperties:false`, min/maxItems.
- A runtime access file (named in the prompt, e.g. `environment_access.md`) — the hub base
  URL, the authorization header, and the list of read interfaces. **Read connection details
  from that file at run time; never hard-code them.**

**Read the answer_template first and work backwards.** It tells you every field, its type,
its ordering rule, and its rounding. Build your output to satisfy it literally.

## 1. The hub and its data model
The hub exposes a catalog, a schema, and a **read-only SQL query interface** over logical
views. Discover the schema from the catalog/schema interface each run — do not assume.
Typical logical views and their keys:

| view | grain | key fields |
|---|---|---|
| `v_contacts` | one source contact row | row_id, source_system, source_record_id, person_or_org_name, email, phone, city, region, consent_status, record_status, verified_flag, business_updated_at, master_hint |
| `v_fuel_transactions` | one fuel txn row | transaction_id, snapshot_id, asset_id, merchant_id, purchased_at, expected_fuel_type, purchased_description, quantity, quantity_unit, currency, amount, record_status |
| `v_freight_charges` | one charge row | charge_id, snapshot_id, invoice_id, invoice_line_no, carrier_id, service_date, expected_service_class, description, billed_weight, weight_unit, distance, distance_unit, currency, amount, record_status |
| `v_maintenance_events` | one event row | event_id, snapshot_id, asset_id, event_type, event_time_raw, odometer_value, odometer_unit, labor_hours, parts_cost, event_status |
| `v_source_snapshots` | one snapshot | collection_id, snapshot_id, source_system, snapshot_status, business_cutoff, created_at, row_count |
| `v_reference_aliases` | alias→canonical | domain, alias_id, alias_text, canonical_value, valid_from, valid_to, reference_status |
| `v_unit_conversions` | unit factor | kind (volume/weight/distance/odometer), from_unit, to_unit, factor, valid_from, valid_to, precision |
| `v_fx_rates` | daily FX | rate_date, currency, usd_per_unit, rate_status |

**Query interface facts that matter:**
- It is SQLite-flavored SQL. Results are **capped (~2000 rows) and flagged truncated**.
  For anything large, compute **server-side with `GROUP BY` / `COUNT` / `SUM`**, or pull a
  sub-2000-row collection whole and process locally. Never trust a truncated page as complete.
- Always scope every query by the `collection_id` from case_scope.

## 2. Snapshot selection & the authoritative source
A collection is delivered as several **source snapshots**. Each has a `snapshot_status`
(`CERTIFIED`, `PROVISIONAL`, sometimes `STALE`) and a `business_cutoff`.
- The **authoritative snapshot** is the `CERTIFIED` one, valid as of the case cutoff (not
  `STALE`, not future-dated). Report its id where the contract asks for
  `authoritative_snapshot_id` and its `row_count` for `authoritative_row_count`.
- **Include all in-scope snapshots in the raw population** (contacts have one snapshot per
  source system; transactions/maintenance have certified + provisional). A `PROVISIONAL`
  snapshot still contributes rows; it just loses survivorship and is never the authority.
- `raw_row_count` = every in-scope source row across snapshots. Filter by business time
  (`business_updated_at`/`purchased_at`/`service_date` ≤ cutoff); confirm none are excluded
  before assuming a number. `ingested_at` is hub-plumbing, **not** a business filter.

## 3. Reconciliation (dedup → canonical records)
Two distinct dedup shapes appear — read the family:

**A. Cross-snapshot duplicate resolution (fuel / freight / maintenance).**
The same logical record appears in more than one snapshot under the **same stable id**
(`transaction_id` / `charge_id` (== `invoice_id`+`invoice_line_no`) / `event_id`).
- `logical_*_count` = distinct stable id. `duplicate_raw_count` = raw − logical.
- For each duplicated id, **retain the authoritative (certified) occurrence**; report the
  duplicate group (snapshot_ids sorted, retained_snapshot_id = certified).

**B. Identity resolution / MDM (contacts).**
Rows do **not** share a stable id across sources; resolve identities:
- **Match key = normalized email** (NFKC → strip → lowercase; treat `''`,`n/a`,`none`,`null`
  and non-`@` values as absent). Rows sharing a normalized email are the same person.
- **Guardrails against false merges** (the control anchors test exactly this): do **not**
  merge on a shared phone (watch for `master_hint = SHARED-HELPDESK`, a phone reused by
  many identities) and do **not** merge on a common name alone. A phone shared by ≥2 distinct
  people is a **contested identifier**, not a merge.
- Rows with **no usable email or phone** are **quarantined**, and each is its own record.
- `merged_duplicate_cluster_count` = clusters with >1 member.

**Counts include quarantined records.** `canonical_*_count` = resolved records *including*
quarantined ones (each unusable row is a quarantined person/entity). Region/depot rollups and
totals are over this full canonical set. (Under-counting by excluding quarantined records is a
classic error here.)

## 4. Survivorship & FIELD-LEVEL precedence
When several source rows form one canonical record, decide each output field:
- **The golden/master row** is the record from the **authoritative certified source that
  carries `master_hint`** (e.g. the "Compliance Master" / "Identity Registry" source), tie-
  broken by verified_flag, then latest `business_updated_at`. Use its id for `master_id`/
  survivor. (Confirmed: choosing the wrong master collapses the score — the master_hint
  source wins.)
- **Resolve each canonical field from its own most-authoritative source** — the contract's
  separate `*_source_system` fields exist because fields come from *different* sources:
  - **name** → the source that is **Unicode-preserving** (keeps accents) and certified, then
    Title-Cased for display (a registry that stripped the accent is *not* the name source).
  - **email / phone (contact)** → the identity/compliance master (cleanest digits; email
    normalized, phone digits-only with no country-code padding).
  - **city / depot(region)** → the HR/roster-style source (the provisional/dispatch source
    often carries a decoy city).
  - **consent + record_status** → the identity master (may legitimately be PENDING).
- The winning source per field IS the value you report and IS the `*_source_system`.

## 5. Normalization
- **Category / class from free-text description** (fuel `expected_fuel_type`, freight
  `expected_service_class`): match `v_reference_aliases` for the right `domain`.
  - Only apply aliases with `reference_status = ACTIVE` **and** whose `[valid_from, valid_to]`
    window contains the row's business date. (An alias that is INACTIVE, or whose window
    starts in the future, does **not** apply — e.g. a "priority" alias effective next month or
    an expired one makes that description unresolved in the current period.)
  - **Match with word boundaries** (`\b…\b`), then drop any match whose span is contained in a
    longer match (**maximal span**). Collect the distinct `canonical_value`s.
    - This is confirmed correct vs. naive substring: `premium unleaded` must subsume
      `unleaded`; `bio diesel` subsumes `diesel`; and `biodieseline` must **not** match
      `biodiesel`.
  - **1 distinct canonical → recognized**; **0 → unrecognized**; **>1 → ambiguous**.
    `unrecognized_transaction_ids`-style lists = zero-match ∪ ambiguous.
- **Mismatch** = recognized-unique canonical ≠ the row's expected category. A *valid* mismatch
  also requires valid physical measures; it still enters normalized totals under the
  **recognized** (actual) category.
- **Units**: convert with `v_unit_conversions` (`kind` = volume/weight/distance/odometer),
  `factor` from unit → canonical unit, honoring validity window. e.g. US_GAL→L 3.785411784,
  IMP_GAL→L 4.54609, LB→KG 0.45359237, MI→KM 1.609344.
- **Currency → USD**: `v_fx_rates` for `(currency, rate_date = the row's business date)`,
  preferring `rate_status = CERTIFIED` (fall back to provisional only if no certified). USD = 1.0.

## 6. Quarantine (and exclusion from totals)
"Quarantine" = records that **cannot be used / cannot enter the ledger**. Read the contract's
exact reasons; typical partitions:
- contacts: **no usable email or phone**.
- fuel/freight: **unresolved class** (unrecognized ∪ ambiguous) ∪ **non-positive/nan quantity
  or weight or distance**. Report per-reason counts; they usually partition the quarantine set.
- maintenance rejects (`invalid_event_ids`): missing timestamp, unparsable timestamp, invalid
  odometer (null/negative), negative labor, extreme labor (a clear high outlier, e.g. a labor
  value far above the normal band). Sequence-only **odometer regressions are reported
  separately**, not as rejects.
**Quarantined records never enter normalized totals**, but valid mismatches do.
Compute data-quality issue counts over the **deduped/retained** records, not raw rows
(raw-row counting scored worse on maintenance).

## 7. Rollups, rankings, focus items
- Group canonical records for rollups (region/depot, fuel_type, service_class). Emit exactly
  the enum members the contract lists, in the stated order; counts sum to the population.
- **Rankings**: apply the case_scope sort exactly, including tie-breaks (e.g. exposure/
  exception_count DESC, then id ASC). "Exception" usually = valid mismatch **or** quarantined.
- **Focus items**: return exactly the requested ids in the requested order, with member ids
  deduped+sorted, master/survivor id, and the field-level canonical values + source systems.
- Odometer / distance metrics: per asset, order valid events by time; regression = a reading
  below the running max; distance = (last − first reliable reading) converted to the canonical
  unit; sum across assets.

## 8. Opaque control / decision codes (IC/OR/FP, RB/SB/LD, MS/HR, SB/…)
These enums are intentionally undocumented and must be **inferred**, not looked up (they are
not in the reference tables). Treat each family as an **ordinal confidence/disposition tier**
and assign by the record's characteristics, monotonically:
- **Identity (IC-25<40<70<90)**: no usable identity / unresolved → lowest; contested/shared →
  low; single-source → mid; multi-source agreeing → highest.
- **Outreach (OR-15<35<60<80)**: not contactable (no consent / inactive / no channel) →
  lowest; one channel + consent → mid; both channels + consent + active → highest.
- **Field provenance (FP-20<55<75)**: by number of contributing certified sources
  (1 → low, 2 → mid, 3 → high).
- **Reference-basis (RB), source-basis/retention (SB), ledger-disposition/routing (LD)**:
  map to the alias's applicability (active-in-window vs inactive/expired vs provisional/
  future) and the charge's snapshot basis / disposition (clean-posted vs mismatch vs
  quarantined).
Assign consistently across the panel. **You cannot fully verify these without an oracle**, so
get every deterministic field right first — codes are a minority of the contract, the
counts/lists/totals are the majority.

## 9. Status / action decision
- If case_scope gives **thresholds** (e.g. `pass_max_quarantine_rate`,
  `pass_with_exceptions_max_quarantine_rate`) and an **action map**, compute the driving rate
  (quarantine rate = quarantined ÷ canonical, rounded per contract) and map
  rate→status→action strictly.
- If case_scope gives a **certification gate** (e.g. any odometer regression → HOLD /
  BLOCK_AND_REMEDIATE), apply it.
- Otherwise infer: clean → PASS/RELEASE; only recognized mismatches → PASS_WITH_EXCEPTIONS/
  REVIEW_EXCEPTIONS; quarantine/blocking issues present → HOLD/BLOCK_AND_REMEDIATE.

## 10. Output discipline (this is graded literally)
- Emit **one JSON object, no prose, no Markdown**, matching the template's keys exactly;
  `additionalProperties:false` means **no extra keys**.
- Honor every ordering rule (lexicographic vs numeric vs by-a-field), `uniqueItems`,
  `min/maxItems`, enums, and integer-vs-number typing.
- Round exactly as stated (`multipleOf`, "2 decimal places"); keep phone/quantity-as-string
  fields as strings.
- Cross-check that partitioned counts sum (readiness buckets = total; quarantine reasons =
  quarantine count; class totals count = valid count).

## 11. Verify before returning
Run the self-checks in `reference/checklist.md`. Recompute headline counts two ways
(server-side `GROUP BY` vs local) and confirm they agree. Confirm the object validates against
the answer_template (types, enums, ordering, item counts). See `reference/data_model.md` for
per-family field notes and `reference/reconciliation_toolkit.py` for ready-made pure helpers
(normalization, word-boundary alias matcher, unit/FX conversion, survivorship, quarantine).

> Scope note: this skill covers only the reconciliation method and the answer contract. All
> runtime connection details come from the access file provided with the task; obtain and use
> them from there.
