---
name: asteria-fleet-dq-reconciliation
description: >-
  Solve an Asteria "Fleet Data Quality Hub" reconciliation task. Use when a task
  gives you payloads/case_scope.json plus payloads/answer_template.json and asks
  you to reconcile overlapping source records from a read-only data hub (catalog,
  schema, SQL query, source-snapshot, contact/transaction/maintenance, and
  reference alias/conversion/fx interfaces) and return exactly one JSON object.
  Covers three task families: contact-master reconciliation, transaction
  normalization (fuel/freight), and maintenance-log integrity.
---

# Asteria Fleet Data Quality Hub — reconciliation tasks

## What these tasks look like
Each task ships two payloads and points at a shared read-only data hub:

- `payloads/case_scope.json` — the scope: `collection_id`, a business cutoff /
  as-of, the focus/anchor/decision IDs you must report on, and (sometimes)
  status thresholds or a certification gate + status→action map.
- `payloads/answer_template.json` — the answer contract: exact keys, enums,
  array lengths, ordering rules, and numeric precision. **This file is the
  spec. Read every field description, `enum`, `pattern`, `minItems/maxItems`,
  `multipleOf`, and ordering note before writing any code.**

Connection details (base URL and a read-only bearer token) are provided
separately in `environment_access.md`. Read them from that file at runtime;
never hardcode them. `references/hub_client.py` does this for you.

Deliver **one JSON object** matching the template exactly — no commentary, no
Markdown, no extra keys (`additionalProperties` is false in most contracts).

## Step 0 — orient
1. Read `case_scope.json` and the whole `answer_template.json`. List every
   output key and its ordering/rounding/enum constraints.
2. Discover the schema from the hub catalog before querying (do not assume
   column names). The hub exposes stable logical views: `v_contacts`,
   `v_fuel_transactions`, `v_freight_charges`, `v_maintenance_events`,
   `v_source_snapshots`, `v_reference_aliases`, `v_unit_conversions`,
   `v_fx_rates`.
3. Pull data through the hub's read-only SQL query interface with a body of the
   form `{"query": "SELECT ... FROM v_* WHERE collection_id='...'"}`. It is SQL
   over the views and supports `WHERE/GROUP BY/JOIN/aggregates`. **It truncates
   at 2000 rows** (a `truncated` flag tells you). Every single collection fits
   under that cap, so pull the whole collection in one query and reconcile in
   code. `sqlite_master`/DDL are blocked.

## Universal reconciliation model (all families)

**Snapshots & the authoritative source.** A collection has several snapshots in
`v_source_snapshots`, one per `source_system`, each with a `snapshot_status`
(`CERTIFIED` / `PROVISIONAL` / `STALE`), a `business_cutoff`, and a `row_count`.
The **authoritative snapshot is the CERTIFIED one**; its `snapshot_id` and
`row_count` are what "authoritative_*" fields want.

**Cutoff.** Keep rows whose *business date* (e.g. `purchased_at`,
`service_date`, event time) is `<=` the scope cutoff. Do **not** filter on
`ingested_at` — rows that landed in the hub after the cutoff are still in scope.

**Dedup → logical records.** The same logical entity (transaction/charge/event)
appears in more than one snapshot. Group by the stable business ID
(`transaction_id`, `charge_id`, `event_id`); the **retained/logical record is
the one from the authoritative (CERTIFIED) snapshot** (fall back to whatever
exists if it is not present there). Then:
- `raw_row_count` = in-scope raw rows across all snapshots.
- `logical_*_count` = distinct business IDs.
- `duplicate_raw_count` = raw − logical.
- A duplicate group reports the business ID, its snapshot IDs (sorted), the raw
  occurrence count, and the retained (certified) snapshot ID.
Confirm there are no cross-snapshot duplicates hiding under *different* business
IDs (same asset/time/type) before trusting the count.

**Reference tables.**
- `v_reference_aliases` (`domain`, `alias_text`, `canonical_value`, `valid_from`,
  `valid_to`, `reference_status`): map free text → a canonical category. Use only
  aliases that are `ACTIVE` **and** whose validity window covers the record's
  business date. Temporal traps exist: an alias can be `ACTIVE` yet not-yet-
  effective (future `valid_from`), and the in-window mapping can be flagged
  `INACTIVE`/`PROVISIONAL`.
- `v_unit_conversions` (`kind`, `from_unit`, `to_unit`, `factor`, `precision`):
  multiply by `factor` to reach the canonical unit (self-unit factor = 1).
- `v_fx_rates` (`rate_date`, `currency`, `usd_per_unit`, `rate_status`): prefer
  the `CERTIFIED` rate whose `rate_date` equals the record's business date;
  `usd = amount * usd_per_unit`; USD→USD = 1.

**Description → category matching (transaction families).** Tokenise the
description into lowercase alphanumeric tokens. Scan left to right taking the
**longest** contiguous alias-token subsequence that matches (so
`premium unleaded` beats bare `unleaded`; filler like `with liftgate accessorial`
is ignored). Match whole-token phrases, not raw substrings. Collect the distinct
canonical values:
- 0 → **unrecognized**;  ≥2 distinct → **ambiguous** (both quarantine).
- exactly 1 → **recognized** category (the "actual" class).

**Classification (transaction families).** For each logical record:
- `invalid_*` = a required physical measure is missing or ≤ 0 (quantity, weight,
  distance).
- **quarantined** = unrecognized OR ambiguous OR any invalid measure.
- **valid** = recognized-unique AND all required measures > 0.
- **mismatch** = *valid* AND recognized ≠ expected category. Mismatch is defined
  on valid records only (this matters).
- **exception** = mismatch OR quarantined.
- Invariants (verify them): `valid + quarantined = logical`; mismatch and
  quarantine are **disjoint** and their union size = the exception count;
  quarantine reason buckets are typically disjoint and sum to the quarantine
  count. `record_status` values like REVIEW/BILLED/POSTED are **not** an
  exclusion criterion.

**Normalized totals.** Sum over **valid** records only (quarantined excluded;
valid mismatches ARE included). Convert units and FX as above, group by the
**recognized** category, and round to the template's precision. Per-group counts
must sum to the overall valid count.

## Family specifics

### A. Contact-master reconciliation (people/orgs) — `v_contacts`
Columns include `row_id`, `source_system`, `email`, `phone`, `city`, `region`,
`consent_status`, `record_status`, `verified_flag`, `master_hint`. Typical
shape: N entities × several source systems, a block of no-contact rows, and a
block of identity edge-cases.

- **Normalise** email (NFKC, strip, lowercase; treat `''`, `none`, `null`,
  `n/a`, `nan`, … as empty; usable ⇔ has `@` and a dotted domain) and phone
  (digits only; usable ⇔ ≥ 7 digits).
- **Cluster** by usable email (primary). Phone is a valid **secondary** merge
  key **except shared identifiers**: a phone flagged
  `master_hint = SHARED-HELPDESK`, or any phone tied to ≥ 2 distinct emails,
  must NOT merge people (shared helpdesk line). **Name is never a merge key**
  (same name + different contact = different people). `NOISY-*` hint rows are
  isolated singletons — not merge signals.
- **Quarantine row** = no usable email and no usable phone.
- **`canonical_entity_count` / `canonical_person_count` INCLUDES quarantined
  (no-contact) rows as singleton entities.** Region/depot rollups also include
  them and must sum to the canonical count (strong self-check; the synthetic
  data tends to split evenly across regions).
- `duplicate/merged cluster count` = clusters with > 1 member.
- **Readiness / dispatch.** Eligible ⇔ `ACTIVE` and has a usable channel. A
  channel/person is "ready"/"dispatchable" only when consent is `GRANTED`.
  Produce whichever partition the template asks for — either
  dispatchable / blocked-consent / blocked-no-contact / blocked-inactive, or
  both / email_only / phone_only / not_ready — and make the buckets sum to the
  stated denominator.
- **Field-level precedence.** Different fields may come from different sources;
  the answer often reports a per-field `*_source_system` and a
  `resolution_outcome` (`SINGLE_SOURCE`, `FIELD_LEVEL_PRECEDENCE_APPLIED`,
  `CONTESTED_NO_AUTOMERGE`, `NO_USABLE_CONTACT`). Resolve each field from the
  highest-precedence source holding a usable value, and keep the choice
  consistent everywhere. **The exact per-field source authority (name vs contact
  vs depot vs consent) and the canonical-consent rule for a merged person are
  the hardest, least-obvious sub-problem** — pin them down from the focus/anchor
  probe rows the scope highlights rather than assuming a fixed order.
- **Contested identifier** watchlist case = the anchor row's usable identifier
  (e.g. phone) is shared across different people.

### B. Transaction normalization — fuel & freight
`v_fuel_transactions` / `v_freight_charges`. Apply the universal transaction
model. Fuel: volume→L, spend→USD. Freight: weight→KG, distance→KM, spend→USD,
and quarantine on non-positive weight or distance. Merchant/carrier rankings
order by an exposure/exception measure descending, then ID ascending, limited to
the scope's top-N, reporting per-entity component counts (mismatch / quarantine
/ exception).

### C. Maintenance-log integrity — `v_maintenance_events`
Columns include `event_id`, `asset_id`, `event_time_raw`, `odometer_value/unit`,
`labor_hours`.
- **Issue flags** on the retained record: missing timestamp (null/blank),
  invalid timestamp (unparseable), invalid odometer (null/negative), negative
  labor (< 0), extreme labor (> a full-day threshold, e.g. 24h).
- `invalid_event_ids` = the deduped union of those. `valid_event_count` =
  logical − invalid.
- **Odometer regression** = within an asset's *valid* events ordered by time, a
  reading below the previous one. Regressions stay **valid** and are reported
  separately (asset IDs + event IDs), not counted as invalid.
- **Corrected distance** = per asset (last − first reliable odometer, converted
  to km), summed across assets.
- **Asset risk ranking**: rejected-event count desc, then regression-event count
  desc, then asset ID asc.

## Status / certification decisions
- If the scope gives `status_thresholds` (e.g. a max quarantine rate for PASS vs
  PASS_WITH_EXCEPTIONS), compute the rate the template defines (e.g. quarantined
  ÷ canonical entities, rounded) and map status → `action` via the scope's
  `status_action_map`.
- If the scope gives a certification gate (e.g. "odometer regression ⇒ HOLD /
  BLOCK_AND_REMEDIATE"), apply it.
- When no threshold is supplied, the release/close decision is whatever the
  scope's rule implies — **derive it; do not assume.** Different tasks resolve to
  different statuses (some to HOLD when issues exist, some to PASS/RELEASE
  because exceptions are only flagged, not blocking).

## Opaque control-code panels
Some tasks ask for compact codes for scoped IDs — identity/outreach/field-
provenance (`IC-* / OR-* / FP-*`), reference-policy/source-basis/ledger-
disposition (`RB-* / SB-* / LD-*`), or maintenance-source/history-route
(`MS-* / HR-*`). Their expansions are intentionally withheld. Method:
1. Classify each scoped ID into its **data-derived disposition** — e.g. source
   basis (certified-only / provisional-only / both), disposition (valid /
   rejected / regression), alias `reference_status`, identity outcome
   (clean-merge / contested / no-contact / single-source), readiness bucket.
2. Assign one code per disposition, consistently, inside the family's allowed
   enum (`FIELD_PROVENANCE→FP`, `IDENTITY→IC`, `OUTREACH→OR`).
Getting the *structure* right (a distinct code per distinct disposition) is what
you can control; never emit one blanket code for every case.

## Output discipline (check before returning)
- Exactly the required top-level keys; nothing extra; no nulls where a value is
  required.
- Enums spelled exactly; IDs match their `pattern`; array lengths match
  `minItems/maxItems`.
- Every list ordered as specified (usually lexicographic/ascending; ranked
  arrays by their sort keys); dedup sets; sort `member`/`evidence` lists.
- Numbers rounded to the stated precision (`multipleOf`); integer fields integer.
- Self-consistency: `valid + quarantine = logical`; reason buckets sum to
  quarantine; region/class rollups sum to their totals; readiness buckets sum to
  their denominator.
- Emit only the JSON object — no prose, no Markdown fences.

See `references/pipeline.md` for a per-family checklist and
`references/hub_client.py` for a ready-to-use read-only query helper.
