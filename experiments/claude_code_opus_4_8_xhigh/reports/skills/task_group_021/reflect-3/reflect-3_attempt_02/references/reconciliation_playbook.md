# Reconciliation playbook (detailed)

Read this alongside `../SKILL.md`. It records the concrete edge-case handling
that these audits require. It contains **method only** — no answer values. Derive
every number from the live data of the task you are solving.

## Discovery order

1. `catalog/collections` → confirm the target `collection_id`, its `family`, and
   its `source_systems`.
2. `catalog/schema` → confirm view and field names before writing SQL.
3. `v_source_snapshots` filtered to the collection → list snapshots, their
   `source_system`, `snapshot_status`, `business_cutoff`, `created_at`,
   `row_count`. The **CERTIFIED** snapshot is authoritative. Several collections
   have exactly one CERTIFIED + one PROVISIONAL snapshot; contacts collections
   often have three source systems (two CERTIFIED, one PROVISIONAL).

## Normalization primitives

- **Text**: NFKC-normalize, strip surrounding whitespace, collapse internal runs
  if the field is a display string. Placeholder set treated as *missing*:
  `{"", "n/a", "na", "none", "null", "unknown", "-"}` (case-insensitive).
- **Email**: normalized text → lowercase. Missing if placeholder/empty.
- **Phone digits**: keep digits only. For a canonical contact value use the
  **national** number (do not synthesize/keep a country code). Note that the
  same person's phone appears in different formats across sources (with/without
  country code, punctuation), so **phone is not a reliable merge key**.
- **Display name**: title-case while preserving accented characters
  (Python `str.title()` on an NFKC string does this).

## Contacts (identity resolution)

- Rows repeat one logical person once per source snapshot. The clean multi-source
  clusters share a normalized email exactly; the harder rows are single-source.
- **Merge only on normalized email.** After treating placeholders as missing,
  group by email. Rows with no usable email are their own (usually quarantined)
  entities.
- Reject these merge traps explicitly:
  - a phone number shared by many distinct emails (a shared desk line);
  - `master_hint` values `SHARED-HELPDESK` and `NOISY-*`;
  - identical names with different emails.
- **Field-level survivorship** (per field, take the highest-precedence source
  that has a usable value):
  - name → the s01 CERTIFIED "portal/HR directory" source, then title-case;
  - email / phone(national) / city / region(depot) / consent / master row →
    the s03 CERTIFIED source that carries `master_hint`;
  - never take city/region from the PROVISIONAL source (its cities are wrong).
- **Counts**: `raw_row_count` = scoped raw rows; `canonical_entity_count` =
  resolved people **including** quarantined ones; `duplicate_cluster_count` =
  clusters with >1 row; `quarantine_row_ids` = rows with no usable email and no
  usable phone; `quarantine_rate` per the contract's definition and rounding.
- **Readiness**: eligible = ACTIVE ∧ (usable email ∨ usable phone). Among
  eligible: both / email_only / phone_only require GRANTED consent; otherwise
  not_ready. `dispatchable` = eligible ∧ GRANTED. Depot buckets
  (dispatchable, blocked_consent = active+channel+non-granted,
  blocked_no_contact = no usable channel, blocked_inactive = inactive+channel)
  partition the depot total.
- **Contested identifier cases** = watchlist anchors whose identity is contested
  (shared-helpdesk / shared identifier) and therefore not auto-merged.

## Fuel & freight (transactional)

- Business date = the row's service/purchase date (date part).
- **Alias resolution** (per row description):
  1. candidate aliases = same domain, `reference_status = ACTIVE`, validity
     window covers the business date;
  2. an alias matches if `alias_text` occurs as a **whole word/phrase** in the
     lowercased description;
  3. drop any matched alias whose text is contained in a longer matched alias
     (**longest match wins**);
  4. distinct `canonical_value`s of survivors → 1 = recognized (that class),
     0 = unrecognized, ≥2 = ambiguous.
  Traps: descriptions where an alias appears only as a substring inside a longer
  word (not a real match); descriptions naming two classes (ambiguous); aliases
  that are not-yet-effective (future `valid_from`) or retired
  (`INACTIVE`/expired) at the cutoff.
- **Disposition** of a logical row:
  - invalid measure = quantity/weight/distance ≤ 0 (or null);
  - quarantine = unrecognized ∨ ambiguous ∨ invalid measure;
  - valid = recognized ∧ all required measures > 0;
  - mismatch = valid ∧ recognized class ≠ expected class;
  - exception = mismatch ∨ quarantine (disjoint).
- These usually form a clean partition of the logical rows — verify the
  sub-counts sum to the logical count.
- **Normalized totals (valid only)**: measure × conversion factor; amount ×
  CERTIFIED `usd_per_unit`(currency, business date). Apply FX to every currency
  including USD. Sum exact, round at the end; group by recognized class.
- **Ranking** (merchant/carrier): by the specified exposure/exception measure
  desc, id asc, top-N; per-entity mismatch and quarantine sub-counts.

## Maintenance

- **Population = union of snapshots, deduped by `event_id`, retained =
  CERTIFIED.** (Certified-only is wrong — it under-reports.) Duplicate rows
  usually differ only in a status field; data fields are identical.
- **Timestamp parsing**: accept ISO forms; a value that is null/empty is
  *missing*; a value that will not parse (impossible month/day/time) is
  *invalid*. Both exclude the event from the odometer history.
- **Per-event integrity flags** (computed on the logical/deduped event):
  missing_timestamp, invalid_timestamp, invalid_odometer (odometer < 0),
  negative_labor (< 0), extreme_labor (gross high outliers — inspect the labor
  distribution; there is a clear cluster of extreme values well above the
  normal range), odometer_regression.
- `invalid_event_ids` = events failing timestamp/odometer/labor validity.
  Regressions are **not** invalid — they are sequence findings reported in
  `corrected_metrics`.
- **Regression & distance**: per asset, order valid events by (time, id),
  convert odometer to km; a reading below the running maximum is a regression
  (its event/asset go into the regression sets). `total_distance_km` =
  Σ_assets (last − first reliable reading), rounded per contract.
- **Duplicate groups**: `event_id` in >1 snapshot; `snapshot_ids` sorted
  lexicographically; retained snapshot = certified.
- **Asset risk ranking**: by rejected-event count desc, then the tie-breaks in
  `case_scope` (e.g. regression-event count desc, asset id asc), top-N.

## Control-code assignment (structural)

The numeric/opaque values are environment constants you must infer; the answer
template's `enum` lists the whole allowed set for each family. Assign by
condition, consistently:

| family (typical) | key dimension → one code per value |
|---|---|
| identity | resolution_outcome: precedence-applied / single-source / contested / no-contact |
| outreach | readiness bucket: both / email_only / phone_only / not_ready |
| field-provenance | survivor provenance: single-source vs multi-source precedence |
| source-basis / retention | snapshot provenance: both / certified-only / provisional-only |
| ledger / history-route | disposition: clean / mismatch / unrecognized / ambiguous / invalid-measure (or valid/invalid/regression) |
| reference-policy | alias state at cutoff: active-usable / not-effective(future or retired) / provisional |

The scoped id lists are deliberately built to cover each condition once, and the
in-answer partition objects (readiness_partition, decision panels) are internal
anchors — keep every code consistent with them. Because the plain-text meanings
are withheld and there is no feedback at test time, this is the highest-risk
part: nail the deterministic fields first, then assign codes by consistent
condition-mapping.

## Self-check before emitting

- Sub-counts reconcile (valid + quarantine buckets = logical; depot buckets =
  depot total; focus/region rollups sum to their parents).
- All arrays sorted/deduped as the contract's descriptions require.
- All numbers rounded to the stated precision; every enum value is allowed.
- The object validates against `answer_template.json` and contains no extra keys.
