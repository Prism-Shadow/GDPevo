---
name: investigation-review-hub-gap-analysis
description: >-
  Produce a structured-JSON gap/remediation deliverable for a government
  investigation matter (grand jury / SEC / DOJ subpoena) by reading evidence from
  the Investigation Review Hub REST API. Use when a task asks for a production gap
  analysis, retention/litigation-hold gap review, cross-system remediation
  dashboard, or production-readiness review, points at an "Investigation Review
  Hub" base URL, and requires output conforming to an answer_template.json.
  Triggers: prompt.txt + payloads/answer_template.json in an input/ dir, a matter
  id like MTR-*, endpoints such as /api/privilege-log, /api/retention-events,
  /api/remediation-actions, and an X-API-Key credential.
---

# Investigation Review Hub — gap & remediation analysis

You are outside-counsel legal-operations support. Each task gives you one matter
(`MTR-*`) and asks for a **single JSON object** that inventories the material
production/retention/privilege/QC gaps, maps them to the subpoena request
categories, reports numeric metrics, and lays out a prioritized remediation
plan — in the exact shape of that task's `answer_template.json`.

The hub is deliberately seeded with **distractor ("noise") records** that look
like issues but are not. The entire difficulty of this family is **separating
the small set of material exception records from the noise**, then translating
them into the template's controlled vocabulary. Get that right and the numbers
follow.

## Inputs to read first (every run)

1. `input/prompt.txt` — the matter, agency, the specific review being asked for,
   and which dimensions to emphasize (retention, privilege, personal sources,
   deleted channels, coding quality, etc.).
2. `input/payloads/answer_template.json` — **the output contract.** Read it in
   full: `required_top_level_keys`, every `enums` list, `ordering_rules`,
   `numeric_precision`, and each field's per-item required keys. Your answer must
   match this template exactly; templates differ between tasks.
3. Any other `input/payloads/*.json` (e.g. `request_context.json`,
   `review_scope.json`, `matter_context.json`) — **client-facing context and
   category labels only.** Treat category titles here as labels; the *evidence*
   (events, sources, counts, statuses) must come from the hub, not the payload.
4. `environment_access.md` (repo root) — the hub base URL, the required
   credential header, and the allowed endpoint list for this run.

**Source-of-record rule (stated in every task):** use only the running hub
endpoints for business evidence. Do **not** read local env files, database
files, seeds, generated manifests, hidden notes, or any answer/evaluation file.
Payload files are allowed only for the client-facing context above.

## Network access

Read the base URL and credential from `environment_access.md` (and/or the task
payload) at runtime — do not hardcode values that may change between runs.
Send the credential header on **every** request (e.g. `X-API-Key: <value>`).
Full endpoint/table map and query patterns: **`reference/hub_api.md`**.

Minimum data pull, always filtered by `?matter_id=<MTR-...>`:
`/api/matters`, `/api/subpoena-categories`, `/api/productions`,
`/api/custodian-sources`, `/api/privilege-log`, `/api/qc-findings`,
`/api/retention-events`, `/api/remediation-actions`, and
`/api/documents/search` as needed. `POST /api/query` runs read-only `SELECT`
SQL — the reliable way to look up a specific record id or aggregate counts
(`documents/search` caps at 100 rows and ignores unknown filters).

## Core procedure

1. **Anchor on remediation actions.** Pull `/api/remediation-actions` for the
   matter. The material findings are the actions whose `action_id` is **not** a
   `*-NOISE-*` action and whose `target_ref` is a **specific record id**
   (`SRC-…`, `PRIV-…`, `QC-…`, `RET-…`, `DOC-…`), not a bare category code.
   These target records are your finding set. Their `action_type`, `owner`,
   `priority`, `severity`, and `due_days` feed the action plan directly.
2. **Fetch each anchored record** by id from its table (via SQL or the matching
   endpoint) to get full detail: statuses, counts, dates, tags, categories.
3. **Sweep for material records the actions missed.** Scan
   `custodian_sources`, `privilege_entries`, `qc_findings`, `retention_events`,
   and `production_stats` for records that pass the **material test** below even
   if no action points at them (privilege gaps and pre/post-hold retention
   losses in particular often need independent judgement).
4. **Discard everything that fails the material test** — do not let noise into
   findings, categories, or metrics.
5. **Classify** each material record into the gap taxonomy and map its hub
   fields to the template's enums (`reference/discrimination_and_mapping.md`).
6. **Compute metrics** from the material set only (see Metrics below).
7. **Build category coverage** — one entry per request category that has a
   material non-complete status; aggregate the findings touching that category.
8. **Build the prioritized action plan** from the material remediation actions
   (+ any finding needing an action the hub didn't pre-stage), translating owner
   and action_type into the template's enums.
9. **Assemble, sort, validate, and return** exactly one JSON object.

## The material test (this is the whole game)

Treat a record as **material** when it shows the marks of a real, unresolved,
escalated production issue:

- It is the `target_ref` of a non-noise (`P1`/`P2`) remediation action; **or**
- Its id carries a **descriptive/semantic suffix** describing the issue
  (e.g. `…-LOG-GAP`, `…-POST`, `…-SIGNAL`, `…-SMS`, `…-TEAMS-ARCHIVE`,
  `…-ZERO-CLAIM`, `…-MISCODED-PRIV`, `…-CONSULTANT`, `…-OVERDESIG`,
  `…-LAPTOP`, `…-GMAIL`, `…-SHARE-DEL`, `…-EHS-POST`) — as opposed to a plain
  sequential id (`PRIV-<MATTER>-007`, `QC-<MATTER>-003`); **and/or**
- Its note states a **concrete, quantified, unresolved** problem
  (e.g. "Only 365 of 840 withheld privileged documents are logged"; "Six
  off-site bid file boxes destroyed after hold"; "Signal messages were
  identified in custodian interview but not collected"), with a loss/gap status
  (`not_collected`, `lost`, `post_hold_loss`, `should_exist_missing`,
  `destroyed`) and/or non-routine `issue_tags`.

Treat a record as **noise (exclude it)** when it shows the distractor marks:

- `action_id` contains `NOISE`, or `priority: P3`, or `severity: low`, or
  `target_ref` is a bare category code, or `owner` is `Matter Associate` /
  `Vendor Team`, or `action_type` is `sampling_review` / `load_file_cleanup` /
  `custodian_followup`;
- a plain sequential id and/or `issue_tags: ["routine"]`;
- a **hedging / dismissive note** — the recurring distractor phrasings include
  "included to create similar labels across matters", "ordinary review
  variance", "marked … for follow-up but not immediate remediation", "requires
  category-level context before escalation", "noisy but not dispositive",
  "re-sampling before escalation", "similar to escalated records in another
  matter", "remediated by archive collection", "no unresolved production
  impact", "no production-impacting issue has been escalated yet", "not one of
  the stable exception records", "clean", "requires matter-level filtering".

**Do NOT select on severity or raw counts.** Noise records routinely carry
`severity: high` and large `doc_count`/`unlogged` values specifically to bait
you. A privilege entry with `unlogged=46` and note "marked for follow-up but not
immediate remediation" is **noise**; the material one is the descriptive-id
entry with the factual note. When a note hedges, exclude — regardless of size.

## Metrics

- Compute **only from the material set.** Where a template says a count is drawn
  "from selected … blockers only," sum across the material records you kept, not
  every hub row.
- Privilege math: `unlogged = withheld_count − logged_count` per entry; roll up
  the material incomplete-log entries for the withheld/logged/unlogged totals.
- Retention volume: report the material event's `volume_count`/`volume_unit`
  (e.g. boxes) — pre-hold policy-compliant destruction is **not** a loss and is
  excluded from loss metrics.
- Counts are whole integers; use `0` (not null) for "0 when not applicable".
- `production_ready` / `rolling_production_ready` is `true` only if there are no
  open material blockers — with a real material finding it is `false`.

See `reference/discrimination_and_mapping.md` for the full gap taxonomy,
pre/post-hold retention logic, and the hub→template owner/action_type/enum
translation tables (the raw hub owner and action vocabularies do **not** match
the template enums and must be mapped).

## Output contract

- Return **exactly one JSON object and no prose outside it.** If the task names a
  required answer file (e.g. `answer.json`), also write the same object there.
- Include exactly the `required_top_level_keys`; set `matter_id` to the hub id.
- **Every enum field value must be a member of that field's template enum list.**
  If no hub value maps cleanly, pick the closest allowed enum — never invent a
  value or reuse a raw hub string that isn't in the enum.
- Apply `ordering_rules` precisely: sort each list by its key ascending; sort
  priority/rank lists ascending with `1` = highest priority.
- Category codes: uppercase, sorted ascending, in every category set.
- `source_refs` / `target_refs` / `record_refs` / `blocking_refs`: stable hub
  ids exactly as they appear, sorted ascending.
- Only list categories/records with a material non-complete status (per each
  list's description in the template).
- Honor `numeric_precision`; use `null` only where the schema explicitly allows.

## Before returning — verify

- [ ] JSON parses; top-level keys == `required_top_level_keys`; every list sorted
      per `ordering_rules`.
- [ ] Every enum value is in the template's enum for that field.
- [ ] Every finding/category/action traces to a **material** record; no noise id,
      no `*-NOISE-*` action, no bare-category `target_ref` leaked in.
- [ ] Metrics cross-foot: `unlogged = withheld − logged`; counts match the cited
      material records; booleans reflect open blockers.
- [ ] All evidence came from the hub; no local db/seed/manifest/answer file used.
