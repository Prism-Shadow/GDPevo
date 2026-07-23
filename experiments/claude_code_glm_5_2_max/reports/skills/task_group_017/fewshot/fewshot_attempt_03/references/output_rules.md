# Output Rules & Validation Checklist

The deliverable is always **exactly one JSON object** conforming to the task's
`answer_template.json`. No prose, no markdown, no trailing text.

## Structural rules

- Top-level keys are exactly `required_top_level_keys`, in the order listed.
- Every list item contains every key in its `item_required_keys`.
- Empty lists are `[]` (e.g. no available archives → `retained_or_available_sources: []`).
- Empty objects/strings are not allowed where the field is a count or ID; use `0` or `null`
  per the field's type.

## Ordering rules (apply every one declared in the template)

- `critical_findings` / `issue_ledger` / `retention_events` / `communication_gaps` → sort
  by the item's stable ID ascending.
- `top_risks` → sort by `priority_rank` ascending (1 first).
- `priority_actions` / `action_plan` / `recommended_actions` → sort by `priority_rank` /
  `rank` ascending; if a tie-breaker is declared (e.g. `target_id` ascending), apply it.
- `category_statuses` / `category_coverage` / `readiness_statuses` → sort by `category_code`
  ascending.
- `available_archives` / `retained_or_available_sources` → sort by `source_id` ascending.
- `privilege_corrections` → sort by `correction_id` ascending.
- Inside any ID list or category list: sort ascending, deduplicate.

## Enum compliance

- Every enum field value must be a member of the template's enum set for that field.
- Enum sets **differ per task variant** — never reuse enum values from a different task's
  template. Read the current template's `enums` block.
- If a hub tag does not match an enum exactly, map to the closest allowed value (see
  `issue_taxonomy.md`); if nothing fits, the template usually provides an `other` /
  `unknown` / `not_applicable` fallback.

## Numeric precision

- All counts are whole integers. Use `0` when a count is not applicable.
- `unlogged_count = withheld_count - logged_count` (never negative; clamp at 0).
- `priority_rank` / `rank` / `open_issue_count` / metric counts are integers ≥ 0.
- `due_days`, `retention_years`, `retention_period_months`, `purge_window_days` are whole
  integers where the template asks for them.
- No floats, no stringified numbers.

## Nullables

Use JSON `null` (not omission, not `""`) for absent nullable fields the template declares
as "string or null" / "integer or null": dates (`event_date`, `hold_date`, `cutoff_date`),
`third_party`, `missing_component`, `policy_section`, `retention_period_months`,
`volume_count`, `purge_window_days`, `archive_exception_source_id`.

## Metric scoping (read each description)

Several metrics are deliberately scoped. Common traps:
- Privilege withheld/logged/unlogged doc metrics may be limited to "selected incomplete-log
  blockers only" — do not sum across all privilege entries unless the description says so.
- `destroyed_lab_archive_box_count` may be "boxes for the destroyed records source named in
  the task, or 0 when not measured in boxes" — 0 when the destroyed source isn't box-based.
- `lost_personal_device_count` / `uncollected_*_source_count` count **sources**, not docs.
- `categories_with_open_gaps` / `categories_with_open_risk` is both a count and a sorted
  list — emit whichever the metric key asks for (some templates have a count key **and** a
  list key).
- `rolling_production_ready` / `production_ready` is boolean → `false` when any P0/P1
  blocker remains open, else `true`.

## Final self-check before emitting

1. Required top-level keys present and ordered.
2. Every list item has every required key.
3. Every list sorted per its ordering rule; every ID/category list sorted ascending.
4. Every enum value is in the template's enum set.
5. Counts are integers; nullables are `null`; privilege math holds.
6. Metrics match their per-key scope.
7. Output is a single JSON object with no surrounding text.
