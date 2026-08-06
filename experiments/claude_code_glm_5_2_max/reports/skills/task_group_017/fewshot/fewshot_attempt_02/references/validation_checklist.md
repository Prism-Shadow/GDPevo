# Pre-Emit Validation Checklist

Run this checklist against the assembled JSON object and the task's
`answer_template.json` before returning the answer. The final output must be exactly one
JSON object with no surrounding prose or markdown fences.

## 1. Top-level shape
- [ ] Every key in `required_top_level_keys` is present.
- [ ] No extra top-level keys (unless the template explicitly permits extras).
- [ ] `matter_id` matches the matter under analysis (from the context payload, confirmed
      via `GET /api/matters`).

## 2. List item completeness
- [ ] Every list item contains every key in the corresponding `item_required_keys`.
- [ ] No `null` where the field type is a plain integer/string/enum (use `0` for
      not-applicable counts; use `null` only where the field type explicitly allows it,
      e.g. optional date/string fields).

## 3. Enum compliance
- [ ] Every coded field value is a member of the matching enum set in the template.
      Check: `issue_type`, `severity`/`risk_level`, `status`/`finding_status`/`risk_status`/
      `readiness_status`, `source_status`, `production_impact`, `category_status`,
      `action_type`, `owner`, `priority`, `corrected_disposition`, `privilege_status`,
      `correction_type`, `volume_unit`, `availability_status`, `active_system_issue`, etc.
- [ ] No invented enum values. If a hub concept lacks an exact match, use `other` or the
      closest permitted value.

## 4. Ordering
- [ ] Each list sorted per its `ordering_rule` (ascending by stable ID, or by
      `priority_rank`/`rank` with 1 = highest).
- [ ] Every `category_impacts` / `affected_categories` list sorted ascending.
- [ ] Every `source_refs` / `record_refs` / `target_refs` / `blocking_refs` /
      `issue_refs` list sorted ascending and deduplicated.
- [ ] `metrics.categories_with_open_gaps` / `categories_with_open_risk` sorted ascending
      and deduplicated.

## 5. Numeric precision
- [ ] All counts are whole integers (no floats).
- [ ] `unlogged` = `withheld − logged` and is never negative (use `0` otherwise).
- [ ] `due_days`, `priority_rank`, `rank`, `retention_period_months`, `retention_years`,
      `volume_count` are whole integers where required.
- [ ] Booleans (`rolling_production_ready` / `production_ready`) are JSON `true`/`false`.

## 6. Provenance / no fabrication
- [ ] Every record ID in the answer exists in a hub endpoint response for this matter.
- [ ] Every category code exists in `GET /api/subpoena-categories` for this matter.
- [ ] Every count/date/status is derived from hub data, not from a train answer,
      evaluation file, environment source file, database file, or manifest.
- [ ] No task-specific answer values (record IDs, counts, custodian names, action IDs)
      were copied from any other source.

## 7. Cross-consistency
- [ ] Metrics re-derived from source tables match the values implied by the findings list.
- [ ] `categories_with_open_gaps` / `affected_category_count` equals the distinct count of
      categories appearing in findings with an open status.
- [ ] Every category appearing in a finding's `category_impacts` is represented in the
      category-coverage / category-statuses list (when the contract requires it).
- [ ] Action plan `target_refs` and `category_impacts` are consistent with the findings
      they remediate; P0/critical findings have a corresponding early-ranked action.

## 8. Output form
- [ ] Output is a single JSON object and nothing else: no prose, no markdown fences, no
      trailing comma, valid JSON.
