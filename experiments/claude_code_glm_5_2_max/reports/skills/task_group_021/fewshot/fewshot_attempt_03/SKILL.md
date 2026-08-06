---
name: asteria-fleet-dq-certification
description: Execute an Asteria Fleet Data Quality Hub audit/certification task — reconcile overlapping source records over the network using environment_access.md, resolve canonical entities, classify quality issues, normalize units/currency, assign internal control codes, and emit one JSON answer that conforms exactly to the task's answer_template.json. Use whenever a task names the Asteria Fleet Data Quality Hub, references <TASK_ENV_BASE_URL> / environment_access.md, and asks for a reconciled audit plus a certification/release decision returned as a single JSON object (fuel, freight, maintenance, contact-master, or field-service-roster collections).
---

# Asteria Fleet Data Quality Hub — Audit & Certification

This skill executes any task in the Asteria Fleet Data Quality Hub family.
Every task is the same shape — only the collection, cutoff, focus items, and
output contract differ. Follow the procedure below; do not special-case a
domain unless its own task materials require it. Do not copy specific answers
from any prior task; re-derive everything from the current task's records.

## Inputs (read in this order)

1. `prompt.txt` — the business narrative: which collection/cutoff to audit,
   what to reconcile, what to report, and any domain-specific rule.
2. `payloads/case_scope.json` — scoped parameters: `collection_id`, the cutoff
   (`business_cutoff` / `cutoff_at` / `as_of` / `business_period`), focus
   items (clusters / people / assets / decision-panel IDs), ranking policies,
   certification thresholds, and the `status_action_map`.
3. `payloads/answer_template.json` — the **authoritative output contract**. It
   is a JSON Schema (or field-contract) listing every required key, enum,
   `minItems`/`maxItems`, regex pattern, and numeric precision. Treat it as
   ground truth for shape, ordering, and rounding.
4. `environment_access.md` — the **only** source of runtime connection info:
   the base URL, the bearer credential, and the allowed endpoint list. Read
   these at runtime; do not hardcode them.

## 0. Input hygiene

Confirm the staged task directory contains only the expected files
(`prompt.txt`, `payloads/case_scope.json`, `payloads/answer_template.json`,
and the environment-access file). If anything unexpected is present, stop and
report it (write a contamination report) instead of proceeding.

## 1. Connect to the hub

Use **only** the endpoints listed in `environment_access.md`, with the
documented `Authorization` header. Substitute the file's base URL for
`<TASK_ENV_BASE_URL>`. The hub exposes a collection catalog, schema,
source-snapshot metadata, the domain record endpoints, reference tables
(aliases / conversions / fx), and an authenticated `POST /api/query` for
scoped/paged retrieval. See `references/hub_endpoints.md`.

## 2. Discover collection, schema, snapshots

- Resolve the `collection_id` from `case_scope.json` in the catalog.
- Read the schema to learn field names for this collection type.
- From source-snapshot metadata, identify the **authoritative snapshot**
  (status `CERTIFIED`; id conventionally `<collection_id>-certified`) and
  confirm it covers the cutoff. Reconcile against this snapshot.

## 3. Retrieve scoped records

Pull raw rows from the domain endpoint and/or `POST /api/query`. Collections
are larger than one page — paginate until exhausted. Keep every raw row
tagged with its snapshot id. Load the reference tables you will need:
aliases (category/service-class resolution), conversions (unit
normalization), and fx (currency normalization).

## 4. Reconcile overlapping sources → logical entities

- Group raw rows into logical entities by stable logical id.
- Collapse cross-snapshot duplicates; **retain the authoritative-snapshot
  occurrence** (report `retained_snapshot_id` = authoritative id where the
  contract asks for it).
- Apply the business cutoff: keep only records at or before the cutoff
  timestamp (and within `business_period` when given).
- Count: `raw_row_count`, logical count, `duplicate_raw_count`
  (= raw − logical), valid count (= logical − quarantined).

## 5. Classify quality issues & quarantine

Driven by the answer_template's issue buckets and the narrative. Typical
classifications: expected-vs-recognized category/service-class **mismatch**;
**unrecognized** (zero canonical alias) and **ambiguous** (>1 alias); invalid
quantities (nonpositive volume/weight/distance, invalid odometer, missing or
invalid timestamp, negative/extreme labor, odometer regression). Quarantine
unusable records and **exclude them from normalized totals**. Valid class
mismatches are *not* quarantined — they stay in totals and feed rankings. See
`references/reconciliation_workflow.md`.

## 6. Normalize

- Units → canonical unit declared in `case_scope.json` (`L`, `KG`, `KM`, …)
  via `/api/reference/conversions`.
- Currency → base currency (`USD`) via `/api/reference/fx`.
- Round to the precision declared in the answer_template (usually 2 dp;
  `quarantine_rate` is 4 dp). Counts are exact integers.

## 7. Resolve canonical entities (contact / people tasks)

- Merge duplicate clusters; pick a survivor/master id per the precedence
  implied by the records (commonly the highest row id in the cluster).
- Choose each canonical field from its source system by field-level
  precedence (e.g. city from the compliance source, name from HR, contact
  and consent from the identity registry) — **infer precedence from the
  evidence**, do not assume it.
- Channel readiness: an entity is **eligible** when active with ≥1 usable
  email or phone; a channel is **ready** only when consent is granted.

## 8. Assign internal control codes

For every focus decision, anchored control case, and decision-panel id listed
in `case_scope.json`, assign the applicable code(s) from the
`answer_template.json` enums. Code families: identity `IC-*`, outreach `OR-*`,
field-provenance `FP-*` (contact/master); reference-policy `RB-*`,
source-basis `SB-*`, ledger-disposition `LD-*` (financial transactions);
maintenance-source `MS-*`, history-route `HR-*` (maintenance logs).

The codes are **opaque compact identifiers whose expansions are intentionally
not supplied** in the task materials. Infer each code from the shared records
and the reconciled audit (the record's source system, alias-resolution
outcome, quarantine reason, mismatch type, snapshot basis, consent/record
status, etc.). Use the hub's reference data and `/api/query` to tie each
evidence condition to its code. Never use a value outside the contract enum,
and never copy a code→id mapping from memory — derive it for this task's
records. See `references/control_codes.md`.

## 9. Certification / release decision

- Compute `quarantine_rate` = quarantined ÷ canonical entities (4 dp).
- If `case_scope.json` declares a `certification_gate`, honor it directly.
- Else if it declares `status_thresholds` + `status_action_map`, apply the
  thresholds to the quarantine rate to pick the status.
- Else let the audit's material findings drive the status (unresolved
  category/quantity issues → `HOLD`).
- Pair status with action via the `status_action_map`
  (`HOLD`→`BLOCK_AND_REMEDIATE`, `PASS`→`RELEASE`,
  `PASS_WITH_EXCEPTIONS`→`REVIEW_EXCEPTIONS`).

## 10. Rankings & rollups

Build any requested rankings (merchants / carriers / assets / depots) using
the sort policy in `case_scope.json` (e.g. exception_count DESC then id ASC;
mismatch_spend_usd DESC then carrier_id ASC) and the stated limit. Build
regional/depot rollups grouped by the declared key field, with partition
counts that sum to the total where the contract requires it.

## 11. Emit the answer

Return **exactly one JSON object** conforming to `answer_template.json`:
- every required key present, no extra keys (`additionalProperties: false`);
- every list ordered and deduplicated exactly as the contract specifies
  (lexicographic / ascending by stable id; ranked arrays by rank);
- enums, regex patterns, `min/maxItems`, and numeric precision all honored;
- no commentary, no Markdown, no trailing text.

## 12. Self-check

Before returning, re-validate the object against `answer_template.json`:
required keys, enum membership, item counts, id patterns, ordering, and
rounding. Fix any drift, then emit. See `references/output_contract.md`.
