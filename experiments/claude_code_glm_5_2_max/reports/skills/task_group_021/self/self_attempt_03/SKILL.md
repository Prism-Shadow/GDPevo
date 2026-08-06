---
name: asteria-fleet-dq-audit
description: Audit, reconcile, and certify an Asteria Fleet Data Quality Hub collection (fuel, freight, maintenance, or contacts family) against a case scope, then return ONE JSON object that conforms exactly to a supplied answer_template.json. Use when a task points at the Asteria Fleet Data Quality Hub at <TASK_ENV_BASE_URL>, stages payloads/case_scope.json + payloads/answer_template.json, and asks for a reconciliation / canonicalization / certification / close decision as strict JSON. Covers source-snapshot reconciliation, duplicate resolution, category/class mismatch + quarantine classification, unit + FX normalization, focus rollups, exception rankings, opaque Asteria control-code inference, and threshold-based certification status.
---

# Asteria Fleet Data Quality Hub — audit & certification

This skill executes a single, repeatable operating procedure distilled from five audit task
families (fuel, freight, maintenance, partner-onboarding contacts, field-service-roster contacts).
It produces **one JSON object** that conforms exactly to the task's `answer_template.json`.

The procedure is family-agnostic. The case scope and answer template are always the source of truth
for *what* to compute and *how* to shape the output; this skill supplies the *how to operate the hub*
and the *cross-cutting reconciliation rules*. Per-family specifics live in
`references/family_playbooks.md`; the hub API contract in `references/hub_api.md`; opaque control-code
inference in `references/control_codes.md`.

## 0. Contamination guard (run first)

Before reading anything, confirm `/work` contains only the expected material:
`environment_access.md` and `train_tasks/train_NNN/input/{prompt.txt, payloads/case_scope.json,
payloads/answer_template.json}` (plus this `skill/` package you are creating). If any other file,
unexpected payload, reference solution, or out-of-place material is present, **stop** and write
`contamination_report.txt` describing the unexpected material instead of producing a skill/answer.

## 1. Read the four inputs in this order

1. **`environment_access.md`** — the ONLY source of network access. It gives the base URL
   (`GDPEVO_ENV_BASE_URL`, substituted for `<TASK_ENV_BASE_URL>`), the `Authorization: Bearer …`
   credential, and the allow-list of endpoints. Never invent endpoints, credentials, or URLs.
2. **`prompt.txt`** — the business framing. It usually adds task-specific rules that override or
   sharpen the defaults (e.g. "a merchant exception is a mismatch OR a quarantine", "valid class
   mismatches DO enter normalized totals", "a channel is ready only when consent is granted",
   "do not include quarantined transactions in normalized totals"). Treat these as authoritative.
3. **`payloads/case_scope.json`** — the audit scope: `collection_id`, the cutoff
   (`business_cutoff` / `cutoff_at` / `as_of`), `base_currency`, canonical units, the focus items
   (assets / people / events / clusters with seed/anchor row IDs), the decision-ID lists
   (reference / transaction / charge / event IDs), ranking policy, `status_thresholds`,
   `status_action_map`, and any fixed certification gate.
4. **`payloads/answer_template.json`** — the **strict output contract**. It defines every required
   top-level key, per-field type/enum/pattern, array lengths, ordering rules (in `description`
   fields and/or an `x-ordering_rules` block), and numeric precision (`multipleOf`, decimal-place
   notes). `additionalProperties: false` is set throughout. This file is the final arbiter of
   output shape — read it completely before computing anything.

## 2. Discover the collection, snapshot, schema, and reference data

Use `environment_access.md` for all calls. Prefer the **`POST /api/query`** interface (SQL-like,
see `references/hub_api.md`) over the REST GET endpoints — every dataset, including snapshots,
aliases, conversions, and FX rates, is exposed as a queryable logical view.

- `GET /api/catalog/collections` (paginated `limit`/`offset`/`total`) → find the `collection_id`
  from the case scope; note its `family` and `source_systems`.
- `GET /api/catalog/schema` → the logical views (`v_contacts`, `v_fuel_transactions`,
  `v_freight_charges`, `v_maintenance_events`, `v_source_snapshots`, `v_reference_aliases`,
  `v_unit_conversions`, `v_fx_rates`) with exact field names/types/meanings. Use these column names
  in every query — do not guess field names.
- `v_source_snapshots` → snapshot metadata: `snapshot_id`, `snapshot_status`
  (`CERTIFIED`/`PROVISIONAL`/`STALE`), `business_cutoff`, `created_at`, `row_count`, `checksum`.
  Select the **authoritative snapshot** = the `CERTIFIED` snapshot whose `business_cutoff` matches
  (or is ≤) the case cutoff; if multiple certified snapshots qualify, take the one with the latest
  `created_at`/`ingested_at`. This snapshot resolves all overlapping logical records.
- `v_reference_aliases` (`domain`, `alias_id`, `alias_text`, `canonical_value`, `valid_from`,
  `valid_to`, `reference_status`) → maps source description text → canonical category/class.
- `v_unit_conversions` (`kind`, `from_unit`, `to_unit`, `factor`, `valid_from`/`valid_to`,
  `precision`) → unit factors for volume→L, weight→KG, distance→KM.
- `v_fx_rates` (`rate_date`, `currency`, `usd_per_unit`, `rate_status`, `published_at`) →
  currency→USD rates.

## 3. Pull ALL in-scope rows (pagination is mandatory)

The collection is **larger than a single response page** (the prompt and `approximate_record_count`
say so). Paginate with `LIMIT N OFFSET k` against the relevant view via `POST /api/query`, filtering
by `collection_id` AND the business-time field ≤ cutoff (use the schema's time field:
`purchased_at` / `service_date` / `event_time_raw` / `business_updated_at`, as appropriate). The
cutoff is an **inclusive** boundary.

The query response carries `{columns, row_count, rows, truncated}`. Check `truncated` on every
page: if `true`, the page was capped and you must continue paging. Stop when a page returns fewer
than `N` rows and `truncated` is false. A `SELECT COUNT(*)` first gives the expected total to size
the loop. Cross-check the row total against `approximate_record_count`.

## 4. Reconcile overlapping source records

A **logical record** is the real-world business entity (one fuel transaction / freight charge /
maintenance event / contact person). Multiple raw rows — across snapshots and `source_system`s —
often describe the same logical record.

- **Dedupe by the stable business key**: `transaction_id` (fuel), `charge_id` (freight),
  `event_id`+asset+time (maintenance), or contact identity (normalized email / digits-only phone /
  name+region). Rows sharing a key are ONE logical record.
- **Resolve overlaps with the authoritative snapshot**: the raw occurrence whose `snapshot_id`
  equals the authoritative snapshot is **retained**; every other occurrence is a duplicate (counted
  in `duplicate_raw_count`, never double-counted in logical/valid totals).
- If no authoritative occurrence exists for a key, apply a deterministic tie-break recorded in the
  case scope (`master_hint`, survivor rule) or fall back to earliest `ingested_at`. Always record
  the retained `snapshot_id` / `row_id` where the template asks for it.

## 5. Classify every logical record

Classify against the canonical reference data, then apply the template's definitions:

- **Valid** — resolves to exactly one canonical category/class and has valid physical measures.
- **Mismatch** — recognized category/class differs from the `expected_*` value on the row. Still a
  valid record for totals unless the prompt/template excludes it.
- **Unrecognized** — description/alias maps to **zero** canonical values.
- **Ambiguous** — maps to **more than one** canonical value.
- **Invalid quantity** — nonpositive or unparseable volume/weight/distance/labor/odometer.
- **Quarantine** — unusable record: unrecognized OR ambiguous OR invalid quantity (and, for
  contacts, a record with no usable email AND no usable phone).

**Totals rule (read the prompt each time):** quarantined records are **excluded** from normalized
totals but **counted** in quarantine/exception counts. Some families (freight) explicitly include
*valid class mismatches* in normalized totals; others count a mismatch as an exception while still
including the record. Follow the prompt's stated rule exactly — do not assume.

## 6. Normalize units and currency

- **Units**: convert each measure to the case scope's canonical unit (volume→`L`, weight→`KG`,
  distance→`KM`) using `v_unit_conversions.factor` where `from_unit`→`to_unit` and the row's date
  falls within `valid_from`/`valid_to`.
- **Currency**: convert `amount` to `USD` via `v_fx_rates`: `usd_amount = amount * usd_per_unit`.
  Use a `CERTIFIED` rate whose `rate_date` is ≤ cutoff (latest certified on or before the cutoff).
  Fall back to `PROVISIONAL` only if no certified rate exists for that currency as of the cutoff.
- **Round once, at the end**: sum raw converted values, then round the final aggregate. Per-row
  rounding drifts. Precision is per the template: money and physical measures → 2 decimals; rates
  (e.g. `quarantine_rate`) → 4 decimals (`multipleOf: 0.0001`); counts → exact integers.

## 7. Build rollups and rankings

- **Focus rollups**: for each focus item in the case scope (asset / person / event / cluster),
  compute exactly the metrics the template lists (logical/valid/mismatch/quarantine/exception
  counts, volume, spend, distance, survivor row, canonical email/phone/city/name, source systems).
- **Category / class / region / depot totals**: emit exactly one row per enum value declared in the
  template, sorted ascending by the key. Include zero-count enum values if the template requires a
  fixed-length array.
- **Rankings**: order by the case scope's primary sort (usually a count or USD-exposure descending),
  apply its tie-breaks (typically stable ID ascending), take the top-N (`merchant_ranking_limit` /
  `carrier_ranking_limit` / `asset_risk_ranking.limit`), and assign `rank` 1..N. Restrict ranking
  inputs to valid+quarantined records per the prompt's exception definition.

## 8. Infer the opaque Asteria control codes

The contract requires internal control codes for specific public IDs from the case scope:
`RB-`/`SB-`/`LD-` (fuel, freight), `FP-`/`IC-`/`OR-` (contacts), `MS-`/`HR-` (maintenance). Their
expansions are **intentionally not supplied** in the task materials. Infer each code from the shared
reference records + the reconciled audit evidence (reference policy from alias
`reference_status`/validity; source-basis from which snapshot/source retained the record; ledger
disposition from the valid/mismatch/quarantine outcome; identity/outreach/field-provenance from the
contact merge resolution). Each code **must** come from the template's allowed enum, one code per
requested ID, emitted in the case scope's sort order (usually ID ascending). See
`references/control_codes.md`.

## 9. Decide certification / close status

- Compute the gating metric per the case scope: typically `quarantine_rate = quarantined_rows /
  canonical_entities` (round to 4 decimals), or a regression/exception indicator.
- Apply `status_thresholds`: e.g. `pass_max_quarantine_rate` → `PASS`;
  `pass_with_exceptions_max_quarantine_rate` → `PASS_WITH_EXCEPTIONS`; above → `HOLD`. If the case
  scope fixes a gate (e.g. `odometer_regression_status: HOLD`), honor it directly.
- Map status → action via `status_action_map` (`PASS`→`RELEASE`,
  `PASS_WITH_EXCEPTIONS`→`REVIEW_EXCEPTIONS`, `HOLD`→`BLOCK_AND_REMEDIATE`).

## 10. Assemble and validate the output

- Return **one JSON object** conforming **exactly** to `answer_template.json`. No commentary, no
  Markdown, no trailing text.
- `additionalProperties: false` everywhere → include **only** the required keys, no extras, no
  `$schema`/`title` echoes.
- **Ordering**: follow the template's per-field rules — lexicographic ascending for ID lists;
  specified key sorts for arrays; `rank` ascending for rankings. Sources: field `description`s and
  any `x-ordering_rules` block.
- **Numeric precision**: exact integers; money/measures to 2 decimals; rates to 4 decimals.
- **Stable IDs only**: use IDs present in the public data or the case scope. Never invent IDs.
- **Self-validate** before returning: every required key present, enums/patterns satisfied, array
  lengths match `minItems`/`maxItems`, ordering correct, precision correct, no extra properties.
  A JSON-schema validator against `answer_template.json` is the safest final check.

## Cross-cutting invariants (never violate)

- Network access details come **only** from `environment_access.md`. Read-only: `GET` on listed
  endpoints and `POST /api/query` only. No writes, no other hosts.
- The cutoff is an **inclusive** boundary; rows at exactly the cutoff timestamp are in scope.
- Quarantined records are **excluded from normalized totals** but **counted** in quarantine and
  exception counts. Re-read the prompt for whether valid mismatches enter totals.
- The **authoritative snapshot** resolves every overlap; non-authoritative occurrences are
  duplicates, never re-counted as logical records.
- **Round once at the aggregate**, never per-row.
- Opaque control codes are **inferred from evidence**, never memorized or guessed outside the enum.
- Output is **strict JSON only**, ordered and precisioned exactly per the template.
