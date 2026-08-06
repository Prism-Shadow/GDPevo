---
name: investigation-review-hub-gap-analysis
description: Produce a schema-conformant JSON gap-analysis / remediation dashboard from the Investigation Review Hub for a legal-discovery matter. Use when a task points at the Investigation Review Hub (base URL like http://task-env:PORT/) and asks for a structured-JSON deliverable (rolling production gap analysis, retention/preservation review, cross-system remediation dashboard, production-readiness review, etc.) conforming to a provided answer_template.json.
---

# Investigation Review Hub — Structured Gap Analysis

This skill solves tasks that ask for a **structured JSON** deliverable about a legal-discovery matter, using a shared **Investigation Review Hub** as the source of record. The hub exposes matter metadata, subpoena categories, production stats, custodian sources, review documents, privilege-log entries, QC findings, retention events, and remediation actions.

The deliverable is always **one JSON object** that must conform to a task-specific `answer_template.json` (field names, types, enum values, ordering rules, required keys, and numeric precision are all defined there). The hard parts are (1) pulling the right data from the hub, (2) separating the few **material** records from many **decoy/noise** records, and (3) conforming exactly to the schema.

## Source of record

Use **only** the Investigation Review Hub endpoints and the task-local payload files. Never inspect environment source files, database files, seeds, manifests, or setup scripts — the prompts explicitly forbid it. Each task provides the hub base URL and API key in its `environment_access.md` / payload files; read those for the current run's access (do not assume a fixed URL/key from memory).

The hub has two ways to read data:
- **REST list endpoints** (`GET /api/matters`, `/api/subpoena-categories`, `/api/productions`, `/api/custodian-sources`, `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings`, `/api/retention-events`, `/api/remediation-actions`, and `GET /api/schema`).
- **A read-only SQL endpoint**: `POST /api/query` with header `X-API-Key` set to the task-provided key, body `{"sql": "<SELECT ...>"}`. **The body key is `sql`, not `query`.** It returns `{"columns": [...], "row_count": N, "rows": [...], "truncated": bool}`.

The SQL endpoint is by far the most efficient tool: pull every table filtered by `matter_id` in one pass. See `references/hub_tables.md` for the full table/column reference.

## Procedure

1. **Read the inputs.** Read the task `prompt.txt`, the `answer_template.json` (this defines the exact output contract — study it carefully), and any payload file (`request_context.json` / `review_scope.json` / `matter_context.json`). Note the `matter_id` and any review cutoff date.
2. **Pull the matter's data.** For the task's `matter_id`, query every hub table with `WHERE matter_id = '<matter_id>'`. Pull all 9 tables (see `references/hub_tables.md`). **Restrict every query to the single task matter_id** — the hub contains many matters; querying other matters is out of scope.
3. **Identify the material records.** Each table is mostly **decoy/noise** rows plus a few **material** rows. This is the single most important step. Use the heuristics in `references/noise_and_material.md`:
   - **Named, business-specific records are material** (e.g. `SRC-ALLOY-KLINE-SIGNAL`, `PRIV-NORTH-LOG-GAP`, `RET-HARB-EHS-POST`, `QC-ALLOY-ZERO-CLAIM`); their notes describe a concrete, escalated fact.
   - **Generically-numbered records are decoys** (e.g. `SRC-ALLOYWORKS-001`, `PRIV-NORTHBAYSE-001`, `RET-GRAYCLIFFS-001`) — their notes contain noise phrases.
   - **Confirm the material set with `remediation_actions`**: the non-noise remediation actions (those whose `description` is NOT "Routine action included as realistic operational noise") target **exactly** the material records via `target_ref`. This is a reliable cross-check — use it.
4. **Derive the metrics.** Compute every numeric metric in the template from the material records (counts of material records of each type, withheld/logged/unlogged privilege counts, box counts, affected-category counts). See `references/metric_definitions.md`.
5. **Build the structured lists** (`critical_findings`/`top_risks`/`issue_ledger`, `category_statuses`/`category_coverage`, `retained_or_available_sources`/`available_archives`, `priority_actions`/`action_plan`, etc.) — one entry per material record or per affected category, as the template dictates.
6. **Conform strictly to the schema** — see the checklist below.
7. **Return exactly one JSON object** and nothing else (no prose, no markdown fences).

## Schema-conformance checklist (this is where most points are lost)

- **Required top-level keys**: include exactly the keys listed in `required_top_level_keys`, no more, no less.
- **Required item keys**: every object in every list must contain every key in `item_required_keys` for that field.
- **Enums**: every enum-typed field must be a value listed in the template's `enums` / `enum_choices`. Enum names differ per task — copy them verbatim. When a real-world concept has no exact enum (e.g. over-designation when the enum lacks it), fall back to the `other`/`not_applicable` enum if present, never invent a value.
- **Ordering**: sort each list per `ordering_rules`. Common rules: sort by the stable ID ascending, by `priority_rank`/`rank` ascending (1 = highest), by `category_code` ascending, and sort category-code lists ascending within each object. Apply the sort to the actual list order **and** to any in-object `category_impacts`/`affected_categories`/`source_refs` lists.
- **Types & precision**: counts are whole integers; use `0` when not applicable; booleans are `true`/`false`; dates are `YYYY-MM-DD` strings; use JSON `null` where the schema says "or null".
- **Stable IDs**: use hub record IDs exactly as they appear (`source_id`, `event_id`, `finding_id`, `entry_id`, `doc_id`, `action_id`, `batch_id`). These anchor findings and are matched as sets.
- **One JSON object only**: no trailing text.

## Key reasoning rules

- **Material vs noise is decisive.** A wrong noise/material split fails most checks because findings/categories are matched by their stable-ID sets. When uncertain, trust the `remediation_actions` cross-check over the note text alone.
- **Communication-system losses** (Teams messages purged, voicemail auto-delete) are both retention events **and** communication gaps — include them in the retention-events list **and** in the communication-gaps list (the latter is the system-gap subset). `retention_event_count` counts all material retention events including these.
- **Pre-hold policy destructions** (`policy_destroyed_pre_hold`) are compliant losses — they are findings/events but the recommended action is a no-action/policy-loss action, not a preservation disclosure.
- **Post-hold losses and post-subpoena erasures** are the highest-severity items (preservation failure / disclosure to government).
- **`post_hold` flag** on custodian sources distinguishes a real preservation failure (flag = 1, event after hold) from routine collection timing.
- **Privilege metrics**: `unlogged = withheld − logged`. "Incomplete-log blockers" are privilege entries with `issue_type = incomplete_log`. Over-designated, family-mismatch, and clean entries are noise unless escalated.
- **`category_status`/`readiness_status`**: only emit a category entry when it has a material non-complete status; a category with no material issue is either omitted or marked `no_open_gap`/`ready` per the template's enum.

## Common pitfalls

- Forgetting the SQL body key is `sql` (not `query`) — returns `{"error":"sql must be a non-empty string"}`.
- Querying all matters instead of filtering by `matter_id` — mixes in decoy data from other matters.
- Treating decoy records (the generically-numbered ones with noise notes) as material — inflates counts and adds wrong findings.
- Inventing enum values or using a different task's enum names — each task's template has its own enum set.
- Not sorting lists / not sorting the in-object category-code and source-ref lists.
- Including prose or markdown around the JSON.
- Including extra top-level keys or omitting required item keys.

## References

- `references/hub_tables.md` — full hub table/column reference (the data model is constant across matters).
- `references/noise_and_material.md` — noise note-phrase catalog and material-record identification rules.
- `references/metric_definitions.md` — how to derive each metric family.
