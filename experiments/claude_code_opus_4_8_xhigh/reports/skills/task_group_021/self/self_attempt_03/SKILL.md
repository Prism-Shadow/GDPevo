---
name: asteria-fleet-dq-reconciliation
description: >-
  Solve Asteria "Fleet Data Quality Hub" reconciliation and certification cases.
  Use whenever a task points at a shared Fleet Data Quality Hub at <TASK_ENV_BASE_URL>
  with payloads/case_scope.json + payloads/answer_template.json and asks you to
  reconcile overlapping source snapshots as of a business cutoff and emit one strict
  JSON object. Covers all four record families: contacts (onboarding / roster /
  contact-master), fuel purchases, freight charges, and maintenance events —
  including source reconciliation, alias/unit/FX normalization, quarantine, dedup
  and survivorship, channel readiness, opaque control-code panels, and the
  certification/close status + action decision.
---

# Asteria Fleet Data Quality Hub — reconciliation & certification

A single reusable workflow. Every case in this family gives you a `case_scope.json`
(what to compute) and an `answer_template.json` (the exact output contract), and asks
you to reconcile overlapping source records from a read-only data hub and return **one
JSON object and nothing else**. The record family varies (contacts / fuel / freight /
maintenance) but the machinery is the same.

> Do not put task-specific answer values in your reasoning ahead of the data. Derive
> every number, ID, and code from the live hub for the collection in scope.

## 0. Recognize & set up

You are in this family when the prompt names the **Asteria Fleet Data Quality Hub** at
`<TASK_ENV_BASE_URL>`, references `payloads/case_scope.json` + `payloads/answer_template.json`,
gives a **business cutoff / as-of**, and asks for reconciled quality counts + a
certification/close decision in strict JSON.

1. **Read both payloads in full first.** `case_scope.json` gives the `collection_id`,
   the cutoff, the focus/anchor/decision IDs, ranking limits, thresholds, and the
   status→action map. `answer_template.json` is the binding contract (JSON Schema or a
   field contract): required keys, `additionalProperties:false`, enums, `minItems`/
   `maxItems`, ordering rules, and numeric precision. **Build to the contract, not to
   your memory of a sibling task.**
2. **Get runtime access from `environment_access.md` only.** It supplies the base URL and
   an `Authorization: Bearer <token>` header (environment-specific, e.g. `asteria-read-021`).
   Read them at runtime; never hardcode.
3. **Use only stable IDs** present in the hub data or supplied in `case_scope.json`.
4. Output is **JSON only** — no Markdown, no commentary, no code fences.

See `references/hub_api.md` for the full endpoint/query/DSL cheatsheet and reference
constants. See `references/playbooks.md` for the per-family detail, the control-code
inference method, and the output-validation checklist. The steps below are the spine.

## 1. Discover the collection and its snapshots

- `GET /api/catalog/collections` → find the target `collection_id`; note its `family`
  and `source_systems`. (Do not confuse look-alike collections, e.g. `..._2026_01` vs
  `..._2026_03`, or a `quotes`/`archive` collection.)
- `GET /api/catalog/schema` → the logical view + fields for that family.
- `GET /api/source-snapshots?collection=<collection_id>` → every snapshot with its
  `snapshot_status` (CERTIFIED / PROVISIONAL / STALE), `source_system`, `business_cutoff`,
  and `row_count`. This is the reconciliation surface.

## 2. Query engine (how you actually read data)

`POST /api/query` with body `{"query":"SELECT ... FROM <view>"}` — SQLite-flavored SQL
over the views (`WHERE`, `GROUP BY`, `ORDER BY`, `COUNT`, `SUM`, `DISTINCT`, `LOWER`,
`TRIM`, …). **Responses cap at 2000 rows and set `"truncated": true` when there is more.**
For collections larger than a page, either aggregate server-side (`GROUP BY`/`COUNT`/`SUM`)
or paginate with `LIMIT/OFFSET` over a stable sort — never assume one page is the whole
collection. Reference endpoints need a filter param (`?collection=`, `?kind=`, `?domain=`);
a bare call returns `400 invalid filter`.

## 3. Scope rows and reconcile snapshots

1. **Scope**: restrict to the target `collection_id` and the business window. Transactions
   and events are filtered by their **business date** field against the cutoff/period
   (`purchased_at`, `service_date`, `event_time_raw` within `business_period`); contact
   rosters typically scope to **all collection rows** as of the cutoff (`population_scope`).
   Report `raw_row_count` = in-scope raw source rows.
2. **Authoritative snapshot**: prefer `snapshot_status` **CERTIFIED > PROVISIONAL > STALE**,
   then recency (`business_updated_at` / `ingested_at` / `created_at`). Only count
   snapshots created on/before the `as_of`. Report the CERTIFIED snapshot's id/row_count
   where the contract asks for `authoritative_snapshot_id` / `authoritative_row_count`.
3. **Overlap / duplicates**: one logical entity (`transaction_id` / `charge_id` /
   `event_id` / person) may appear in several snapshots. `duplicate_raw_count` = raw rows −
   logical entities. **Retain the occurrence from the authoritative snapshot**; record the
   retained snapshot per the contract.
4. **Contacts differ**: the per-source-system snapshots are **merged**, not one-picked —
   cluster rows into canonical people (§4b), don't drop a whole snapshot.

## 4. Normalize transactions (fuel / freight / maintenance)

- **Category recognition via aliases** (`v_reference_aliases`, `domain` = `fuel`/`freight`):
  normalize the description (trim + lowercase) and match `alias_text` among aliases
  **effective at the business date** — `reference_status = ACTIVE` and
  `valid_from ≤ date ≤ (valid_to or open)`. **0 matches → unrecognized**; **>1 distinct
  `canonical_value` → ambiguous**; both are quarantine conditions. Exactly one → the
  recognized canonical category. (Watch aliases that are PROVISIONAL, INACTIVE, expiring,
  or future-dated — they change what is recognized at a given cutoff.)
- **Mismatch**: recognized category ≠ the row's `expected_*` class. A mismatch is still a
  **valid** charge — it enters normalized totals and counts as an exception/exposure.
- **Units**: convert `quantity`/`billed_weight`/`distance`/`odometer_value` to the
  canonical unit via `v_unit_conversions` (`?kind=volume|weight|distance|odometer`),
  multiplying by `factor` for `from_unit → to_unit`. Non-positive / null physical measures
  → quarantine (`invalid_quantity` / `invalid_weight` / `invalid_distance`).
- **Currency**: convert `amount` to USD via `v_fx_rates` — the rate for the row's
  `currency` on its business date, `rate_status` CERTIFIED preferred, latest
  `published_at`. USD is 1.0.
- **Totals rule**: **quarantined rows are excluded** from normalized totals; **valid
  mismatches are included**. Round to the contract's precision (usually 2 dp).

## 4b. Canonicalize contacts

- **Identity keys**: normalized email (trim → NFKC → lowercase) and normalized phone
  (digits only). Cluster rows sharing a key across source systems.
- **Survivorship / field-level precedence**: choose each canonical field
  (name/email/phone/city/region/consent/record_status) by source-system precedence +
  `verified_flag` + recency; `master_hint` (`MH-####`) may name the master row. Report the
  winning **source system per field** where the contract asks.
- **Quarantine**: a person with **no usable email and no usable phone** →
  `NO_USABLE_CONTACT`.
- **Resolution outcomes**: `SINGLE_SOURCE`, `FIELD_LEVEL_PRECEDENCE_APPLIED`,
  `CONTESTED_NO_AUTOMERGE` (identifier conflict blocks automerge), `NO_USABLE_CONTACT`.
- **Readiness**: an entity is eligible only when **ACTIVE and has ≥1 usable email or
  phone**; a **channel is ready only when consent is GRANTED**. Partition eligible
  entities into `both / email_only / phone_only / not_ready`, and by depot into
  `blocked_consent` (active + usable + non-granted), `blocked_no_contact`,
  `blocked_inactive`. Partition counts must sum to the totals the contract states.

## 5. Quality metrics, control codes, certification

- Compute every scoped count the contract names (raw / logical / duplicate / valid /
  mismatch / unrecognized / ambiguous / invalid / quarantine, plus `quarantine_rate` over
  the exact denominator the contract specifies, at the stated precision).
- **Opaque control-code panels** (IC / OR / FP / RB / SB / LD / MS / HR …): the code
  expansions are intentionally withheld. Infer each code as a deterministic function of the
  record's **reconciled condition**, using the family cardinality (number of allowed
  values = number of buckets) and the **anchor/control cases in `case_scope.json`** to
  calibrate the bucket→code binding. Full method in `references/playbooks.md`.
- **Certification / close status**: apply the thresholds and status→action map from
  `case_scope.json` **exactly** (e.g. `PASS→RELEASE`, `PASS_WITH_EXCEPTIONS→REVIEW_EXCEPTIONS`,
  `HOLD→BLOCK_AND_REMEDIATE`); honor hard gates such as an odometer-regression HOLD. Do not
  invent thresholds.

## 6. Assemble, validate, emit

- Include exactly the required keys, nothing more (`additionalProperties:false`). Honor
  every enum, `minItems`/`maxItems`, `uniqueItems`, and ordering rule (lexicographic /
  by-id ascending / ranked with the documented tie-breaks). Dedupe and sort each list.
- Apply numeric precision precisely: integers exact; floats rounded to the stated decimals
  (`multipleOf: 0.01` → 2 dp).
- **Self-check invariants** before returning: `raw = logical + duplicates`; partition
  counts sum to their totals; each scoped focus/anchor/decision ID appears exactly once in
  its panel; every array length matches the contract. Recompute a couple of aggregates with
  a second `GROUP BY` query to catch pagination gaps.
- Return the single JSON object. Nothing else.
