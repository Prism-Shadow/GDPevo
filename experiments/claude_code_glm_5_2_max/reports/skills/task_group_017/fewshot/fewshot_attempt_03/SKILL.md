---
name: investigation-review-hub-gap-analysis
description: Produce a structured JSON gap / remediation / readiness analysis for a legal investigation matter by querying the shared Investigation Review Hub over the network. Use when a task gives a matter ID, a per-task answer_template.json schema, and asks for production gaps, retention/preservation losses, privilege defects, responsiveness miscodes, QC findings, category coverage, metrics, and a prioritized action plan — returned as a single JSON object.
---

# Investigation Review Hub — Structured Gap / Remediation Analysis

This skill handles a family of tasks that all share one shape: a legal or regulatory
matter (grand jury subpoena, SEC subpoena, DOJ antitrust, environmental) needs a
**structured JSON** analysis of production gaps, preservation/retention losses, privilege
defects, responsiveness miscoding, and QC findings, plus a prioritized action plan. The
single source of record is the shared **Investigation Review Hub**, reached only over the
network. The output must be exactly one JSON object conforming to the task's own
`answer_template.json`.

The five task variants observed differ only in which top-level keys and enums the template
requires (rolling-production gap analysis, retention/hold gap review, cross-system
remediation dashboard, production-readiness review). The *method* below is the same for all
of them. **Treat the per-task `answer_template.json` as the schema authority** — read it
fresh every run and adapt the output structure to whatever keys, enums, ordering rules, and
field types it declares.

## What you must never do

- Do **not** inspect local environment source files, database files, seed data, generation
  manifests, setup scripts, hidden notes, or any task answer / evaluation files. Business
  evidence comes only from the running hub endpoints and the task-local payload files.
- Do **not** invent record IDs, category codes, owners, or counts. Use stable hub IDs
  exactly as they appear.
- Do **not** copy values from any prior task's answer. Each matter is solved from its own
  hub data.
- Do **not** return prose, markdown, or explanation. Return exactly one JSON object.

## Inputs

1. `prompt.txt` — names the client, the matter ID, the review type, and the deliverable.
2. `input/payloads/answer_template.json` — the schema you must conform to. It declares:
   - `required_top_level_keys`
   - `ordering_rules` (per-list sort keys)
   - `enums` (allowed values for every enum field — these vary per task)
   - `fields` / `schema` (field names, types, descriptions, and which keys each list item needs)
   - `numeric_precision`
3. A context payload (`request_context.json` / `review_scope.json` / `matter_context.json`) —
   client-facing request context, category labels, and a repeat of the base URL / API key.
   It is **context only**; event and source evidence still comes from the hub.

## Environment access

Read `environment_access.md` (at the repo root) for the base URL, the API key, and the
allowed endpoint list. Reach the hub **only** over the network using those endpoints. Full
endpoint, SQL, and table details live in `references/hub_endpoints.md`.

## Procedure

### 1. Read the template as the schema authority
Open `answer_template.json` and extract: required top-level keys, every enum set, every
list's required item keys and field types, every ordering rule, and the metric key list.
The metric keys and their descriptions define **exactly** what to count — some metrics are
scoped (e.g. "from selected incomplete-log blockers only"). Honor those scopes literally.

### 2. Identify the matter
Take the `matter_id` from the prompt and/or the context payload. All hub evidence is
filtered to this one matter.

### 3. Pull all hub evidence for the matter
Fetch every relevant table filtered by `matter_id`. See `references/hub_endpoints.md` for
the endpoint-to-table mapping and query shapes. The nine hub tables are: `matters`,
`subpoena_categories`, `production_stats`, `custodian_sources`, `review_documents`,
`privilege_entries`, `qc_findings`, `retention_events`, `remediation_actions`. Prefer the
GET endpoints (each accepts a `matter_id` filter) for whole-table reads; use the SQL
endpoint for joins/aggregates.

### 4. Build the category frame
From `subpoena_categories`, list every request category code and title for the matter.
Category codes are whatever the hub uses (single letters, `R##`, `SEC-*`, etc.) — preserve
them verbatim and sort ascending inside any list. Classify every issue against these codes.

### 5. Detect material issues by domain
Apply the issue taxonomy in `references/issue_taxonomy.md`. In short, scan the hub data for:
- **Preservation / retention loss** — `retention_events` and `custodian_sources` records
  that are lost/destroyed/purged/missing, distinguishing pre-hold policy destruction from
  post-hold loss.
- **Collection gaps** — `custodian_sources` not yet collected.
- **Privilege log gaps** — `privilege_entries` where `withheld_count - logged_count > 0`.
- **Privilege waiver** — `privilege_entries` flagged third-party.
- **Privilege miscoding / over-designation** — `qc_findings` + `privilege_entries` coding defects.
- **Responsiveness miscoding / zero-production claims** — `review_documents` miscodes plus
  `qc_findings` and `production_stats.zero_claim_reason`.
- **Communication / system gaps** — auto-purge and active-system-loss retention events.
- **Available archives / retained sources** — `custodian_sources` / `remediation_actions`
  that remain a remediation path.

For each issue, anchor it on the **stable hub record ID** the template expects
(`finding_id` / `risk_id` / `issue_id` / `event_id` / `source_id` / `correction_id`).

### 6. Normalize each issue to the template's fields
For every list item, fill every required key. Apply these normalization rules:
- **Counts are whole integers.** Use `0` when a count is not applicable; never omit a
  required count key.
- **Privilege math:** `unlogged_count = withheld_count - logged_count` (clamp at 0).
- **`document_count`** = actual documents tied to the issue. **`volume_count`** + the enum
  **`volume_unit`** = how the issue's bulk is measured (boxes / sources / emails / report /
  documents / `not_applicable`).
- **`source_refs` / `record_refs` / `issue_refs` / `target_refs` / `blocking_refs`** = the
  set of hub record IDs supporting the item, **sorted ascending**, deduplicated.
- **`category_impacts` / `affected_categories`** = category codes touched, sorted ascending.
- **Nullable fields** (dates, `third_party`, `missing_component`, `policy_section`,
  `retention_period_months`, `volume_count`, `cutoff_date`, `purge_window_days`, etc.) use
  JSON `null` when absent — never drop the key, never use empty string.
- **Every enum value** must come from the template's enum set for that field. Where the
  template's enum names differ from the hub's free-text tags, map to the closest allowed
  enum value (see `references/issue_taxonomy.md`).

### 7. Roll up category coverage / statuses
For each request category with any open issue, produce the per-category object the template
requires (e.g. `category_statuses`, `category_coverage`, `readiness_statuses`). Aggregate
the issue refs into the category's ref list (sorted ascending), pick the category's
`status` and `production_impact` from the dominant issue, and set `recommended_action` /
`required_actions` accordingly. Categories with no open gap are omitted unless the template
asks for all categories.

### 8. Compute metrics
Compute every key in the template's `metrics` block. Count over the issues you actually
recorded (after scoping). Common metric families: privilege withheld/logged/unlogged;
miscoded responsive doc count; lost personal-device count; uncollected source counts;
post-hold loss event count; available archive count; affected/`categories_with_open_*`
count and list; a boolean readiness flag (false when any P0/P1 blocker is open). Re-read
each metric's description — several are deliberately scoped and will be wrong if you count
everything.

### 9. Build the prioritized action plan
Produce the action list (`priority_actions` / `action_plan` / `recommended_actions`)
sorted by `priority_rank` / `rank` ascending (1 = highest). Ranking logic:
1. **P0 / rank 1–2:** source-lost / post-hold preservation losses and privilege waiver
   exposure that must be disclosed to the government/agency → `disclose_preservation_issue`
   / `disclose_to_government` / `waiver_assessment_and_disclosure`, owner
   `outside_counsel` / `privilege_counsel`.
2. **P1 / next:** privilege log supplementation, privilege/privilege-responsiveness recodes,
   source collection (personal devices, board sources, archives) → owners
   `privilege_team` / `review_qc` / `forensics` / `ediscovery_vendor` / `client_it`.
3. **P2:** over-designation downgrades, QC remediation of lower-severity items.
4. **P3 / monitor:** pre-hold policy-compliant losses (`no_action_policy_loss` /
   `monitor_only`), records-management documentation.

Each action targets specific hub record IDs (`target_refs`, sorted ascending) and the
categories they affect. `due_days` (where the template asks): P0 ≈ 3, P1 ≈ 3–7, P2 ≈ 5–10,
P3 = monitor. Assign `owner` and `action_type` only from the template's enums.

### 10. Assemble and validate the JSON object
- Top-level keys: exactly the template's `required_top_level_keys`, in that order.
- Apply every `ordering_rule` to its list.
- Sort every ID list and every category list ascending.
- Confirm every enum field value is in the template's enum set.
- Confirm every required item key is present; counts are integers; nullables are `null`.
- Emit **only** the JSON object — no wrapping, no prose, no trailing comma, no comments.

## When to stop and report contamination

If anything in `/work` is not one of: `environment_access.md`, the `train_tasks/` tree, or
the `train_answers/` tree — or if a payload contains answer values, evaluation rubrics, or
non-environment source/db/manifest files — do not proceed. Write `contamination_report.txt`
describing the unexpected material and stop.
