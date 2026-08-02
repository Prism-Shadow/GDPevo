# Output contract — the recurring answer archetype

Every task hands you a different `answer_template.json`, but they all instantiate
the **same five-part dashboard** under task-specific key names, enum lists, metric
sets, and ordering. Read the template for the exact names each time; use this map
only to recognize which part is which and to know what evidence feeds it.

| Archetype part | Named (examples across tasks) | Feeds from |
|---|---|---|
| 1. Matter id | `matter_id` | context payload + `matters` |
| 2. Material findings | `critical_findings` / `top_risks` / `issue_ledger` (+ `privilege_corrections`) / `retention_events` + `communication_gaps` | retention_events, custodian_sources, review_documents, privilege_entries, qc_findings |
| 3. Category coverage | `category_statuses` / `category_coverage` / `readiness_statuses` | per-category rollup of part 2 + production_stats + subpoena_categories |
| 4. Retained/available sources | `available_archives` / `retained_or_available_sources` | custodian_sources (`available`/`retained`), retention_events `retained` |
| 5. Metrics | `metrics` | integer rollups of parts 2–4 |
| 6. Action plan | `priority_actions` / `action_plan` / `recommended_actions` | remediation_actions (mapped to template enums) |

Not every template includes a standalone part 4 (part-1 tasks fold sources into
finding `source_refs`); some split part 2 into two lists. Follow
`required_top_level_keys` exactly — emit every listed key, and no extras.

## Reading the template — checklist
- **`required_top_level_keys`** → the exact set of top-level keys to emit.
- **`item_required_keys` / `schema`** → every field each list item must carry.
  Missing-value convention: `0` for N/A integer counts, `null` for N/A
  strings/dates, `[]` for empty lists (unless the template says otherwise).
- **`enums` / `enum_choices`** → the *only* legal values for each enum field.
  These vocabularies differ per task; never emit a value not listed. Map the raw
  hub value to the closest listed enum and stay consistent across sections.
- **`ordering_rules`** → sort key + direction for each list (usually an id
  ascending, or `priority_rank`/`rank` ascending with 1 = highest). Sort
  category-code sets ascending within every list.
- **`metrics.required_keys` + `field_types`** → the exact metric names, their
  units, and any scoping qualifier in the description (honor "…only" clauses).
- **`numeric_precision`** → all counts whole integers; `due_days` whole days;
  no fractional scores unless a field is explicitly typed that way.
- **`output_rule`** → return exactly one JSON object, no prose outside it.

## Common item fields and how to populate them
- `*_id` (finding/risk/event/source/correction/action) — a stable hub record id
  that anchors the item; reuse the hub id verbatim, do not mint new ones.
- `*_refs` (`source_refs`, `issue_refs`, `blocking_refs`, `record_refs`,
  `target_refs`) — supporting hub ids, sorted ascending.
- `affected_categories` / `category_impacts` — category codes for the item,
  uppercase, sorted ascending.
- count fields (`document_count`, `withheld_count`, `logged_count`,
  `unlogged_count`, `volume_count`) — integers from the hub row;
  `unlogged = withheld − logged`; `0` when not applicable.
- `severity`/`risk_level`, `status`, `production_impact`, `source_status`,
  `recommended_action`, `owner`, `priority` — pick the matching enum per
  `references/gap_classification.md`.
- `third_party` — from `privilege_entries.third_party`; string/label or `null`
  per the template's declared type.

## Consistency invariants (self-check before emitting)
- Every category flagged non-complete in part 3 is explained by ≥1 finding in
  part 2 whose `affected_categories` include it.
- Every material finding has a corresponding action in part 6 (and no action
  targets a phantom finding).
- Part-5 metrics reconcile with parts 2–4 (e.g. `available_archive_count` ==
  number of part-4 items; privilege doc metrics == sum over the scoped
  privilege findings).
- `production_ready`-style booleans are `true` only if no in-scope category
  carries a material blocker.
