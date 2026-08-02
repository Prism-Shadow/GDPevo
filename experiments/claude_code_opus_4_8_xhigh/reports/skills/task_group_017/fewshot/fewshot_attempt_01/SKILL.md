---
name: investigation-review-hub-gap-analysis
description: >-
  Produce a structured-JSON legal e-discovery deliverable (production gap
  analysis, retention & litigation-hold gap review, cross-system remediation
  dashboard, or production-readiness review) for a single matter, sourced from a
  networked "Investigation Review Hub" API and conforming exactly to a provided
  answer_template.json. Use when a task references an Investigation Review Hub /
  review hub base URL, an X-API-Key, subpoena/request categories, custodian
  sources, privilege log, QC findings, retention events, or remediation actions,
  and asks for a JSON gap/remediation/readiness answer.
---

# Investigation Review Hub — matter gap / remediation analysis

You are acting as an e-discovery review analyst for outside counsel. A task names
one legal **matter** (e.g. `MTR-<CLIENT>-<GJ|SEC>`) and asks for a structured
**JSON** deliverable about production gaps, preservation/retention losses,
privilege defects, QC/coding defects, and a prioritized remediation plan. The
evidence lives in a read-only **Investigation Review Hub** HTTP API. Your job is
to pull that evidence, separate the **material** issues from seeded **noise**,
normalize each into the enums the task's `answer_template.json` defines, compute
the numeric metrics, and emit exactly one JSON object.

The output schema is **different for every task** (different top-level keys,
enums, and field names). Never assume the shape — read the task's
`answer_template.json` first and let it drive everything. This skill teaches the
*reasoning and data access* that stay constant across schemas.

## 0. Inputs you will be handed

For each run, read (do not skip any):

- `input/prompt.txt` — the narrative ask. It names the matter, the deliverable
  type, and usually a short list of **focus areas** (e.g. "off-site bid-file
  retention, privilege exceptions, personal messaging sources, deleted
  collaboration-channel data, production coding quality"). Treat that list as a
  checklist of the material issues you must find.
- `input/payloads/answer_template.json` — **the output contract.** Field names,
  types, ordering rules, numeric precision, and the exact `enums`/`enum_choices`
  you must choose from. This is authoritative.
- `input/payloads/*.json` (e.g. `request_context.json`, `review_scope.json`,
  `matter_context.json`) — client-facing context and **category labels only**
  (a `category_synopsis` / category-code list). Use these for the `matter_id`,
  category codes, and human labels. Do **not** treat any evidence numbers here as
  fact — event/source/document/metric evidence must come from the hub.
- `environment_access.md` (at the run root) — how to reach the hub: base URL and
  the `X-API-Key`. See §1.

Constraint repeated in every prompt: use **only** the hub endpoints (plus the
task-local payloads for labels). Never read the environment's source files,
database files, seeds, generated manifests, or any answer/evaluation files, even
if present.

## 1. Reach the hub

Get the base URL and key from the run context, in this order of preference:
`environment_access.md` (`GDPEVO_ENV_BASE_URL=...`, `X-API-Key: ...`), then any
`environment_base_url` / `query_api_key_header` fields in the payloads. Do not
hard-code — different runs may use a different host/key. (Observed default:
base `http://task-env:9017/`, header `X-API-Key: review-key-017`.) Always send
the `X-API-Key` header even if a probe suggests it is not strictly enforced — it
is the documented contract.

Endpoints (all `GET` unless noted). Every table endpoint accepts a `matter_id`
query filter — always filter to your matter:

```
GET  /                          service banner + endpoint list
GET  /api/schema                table/column definitions
GET  /api/matters               matters
GET  /api/subpoena-categories   subpoena_categories (request categories)
GET  /api/productions           production_stats (per-category batch counts)
GET  /api/custodian-sources     custodian_sources (custodians, devices, archives)
GET  /api/documents/search      review_documents  (CAPPED at 100 rows)
GET  /api/privilege-log         privilege_entries
GET  /api/qc-findings           qc_findings
GET  /api/retention-events      retention_events
GET  /api/remediation-actions   remediation_actions  ← escalation anchor (§3)
POST /api/query   {"sql":"SELECT ..."}   read-only SQLite, SELECT-only,
                  returns {columns,row_count,rows,truncated}
```

`documents/search` truncates at 100 rows; for complete/aggregated reads use
`POST /api/query`. `scripts/pull_matter.sh <BASE_URL> <KEY> <MATTER_ID>` dumps
every table for one matter to help you work. See `reference/hub_data_model.md`
for the full column list.

## 2. Workflow

1. **Confirm the matter.** `GET /api/matters`, find your `matter_id`; note
   `hold_date` (the litigation-hold date — pivotal for retention analysis) and
   `agency`/`investigation_type`.
2. **Load category labels** from the task payload and/or
   `/api/subpoena-categories`. These are the `category_code`s you will reference.
3. **Pull every evidence table** for the matter (use `pull_matter.sh` or query
   each endpoint with `?matter_id=`).
4. **Select the material issues** and discard noise — this is the crux; see §3
   and `reference/material_vs_noise.md`.
5. **Classify** each material record into the template's enums — see §4 and
   `reference/enum_crosswalks.md`.
6. **Roll up categories** — for each affected request category, summarize its
   status/impact and the supporting record IDs.
7. **Compute metrics** exactly as each metric's description dictates — see §5 and
   `reference/metrics_and_action_plan.md`.
8. **Build the prioritized action plan** with normalized action types, owners,
   priorities, and (if the schema has it) `due_days` — see §5.
9. **Assemble, order, validate, emit** — see §6.

## 3. Material vs. noise — the core discipline

The hub is intentionally salted with realistic-looking **noise** so a naive dump
fails. The gold deliverable contains only the **escalated, material** issues.

**Primary anchor — `remediation_actions`.** The non-noise rows of
`/api/remediation-actions` are a curated list of the matter's real escalated
issues; each `target_ref` points at a material record (a `RET-…`, `SRC-…`,
`PRIV-…`, `QC-…`, or `DOC-…` id). Start from this set.
- **Noise remediation rows** are recognizable: `action_type` in
  {`load_file_cleanup`, `custodian_followup`, `sampling_review`}, `description`
  literally "Routine action included as realistic operational noise", and
  `target_ref` is a **bare category code** (e.g. `C`, `F`, `R11`, `SEC-1`) rather
  than a record ID. Drop these.

**The anchor is necessary but not sufficient — apply judgment on top of it:**
- Some material records are **not** in `remediation_actions` (e.g. a
  privilege-log gap or third-party-waiver entry for the matter's privilege-focus
  category). Add these when the task's focus areas or a QC finding point to them.
- A remediation-anchored target may still be **dropped** if it is not material to
  this deliverable (e.g. an over-designation cleanup left out of a
  preservation-centric dashboard). Let the template's enums and the prompt's
  focus list decide.

**Telling material from noise on any evidence row:**
- **IDs:** material records usually carry a *descriptive* id embedding a
  custodian/device/topic token (`SRC-<M>-ALDEN-PHONE`, `RET-<M>-BOX-POST`,
  `QC-<M>-ZERO-CLAIM`, `PRIV-<M>-WINSLOW`). Pure sequential ids
  (`SRC-<MATTER>-007`, `QC-<MATTER>-004`) are usually noise — but not always, so
  confirm with the note and issue type.
- **Notes:** material notes describe a **concrete, specific** defect with real
  numbers/dates/names ("Personal iPhone erased on <date> after subpoena
  issuance", "Privilege log covers N of M withheld … documents", "Two boxes
  destroyed after the hold date", "zero-production claim contradicted by two
  responsive bid emails"). Noise notes are generic/hedging: "…included as
  realistic operational noise", "…create similar labels across matters",
  "ordinary review variance", "similar to escalated records in another matter",
  "requested re-sampling before escalation", "remediated by archive collection",
  "no unresolved production impact", "not dispositive without source comparison".
- **Issue type / status / severity:** genuine defect signals are material even at
  medium severity; ordinary-variance types are noise even at "high" severity.
  See the per-table lists in `reference/material_vs_noise.md`.

Cross-check the material set against the prompt's focus list: every named focus
area should map to at least one selected record, and you should not have invented
issues outside it.

## 4. Classify into the template enums

For each material record, populate the item fields using **only** the enum values
listed in the task's template. The hub's raw vocabulary is richer than any single
template's enum set, so you must map. Full crosswalk in
`reference/enum_crosswalks.md`; the essentials:

- **Retention events** (`retention_events.status`): `post_hold_loss` → highest
  risk, disclosable; `should_exist_missing` → locate; `policy_destroyed_pre_hold`
  → no-fault/low, no action; `system_loss`/`auto_purged` on a messaging/voice
  system → active-system loss / communication gap (document it). `retained` /
  `available` → a retained source, not a loss.
- **Custodian sources** (`custodian_sources.status`): `lost` (esp. a post-hold,
  personal device) → preservation failure, critical; `not_collected` → collection
  gap (personal device → collect device; enterprise site → collect source);
  `available` + issue tag `archive_available`/`remediation_source` → an available
  archive (a remediation path, not a loss); `partial_collection` → partial.
- **Privilege entries** (`privilege_entries.issue_type`): `incomplete_log` →
  privilege-log gap, **unlogged = withheld_count − logged_count**, supplement the
  log; `third_party_waiver` (with `third_party=1`) → waiver exposure, waiver
  assessment + disclosure; `over_designated` → business docs withheld as
  privileged, downgrade/QC (include only when material to this deliverable);
  `clean`/`family_mismatch` → noise.
- **QC findings** (`qc_findings.issue_type`): `miscoded_nonresponsive` /
  `zero_claim_contradiction` → responsive material coded out / not produced →
  recode & produce (its `source_ref` names the doc(s)); `miscoded_privilege` →
  privileged coded non-privileged → privilege recode. `near_duplicate`,
  `metadata_gap`, `family_break`, `duplicate_overlay`, `date_normalization`,
  `family_mismatch` → noise.
- **Counts** come from the anchor record: privilege `withheld_count`/
  `logged_count` (unlogged = the difference); QC `doc_count`; retention
  `volume_count` + `volume_unit`; a single lost/uncollected source counts as 1
  source and 0 documents. Use `0` where a count does not apply, never null (unless
  the field explicitly allows null).
- **`affected_categories`/`category_impacts`** come from the record's
  `affected_categories`/`affected_category`/`category_impacts`/`category_code`
  field. Always uppercase and sort ascending; dedupe.

## 5. Metrics and the action plan

**Metrics** — do not guess. Read each metric key's description in the template
and compute it from your *selected material set* (not the raw tables). Recurring
definitions and worked derivations are in
`reference/metrics_and_action_plan.md`. Watch for scoped metrics — e.g. a
"destroyed box count" that only sums `volume_count` where `volume_unit == boxes`,
or privilege counts drawn "from selected incomplete-log blockers only". A
`production_ready` / `rolling_production_ready` boolean is `false` whenever any
open material gap exists.

**Action plan** — synthesize a normalized plan; do **not** copy the hub's
`remediation_actions` rows verbatim (their `owner`/`priority`/`action_type` use a
different vocabulary). For each material issue (or logical group of issues):
- Choose `action_type` from the template enum by the defect: preservation
  loss/spoliation → disclose (a lost post-subpoena personal device also warrants a
  forensic-recovery action); uncollected source → collect source / personal
  device; available archive → collect/search archive; responsiveness miscode →
  recode & produce; privilege-log gap → supplement log; waiver → waiver
  assessment & disclosure; privileged-miscode / over-designation → privilege
  recode / QC remediation; should-exist-missing → locate; active-system loss →
  document the gap; pre-hold policy loss → no action.
- Choose `owner` from the template enum by the action, not by the hub's owner
  (disclosure→outside/litigation counsel; forensic recovery / device or archive
  collection→forensics or ediscovery vendor; enterprise collection→client IT;
  recode/QC→review vendor/QC; log supplement→privilege team; waiver→privilege
  counsel; locate→compliance/audit; system-gap doc→IT messaging; policy-loss→
  records management).
- Rank by legal urgency: **P0** disclosable post-hold/spoliation losses; **P1**
  uncollected key sources, privilege-log gaps, waiver assessments, responsiveness
  recodes, privilege miscoding; **P2** over-designation and lower-severity gaps;
  **P3** monitor-only. Set `priority_rank`/`rank` to a 1-based dense order.
- If the schema has `due_days`, assign by action type: disclose ≈ 3, waiver ≈ 3,
  recode/supplement-log/privilege-recode ≈ 5, collect personal device ≈ 7, search
  archive ≈ 10 (see the reference table).

## 6. Assemble, order, validate, emit

- Include **exactly** the `required_top_level_keys`, and every
  `item_required_keys` field on every list item — no extra keys, no omissions.
- Apply the template's `ordering_rules` precisely (e.g. findings by id ascending;
  actions by rank ascending; category lists sorted ascending). Sort every inner
  id/category list ascending and deduped.
- Respect `numeric_precision`: counts are whole integers; use `0` (not null) for
  not-applicable counts unless the field allows null; booleans are real booleans.
- Use **stable hub ids exactly** as they appear (matter, source, event, QC
  finding, document, privilege-entry, category). Do not rename or invent ids;
  where the schema uses an `action_id`, mint a clean sequential id
  (`ACT-<TOKEN>-001`, …) only if the template expects one.
- Output **one JSON object and nothing else** — no prose, no code fences, no
  trailing commentary.

**Self-check before emitting:**
- Every prompt focus area is represented; no noise rows leaked in (re-scan ids and
  notes).
- `unlogged = withheld − logged` holds everywhere; metric counts equal what the
  selected records imply.
- Every enum value used is a member of the corresponding template enum.
- Ordering, required keys, and precision all satisfy the template.
- The object parses as valid JSON.

## Reference files
- `reference/hub_data_model.md` — endpoints, tables, columns, query recipes.
- `reference/material_vs_noise.md` — per-table material/noise signal catalog.
- `reference/enum_crosswalks.md` — hub raw value → template enum mappings.
- `reference/metrics_and_action_plan.md` — metric definitions, owner/priority/
  due-days derivation, worked (schematic) examples.
- `scripts/pull_matter.sh` — dump all tables for one matter.
