# Output Conventions

The deliverable is **exactly one JSON object**, no prose, no markdown fences.

## Top-level shape
- Top-level keys = the template's `required_top_level_keys`, in that order, nothing extra, nothing missing.

## List items
- Every list item must include **all** of its `item_required_keys` from the template.
- Required-key lists are defined per field in the template (e.g. `critical_findings.item_required_keys`, `priority_actions.item_required_keys`).

## Enums
- Every enum field (`issue_type`, `severity`, `*status`, `production_impact`, `action_type`, `owner`, `priority`, `gap_type`, `volume_unit`, etc.) must be a string drawn **verbatim** from the template's `enums` / `enum_choices`.
- Match underscores and casing exactly. Prefer an explicit `other` / `unknown` / `not_applicable` / `no_*` bucket over an out-of-enum value.

## Ordering (apply before emitting — from template `ordering_rules`)
- Record lists (findings, risks, issues, events, sources, corrections): sort by their stable ID ascending.
- Action/priority lists (`priority_actions`, `action_plan`, `recommended_actions`): sort by `priority_rank`/`rank` ascending, 1 = highest. Secondary sort by target ID ascending where the template says so.
- Category-status lists: sort by `category_code` ascending.
- Any `category_impacts`/`affected_categories`/`category_sets` list: sort codes ascending within the list, hub casing preserved.

## Numeric precision
- All counts are **whole integers**.
- Use `0` (not `null`) for count fields that do not apply to a given record.
- Use `null` **only** where the template explicitly allows it (dates, `third_party`, `policy_section`, `missing_component`, etc.).
- Booleans (`production_ready`, `rolling_production_ready`) are JSON `true`/`false`, not strings.
- Dates are `YYYY-MM-DD` strings or `null`.

## IDs
- `matter_id`, `source_refs`/`record_refs`/`issue_refs`/`target_refs`/`blocking_refs`, `finding_id`/`risk_id`/`issue_id`/`event_id`/`source_id`/`entry_id`/`correction_id`/`action_id` must be copied **verbatim** from the hub. Never invent, reformat, or rename.

## Metric derivation
- Every field in `metrics` is computed by aggregation over that matter's hub rows (counts, sums, distinct-category sets). Do not estimate. Whole integers; list-of-codes metrics hold distinct, sorted codes.
