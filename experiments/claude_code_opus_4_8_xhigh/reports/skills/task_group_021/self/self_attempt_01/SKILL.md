---
name: asteria-fleet-data-quality-hub
description: >-
  Solve Asteria Fleet Data Quality Hub reconciliation-and-certification tasks.
  Use whenever a task points at the "Fleet Data Quality Hub" / a
  <TASK_ENV_BASE_URL> with endpoints like /api/catalog, /api/source-snapshots,
  /api/contacts, /api/transactions/{fuel,freight}, /api/maintenance/events,
  /api/reference/{aliases,conversions,fx}, and /api/query, and asks for one JSON
  object (matching payloads/answer_template.json) reconciling overlapping source
  records as of a business cutoff and returning quality counts, canonical/
  survivor decisions, rollups/rankings, opaque control codes, and a
  certification/status decision. Covers contact-master certification, contact-
  readiness rosters, fuel/freight normalization audits, and maintenance-log
  integrity — all variants of the same pipeline.
---

# Asteria Fleet Data Quality Hub — reconciliation & certification

Every task in this family is the **same pipeline over a different collection and
output contract**. Recognize it, run the pipeline, then bend the output to the
exact `answer_template.json` in front of you. Do not invent numbers: every value
must be derived from the live hub as of the scoped cutoff.

## 0. Inputs you are always given

- `payloads/case_scope.json` — the *only* source of scope: collection id, the
  business cutoff / as-of / period, focus items (clusters, assets, events,
  people, charges, transactions), anchored control cases with pinned evidence
  rows, ranking limits and tie-breaks, canonical units / base currency,
  status thresholds and a status→action map.
- `payloads/answer_template.json` — the output contract (usually JSON Schema,
  sometimes a `field_contract` document). It is authoritative for keys, enums,
  array cardinality (`minItems`/`maxItems`), ordering, rounding, and
  `additionalProperties:false`. **Read it last-mile and satisfy it literally.**
- `environment_access.md` — the **only** thing that grants network access: the
  base URL (`*_BASE_URL=...`) and an `AUTHORIZATION: Bearer <token>` header,
  plus the list of allowed endpoints. Send the auth header on every request.

Never hardcode a token, base URL, count, or code mapping from a previous task —
they change per task. Read them fresh at runtime.

## 1. Connect and discover (never assume the API shape)

Use `scripts/asteria_client.py` (stdlib-only) to read `environment_access.md`
and make authenticated calls, or replicate its logic. Before pulling data:

1. `GET /api/catalog/collections` — confirm the scoped `collection_id` exists
   and learn its domain/metadata.
2. `GET /api/catalog/schema` — learn the **real field names and types** for
   rows, snapshots, and reference tables. Do not guess field names from this
   skill; the schema is ground truth.
3. `GET /api/source-snapshots` — snapshot metadata: ids, status
   (e.g. CERTIFIED / PROVISIONAL / STALE), timestamps, coverage.
4. Inspect one page of the domain endpoint and one `POST /api/query` response to
   learn the pagination envelope and the query request/response shape, then
   adapt `get_all()` / `query()` accordingly. Collections span **multiple
   pages** — page to exhaustion; never reason from a truncated first page.

Endpoints seen in this family (subset appears per task):
`/api/catalog/collections`, `/api/catalog/schema`, `/api/contacts`,
`/api/transactions/fuel`, `/api/transactions/freight`,
`/api/maintenance/events`, `/api/reference/aliases`, `/api/reference/conversions`,
`/api/reference/fx`, `/api/source-snapshots`, `POST /api/query`.

## 2. The reconciliation pipeline (shared spine)

Run these stages in order; every task uses a subset, described in its prompt.

**A. Scope & pull.** Restrict to the scoped `collection_id`. Pull *all* raw rows
across snapshots (paginate). `raw_row_count` = in-scope raw source rows
(including cross-snapshot duplicates).

**B. Cutoff filter.** Keep only rows whose business/effective date is `<=` the
scoped cutoff / as-of / within the period. Use the business-date evidence the
prompt names, not ingestion time.

**C. Authoritative snapshot & de-duplication.** Rows overlap across snapshots.
Choose the authoritative snapshot from snapshot metadata (prefer certified/
current status and the latest as-of within cutoff — verify the rule from the
schema/metadata, don't assume). Collapse raw rows into **logical entities**
(logical transaction / charge / event / person / contact) by their stable
business key. For each duplicate group the **retained** occurrence comes from the
authoritative/retained snapshot. Report `duplicate_raw_count = raw − logical`
and, where required, per-group `snapshot_ids` (sorted) + `retained_snapshot_id`.

**D. Normalize.** Depending on domain:
- Text/contacts: canonical name (Unicode-preserving), email = trimmed NFKC
  **lowercase**, phone = **digits only** (kept as a string), canonical city,
  canonical region/depot value.
- Fuel/freight: resolve descriptions/aliases to a **recognized canonical
  category/class** via `/api/reference/aliases`; convert quantities to the
  canonical unit via `/api/reference/conversions`; convert money to the base
  currency via `/api/reference/fx` using the applicable business-date rate.
- Maintenance: convert odometer/labor to declared units; reconstruct per-asset
  history ordered by reliable timestamp.

**E. Classify: valid vs mismatch vs quarantine.** Quarantine = a row that cannot
enter normalized totals. Reason families observed:
- `unrecognized` — no recognized category/alias match.
- `ambiguous` — matches more than one category/alias.
- `invalid_quantity` / `invalid_weight` / `invalid_distance` — non-positive or
  out-of-range physical measure.
- `no usable contact channel` — no usable email or phone (contacts/roster).
- maintenance rejects — missing/unparsable timestamp, invalid odometer range,
  negative or extreme labor.
A **mismatch** (expected category/class ≠ recognized category/class) is still a
**valid** record: it counts in normalized totals and is flagged separately.
**Quarantined rows are excluded from all normalized totals; valid mismatches are
included.** An "exception" is a distinct logical record that is a valid mismatch
*or* is quarantined.

**F. Canonical resolution & survivors.** Group logical entities that are the same
real-world entity (identity resolution). Pick a survivor / `master_id` (a real
public row id) and build canonical field values. When sources disagree per
field, apply **field-level source precedence** (discover the precedence order
from schema/reference — e.g. CRM vs Compliance Master vs Partner Portal, or
HR Directory vs Dispatch vs Identity Registry) and record which source won each
field. Entities with genuinely conflicting identity evidence on a watchlist are
**contested → not auto-merged** (`CONTESTED_NO_AUTOMERGE`). `member_row_ids` is
the deduplicated, lexicographically-sorted set of contributing public row ids.

**G. Rollups, rankings, readiness.**
- Rollups (region/depot, fuel_type, service_class): one row per represented
  value from the contract's enum, canonical-entity/charge counts, sorted
  ascending by the key.
- Rankings (merchant / carrier / asset): sort by the primary metric **descending**
  then the declared tie-breaks (usually id ascending); truncate to the scope's
  limit; assign `rank` from 1.
- Readiness (contacts/roster): an entity is **readiness-eligible** only when it
  is **active AND retains at least one usable email or phone**. A channel is
  **ready only when consent is granted**. Partition eligible entities into
  mutually exclusive buckets (`both` / `email_only` / `phone_only` / `not_ready`)
  that sum to the eligible count. "Dispatchable" = active + usable channel +
  consent granted; blocked reasons (consent / no-contact / inactive) partition
  the depot total.

**H. Control codes (opaque; expansions withheld on purpose).** See §3.

**I. Certification / status.** Compute the gate metric — usually
`quarantine_rate = quarantined_rows / canonical_entities`, rounded to 4 dp — and
apply the scope's thresholds: at-or-below `pass_max` → `PASS`; else at-or-below
`pass_with_exceptions_max` → `PASS_WITH_EXCEPTIONS`; else `HOLD`. Honor any
**hard gate** the scope names (e.g. any odometer regression forces HOLD /
BLOCK_AND_REMEDIATE) — a hard gate overrides the rate. Map status → action with
the scope's `status_action_map` (typically PASS→RELEASE,
PASS_WITH_EXCEPTIONS→REVIEW_EXCEPTIONS, HOLD→BLOCK_AND_REMEDIATE).

**J. Assemble & self-check.** Build the object to the contract, then run §4.

## 3. Assigning the opaque control codes

Codes like `IC-25/40/70/90`, `OR-15/35/60/80`, `FP-20/55/75`, `RB-17/42/83`,
`SB-24/61/79`, `LD-14/31/53/72/88`, `MS-12/47/86`, `HR-19/33/74` are **labels for
categorical reconciliation outcomes** within a family (identity, outreach/
readiness, field-provenance, reference-basis, source-basis, ledger-disposition,
maintenance-source, history-route). Their plain-language expansions are
**deliberately not provided** — you must infer the mapping from the data, not
memorize it. Method:

1. **Count the outcomes.** The enum size = number of distinct outcomes to
   distinguish (e.g. FP/RB/SB/MS/HR have 3; IC/OR have 4; LD has 5). Derive that
   many categorical outcomes from your reconciliation for that family.
2. **Use built-in calibration.** When the contract pairs a code family with
   *named* categories, that pairing reveals the family's semantics — e.g. a
   `readiness_partition` object that asks for an OR code per
   `both/email_only/phone_only/not_ready` bucket tells you OR codes label
   readiness states; solve the 1:1 assignment from that. Anchored control cases
   (pinned evidence rows in the scope) exist precisely to let you tie a known
   reconciliation outcome to its code.
3. **Cross-check with the hub.** Look for a signal in the records, reference
   tables, or `/api/query` results that separates the outcomes; assign codes so
   the observable ordering/partition is consistent.
4. **Be internally consistent.** The same outcome always maps to the same code,
   everywhere in the answer. Do not assume the numeric suffix implies severity or
   order unless the evidence shows it.

## 4. Output contract compliance (do this before returning)

The contract — not this skill — is authoritative. Verify each:

- **Shape:** every required key present; no extra keys (`additionalProperties:
  false` / `additional_top_level_keys_allowed:false`). Objects/arrays nested
  exactly as specified.
- **Cardinality:** arrays with `minItems`/`maxItems` (or a `length`) have exactly
  that many items — one row per requested focus item / rollup enum value / scope
  id, no more, no fewer.
- **Ordering:** apply each list's stated rule (usually lexicographic ascending by
  id; rankings by metric desc then tie-break). Set membership is deduplicated.
- **Enums:** every enum-typed value is one of the allowed literals (statuses,
  actions, source systems, categories, control codes).
- **Rounding / precision:** money/volume/weight/distance to 2 dp; rates to 4 dp;
  honor `multipleOf`. Counts are exact integers. Phone stays a **string** of
  digits.
- **Ids:** use only stable public ids present in the data or supplied in the
  scope; match id `pattern`s.
- **Partitions add up:** mutually-exclusive count groups sum to their stated
  total (readiness buckets, depot dispositions).
- **Consistency:** e.g. `dispatchable_person_count` == length of
  `dispatchable_master_ids`; `duplicate_raw_count` == raw − logical;
  quarantine_rate == quarantined / canonical (rounded).
- **Return one JSON object only** — no Markdown, no commentary, no code fences.

## 5. Cross-cutting reminders

- Discover, don't assume: field names, pagination, snapshot-selection rule, and
  precedence order all come from the live catalog/schema/metadata.
- Reconcile *as of the cutoff*; ignore rows and rate versions outside it.
- Quarantined rows never enter normalized totals; valid mismatches always do.
- Recompute derived counts from your own reconciled set — never copy a count the
  API reports for a different scope.
- Keep every derivation deterministic so the same inputs always yield the same
  answer.

See `references/task-family-map.md` for how each observed task variant maps onto
this pipeline, and `scripts/asteria_client.py` for the authenticated client.
