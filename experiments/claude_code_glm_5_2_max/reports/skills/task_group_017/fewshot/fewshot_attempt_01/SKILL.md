# Investigation Review Hub — Gap & Remediation Dashboard

## What this skill does

Produces a **structured JSON gap / remediation dashboard** for a legal or regulatory
matter, drawn entirely from a running **Investigation Review Hub** HTTP service. The
deliverable is always a single JSON object that conforms to a task-supplied
`answer_template.json` (the schema contract). It is never a narrative memo.

The skill is matter-agnostic and template-agnostic. The same procedure handles every
deliverable archetype seen across the train tasks:

- **Rolling production gap analysis** — `critical_findings`, `category_statuses`,
  `metrics`, `priority_actions`
- **Retention / litigation-hold gap review** — `retention_events`,
  `communication_gaps`, `available_archives`, `metrics`, `recommended_actions`
- **Cross-system remediation dashboard** — `top_risks`, `category_coverage`,
  `retained_or_available_sources`, `metrics`, `action_plan`
- **Production-readiness review** — `readiness_statuses`, `issue_ledger`,
  `privilege_corrections`, `metrics`, `priority_actions`

Do not hardcode any of those shapes. Read the task's `answer_template.json` and conform
to *that* template's required keys, ordering rules, enums, field types, and numeric
precision.

## Hard constraints (read first)

1. **Source of record is the running hub, reached only over the network.** Read
   `environment_access.md` (in the work directory) at run time to obtain the base URL,
   the SQL API key, and the allow-list of endpoints. Do **not** copy the URL, key, or
   port into the skill — read them fresh each run. Do **not** open local environment
   source files, database files, seeds, generation manifests, setup scripts, or any
   "hidden notes" file. The prompts explicitly forbid all of these.
2. **Use only the allowed endpoints.** If an endpoint is not in `environment_access.md`,
   do not call it. The read-only SQL endpoint (`POST /api/query`) requires the
   `X-API-Key` header named in `environment_access.md`.
3. **Return exactly one JSON object.** No prose, no markdown fences, no trailing
   commentary. The whole final answer is the JSON.
4. **Never copy task-specific answer values** from train answers or anywhere else. Every
   ID, count, status, and category code in the output must be derived from the live hub
   for the matter under review. Train answers are illustrations of *method*, not a
   lookup table.
5. **Stable IDs verbatim.** Use matter, source, event, QC-finding, document,
   privilege, action, and category identifiers exactly as they appear in the hub. Do
   not invent, rename, or reformat them.

## Inputs to read at the start of each run

For the current task directory:

- `input/prompt.txt` — the matter, the deliverable intent, and any task-specific focus.
- `input/payloads/answer_template.json` — **the schema contract.** Parse it for:
  `required_top_level_keys`, `ordering_rules`, `enums` / `enum_choices`, `fields` /
  `schema` (item_required_keys + field types), and `numeric_precision`.
- The remaining payload file (name varies: `request_context.json`,
  `review_scope.json`, `matter_context.json`) — gives `matter_id`, client, request type,
  category-code family and labels, base URL confirmation, and source constraints.

Extract the **matter_id** from the payload/context file (and confirm it matches the
prompt). Every hub query is scoped to that matter_id.

## Procedure

### 1. Discover the hub's data model

Call `GET /api/schema` to learn the tables, columns, and relationships. Then call
`GET /api/subpoena-categories` (filtered to the matter) to fix the authoritative set of
request category codes and their labels for this matter — these codes appear throughout
the answer (`category_impacts`, `affected_categories`, `category_coverage`, etc.).

### 2. Pull all evidence for the matter

Call each relevant list endpoint and retain only records whose matter matches the
target `matter_id`:

| Endpoint | Evidence it provides |
|---|---|
| `GET /api/matters` | Matter metadata, hold date, review cutoff |
| `GET /api/productions` | What has been produced / withheld, per category |
| `GET /api/custodian-sources` | Custodian sources, status (collected / not_collected / partial / lost), source type |
| `GET /api/documents/search` | Review documents, coding (responsive/privileged/nonresponsive), produced status |
| `GET /api/privilege-log` | Withheld vs logged doc counts, log completeness, third-party recipients, waiver flags |
| `GET /api/qc-findings` | Miscoding findings (responsive miscodes, privilege miscodes), zero-claim contradictions |
| `GET /api/retention-events` | Retention losses, purge/auto-purge, post-hold destruction, policy section, hold_date |
| `GET /api/remediation-actions` | Candidate remediation actions, owners, priorities |

When a cross-table question is hard to answer from the list endpoints (e.g. "withheld
minus logged, grouped by category"), use `POST /api/query` with the SQL API key for a
single read-only query. Never write to the hub.

### 3. Identify the material gaps and defects

Classify each material hub record into an issue type. The enum names differ slightly per
template (`issue_type`, `gap_type`, retention `status`); map the record to the **enum
value defined by this task's `answer_template.json`**. The recurring defect families:

- **Preservation loss** — a source destroyed or lost, especially *after* the hold date
  (post-hold loss is far more severe than pre-hold policy-compliant destruction).
- **Collection gap** — a required source never collected or only partially collected.
- **Personal source gap** — personal phone / personal email / personal messaging not
  collected.
- **Retention / communication loss** — auto-purge, active system loss, deleted channel,
  missing required record that should exist.
- **Responsiveness miscode** — a responsive document coded nonresponsive (or a
  "zero-claim" contradiction where production claims completeness but a responsive doc
  is missing).
- **Privilege log gap** — documents withheld but not fully logged (withheld > logged).
- **Privilege miscoding** — privileged docs coded nonprivileged (or vice versa).
- **Third-party waiver / privilege exposure** — privileged content shared with a
  third party, risking waiver.
- **Over-designation** — business-only counsel copies withheld as privileged.

For full mapping rules (severity, status, production impact, owner, priority), see
[`references/answer_construction.md`](references/answer_construction.md).

### 4. Build each required top-level section

Follow `required_top_level_keys` exactly — include every key, omit nothing extra.

- **Findings / risks / issues / retention events** — one object per material defect,
  anchored on a single stable hub record ID used as the `finding_id` / `risk_id` /
  `issue_id` / `event_id`. Carry every supporting record ID in the refs list. Fill the
  count fields from the hub (`document_count`, `withheld_count`, `logged_count`,
  `unlogged_count`, `volume_count` + `volume_unit`). Use `0` when a count does not
  apply; use `null` only where the template's field type explicitly allows it
  (`third_party`, `missing_component`, dates, etc.). `unlogged_count` is
  `withheld_count − logged_count` whenever both apply.
- **Category statuses / coverage / readiness** — one object per request category that
  has a material non-complete status. Aggregate the issue records touching that
  category into the refs/issue_refs list and pick the dominant `status` /
  `production_impact` / `recommended_action`. Include the open-issue count where the
  template asks for it. Categories with no open gap are generally omitted (the templates
  ask for "material non-complete" categories) unless the template says otherwise.
- **Retained / available sources / archives** — sources that remain a remediation path
  (email archive, teams archive, offsite records, backup). State which categories each
  limits loss for. If no retained source exists, return an empty list — do not invent one.
- **Privilege corrections** (when required) — one object per privilege record needing a
  correction (supplement log, waiver assessment, recode, downgrade).
- **Metrics** — rollups computed from the evidence above. See
  [`references/answer_construction.md`](references/answer_construction.md) for the
  computation rules. Every metric key in the template must be present; counts are whole
  integers; readiness booleans are `false` when any critical/high open gap exists.
- **Priority actions / action plan / recommended actions** — the remediation plan,
  sorted by priority rank (1 = highest). Each action targets specific hub record IDs and
  lists affected categories. Map `action_type` → `owner` and `priority` per the
  conventions in the reference file. Use a stable `action_id` / `target_id`.

### 5. Apply ordering, enum, and precision discipline

- Sort every list per `ordering_rules`. The common rules: findings/issues by their ID
  ascending; categories by category code ascending; actions by priority_rank ascending
  (1 highest); category-code lists ascending within each object. Where a template
  specifies a secondary sort key (e.g. "then target_id ascending"), apply it.
- Every enum field must take a value listed in the template's `enums` /
  `enum_choices`. If the evidence does not fit cleanly, pick the closest listed value
  or `other` / `not_applicable` / `unknown` where those are offered — never invent a new
  enum string.
- Use uppercase / exact casing exactly as the enum is written. Category codes use the
  matter's own family (e.g. `R09`, `SEC-3`, single letters) verbatim from the hub.
- Whole integers only. No floats, no ranges. Booleans are JSON `true`/`false`.

### 6. Validate before returning

Self-check the final JSON against the template:

- Every `required_top_level_key` present, no extras.
- Every item object has every `item_required_keys` / `item_required` field.
- Every list sorted per `ordering_rules`.
- Every enum field value is in the allowed set.
- All counts are integers (or `null`/`0` per field type); `unlogged = withheld − logged`.
- `matter_id` matches the task's matter.
- Output is a single JSON object with no surrounding prose.

Emit the JSON object as the entire answer.

## What not to do

- Do not read or rely on `train_answers/*` values for the live matter — they belong to
  other matters and will be wrong.
- Do not hardcode the hub URL, API key, matter ID, category codes, record IDs, or any
  counts into the skill or the answer.
- Do not inspect environment source code, database files, seeds, manifests, or setup
  scripts even if present.
- Do not produce narrative text, headings, or explanations alongside the JSON.
- Do not skip a required metrics key because it is `0` — include it as `0`.
