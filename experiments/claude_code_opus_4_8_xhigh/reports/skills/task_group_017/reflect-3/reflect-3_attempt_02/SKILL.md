---
name: investigation-review-gap-analysis
description: >-
  Produce a single structured-JSON gap / defect / remediation analysis for a
  litigation or investigation matter, driven entirely by an "Investigation
  Review Hub" dataset and conforming to a task-provided answer_template.json.
  Use this whenever a task asks for a production gap analysis, a retention /
  litigation-hold gap review, a cross-system remediation dashboard, a
  production-readiness review, or a similar structured e-discovery deliverable
  whose evidence lives in a review hub exposing tables such as matters,
  subpoena_categories, production_stats, custodian_sources, review_documents,
  privilege_entries, qc_findings, retention_events, and remediation_actions.
---

# Investigation Review Hub — structured gap/remediation analysis

These matters vary (grand-jury, SEC, DOJ antitrust; production gap, retention
review, remediation dashboard, readiness review) and every one ships its own
`answer_template.json`, but they are the **same problem**: read a noisy review
hub, separate the handful of *material* defects from realistic operational
noise, normalize them into the template's vocabulary, and compute exact
rollup metrics. Solve them with one repeatable pipeline.

The schema changes per task; the **method does not**. Treat the answer_template
as the contract and the hub as the only source of truth.

## 0. Ground rules

- **The hub is the sole source of business evidence.** The prompts explicitly
  forbid reading local environment source files, database/seed files, generated
  manifests, hidden notes, or any "standard answer" file. Pull every fact from
  the hub's read endpoints. The task's environment-access file tells you the
  hub base URL, the API-key header to send, and the exact read endpoints that
  are permitted — use those and nothing else.
- **Output is one JSON object and nothing else.** No prose, no markdown fences.
  Conform exactly to the answer_template: every required top-level key, every
  required item key, the declared enums, types, ordering, and integer/boolean
  precision.
- **Work matter-scoped.** Every table holds many matters. Filter everything by
  the matter_id from the request the moment you query.

## 1. Read the contract first

Before touching data, read the task `prompt.txt`, the payload file(s) in
`input/payloads/`, and the `answer_template.json`. From the template, extract
and keep in front of you:

- `required_top_level_keys` — the sections you must emit.
- Each list's `item_required_keys` / field types.
- `ordering_rules` — how each list is sorted (and any tie-breakers).
- The `enums` block — the *only* legal values for every enum field. You will
  map raw hub strings onto these; never invent a value outside the enum.
- `metrics` required keys and their one-line definitions (they tell you exactly
  what to count and how, e.g. "documents from selected incomplete-log blockers
  only", "boxes for the destroyed source named in the task").

The payloads usually give you the matter_id, client, agency, deliverable label,
and the request category labels/synopsis. Category **titles** may come from a
payload, but category **evidence** (events, sources, counts) must come from the
hub.

## 2. Pull the matter's data

Discover the shape, then extract. The hub exposes a resource per table plus a
read-only SQL query endpoint; the SQL endpoint is the fastest way to pull one
matter's rows from every table. For each table, select all rows
`WHERE matter_id = '<this matter>'`, and save them so you can re-read locally
while you build the answer.

Tables you will use (names come from the hub's schema resource):

| table | what it anchors |
|---|---|
| `matters` | matter metadata: hold_date, agency, dates |
| `subpoena_categories` | the request categories (codes + titles) |
| `production_stats` | per-category production; `status` + `zero_claim_reason` |
| `custodian_sources` | custodian devices/sources; `status`, `post_hold`, `issue_tags` |
| `review_documents` | document-level review corpus (mostly volume/noise) |
| `privilege_entries` | privilege log entries; withheld/logged counts, third_party |
| `qc_findings` | QC defects; issue_type, doc_count, severity |
| `retention_events` | retention/preservation losses; status, volume |
| `remediation_actions` | escalated action list (the spine — see §3) |

`review_documents` is deliberately large and mostly realistic noise. Do not
enumerate it into the answer; aggregate it only to corroborate a specific count
that a material `qc_finding` points at (e.g. the single doc tagged as a
responsiveness miscode).

## 3. Find the material record set (the crux)

Each matter contains only a **handful of material defects** buried in dozens of
realistic-but-immaterial rows. Identifying that set correctly is 80% of the job.

**Use `remediation_actions` as the spine.** The escalated, real issues are the
rows whose `action_id` is a normal action AND whose `target_ref` points at a
specific hub record. Drop the injected noise actions — they are recognizable:

- `action_id` contains a noise marker (e.g. `...-NOISE-0x`),
- `description` is boilerplate like *"Routine action included as realistic
  operational noise"*,
- `target_ref` is a bare category code rather than a record ID.

The `target_ref`s of the surviving (non-noise) remediation actions are your
**material anchor records**. Then pull each anchor from its home table
(`SRC-...` in custodian_sources, `PRIV-...` in privilege_entries, `QC-...` in
qc_findings, `RET-...` in retention_events).

**Corroborate and extend.** A few material issues may not have their own
remediation action (e.g. a zero-production claim that is contradicted, an
available archive that mitigates a loss). Also check:

- `production_stats.status` / `zero_claim_reason` for a contradicted
  zero-production certification,
- `custodian_sources` tagged as an available archive / retained source,
- the anchor's own cross-references (a qc_finding's `source_ref`, a retention
  event's archive exception).

**Recognize distractors and exclude them.** Immaterial rows have generic
sequential IDs and carry tell-tale boilerplate notes. If a row's note matches
one of these, it is noise unless a non-noise remediation action targets it:

- "ordinary review variance" / "Privilege sample has ordinary review variance"
- "minor metadata normalization issues"
- "No production-impacting issue has been escalated yet"
- "remediated by archive collection" / "Potential issue was remediated…"
- "vendor tracker and legal hold tracker use slightly different record labels"
- "relevant only after comparing hold date and policy period"
- "similar label but has no unresolved production impact"
- "Requires matter-level filtering because similar issue labels appear across matters"
- "included to create similar labels across matters"
- "similar to escalated records in another matter"
- "requires category-level context"
- "marked this item for follow-up but not immediate remediation"
- "noisy but not dispositive"

By contrast, **material** anchor records carry a descriptive ID (naming the
custodian/device/defect) and a note that states a concrete defect **with
numbers and a date** (e.g. "…erased after subpoena issuance", "Only N of M
withheld documents are logged", "boxes destroyed after the hold date",
"identified in interview but not collected", "archive backup available for the
deleted channel"). See `reference/field-mapping.md` for the recurring defect
archetypes and how each maps to the template vocabulary.

## 4. Normalize each material record into the schema

For every material record, fill one list item. Choose enum values by the
**intrinsic nature of the defect**, constrained to the template's enum lists.
The detailed archetype→enum tables live in `reference/field-mapping.md`; the
load-bearing rules:

- **issue/status/impact enums**: map the hub's raw status onto the closest
  template enum (e.g. a raw "system_loss" becomes the template's active-system-
  loss value; a wiped/erased device becomes "lost/destroyed" + "source_lost").
- **severity / risk_level = intrinsic severity of the issue, not the
  remediation row's severity field.** Post-hold or post-subpoena destruction
  (spoliation) is high/critical; a missing required record is high; a
  policy-compliant *pre-hold* destruction is low; auto-purge or system loss that
  an archive can still remediate, and partial-recovery losses, are medium.
- **counts**: `unlogged = withheld − logged`. Use 0 (not null) for count fields
  that don't apply. Physical volumes keep their unit; put doc counts in the doc
  fields.
- **third_party**: carry the third-party name/flag from a privilege entry with
  `third_party = 1`; otherwise null.
- **source_refs / issue_refs / target_refs**: the supporting hub record IDs,
  sorted ascending. **category lists** (`affected_categories`, etc.) use the
  category codes, sorted ascending.
- **owner**: assign by the *function* of the recommended action, mapped to the
  template's owner enum — disclosure→counsel; forensic/personal-device or
  archive collection→forensics/ediscovery vendor; privilege-log work→privilege
  team; waiver assessment→privilege counsel; recode/QC→review-QC/review vendor;
  records retention→records management. The raw `owner` strings in the hub do
  **not** map cleanly onto the enum, so drive owner from the action, not the row.

For per-category sections, produce one entry per category. Some templates want
an entry only for categories with a material issue; others enumerate **every**
request category (with a "no open gap / ready" status for clean ones) — follow
the template's wording and its enum set (if a "no_open_gap"/"ready" enum exists,
list all categories). A category's status is the **most severe** issue touching
it; its refs are the sorted union of the records touching it.

## 5. Compute metrics exactly

Metrics are graded strictly (treat the metrics object as pass/fail — one wrong
number fails it), so derive each from the material anchors and re-check the
arithmetic:

- Counts of events/sources by type = number of **material** records of that type
  (never include distractors).
- Box/volume math: sum destroyed volumes; split pre-hold vs post-hold; a
  "destroyed boxes" metric counts only records actually measured in boxes (else
  0 per its definition).
- Privilege doc metrics come from the specific blocker(s) the metric names
  (e.g. the incomplete-log gap): withheld, logged, and `unlogged = withheld −
  logged`.
- "unique affected category count" / "categories with … " = the sorted union of
  category codes across the material records (count = length of that list).
- A production-ready / rolling-ready boolean is **false** whenever any material
  gap remains.

Read each metric's one-line definition in the template literally; the noun it
names (events, sources, documents, boxes, categories) tells you the unit.

## 6. Order, format, self-check

- Sort every list per the template's `ordering_rules`. When a list is ranked by
  a `priority_rank` you assign, use a **unique sequential** 1..N ordered by
  priority tier (P0<P1<P2<P3) then the declared tie-breaker (usually the record
  ID / target ID ascending).
- Emit whole integers, real booleans, and `null` only where the type says
  "or null".
- Validate before returning: all required keys present; every enum value is in
  the template's enum list; lists sorted; counts internally consistent
  (`unlogged = withheld − logged`; category-count = length of category list;
  section counts = list lengths). Return exactly one JSON object.

## What to hand back

Return only the JSON deliverable. Do not include any commentary, the reasoning
trail, or intermediate data in the final answer.

See `reference/field-mapping.md` for defect archetypes, enum-mapping tables, and
metric recipes, and `reference/pipeline.md` for a runnable, matter-parameterized
extraction/aggregation outline.
