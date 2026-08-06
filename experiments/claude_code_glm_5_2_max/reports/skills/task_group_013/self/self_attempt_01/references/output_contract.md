# Output Contract & Self-Check

The deliverable is always **one JSON object** that conforms to the task's
`answer_template.json`. The template is the source of truth for shape, allowed values,
and ordering; this file captures the discipline that applies across every task family.

## Shape

- A single top-level JSON object. No prose, no markdown fences, no trailing commentary,
  no keys the template does not list.
- Emit every required top-level key and every required item key, even when a list is empty
  (emit `[]`) or a count is `0`. Empty sections are still required sections.
- Pin constant values from the template verbatim (`task_id`, `batch_id`, `roster_id`,
  `program_code`). Do not alter or omit them.

## Controlled vocabulary

- Every enum, reason code, and blocker code must come from the template's `allowed_values`
  / `allowed` list for that field. Never invent or synonym a value.
- When evidence is genuinely absent, use the template's "missing/unknown/none" member for
  that field rather than guessing. Do not emit `null` unless the field is explicitly
  `enum_or_null` / `integer_or_null`.

## Ordering

- Order each list exactly as the template states:
  - **ascending by id** — `referral_id`, `patient_id`, `transfer_id`, `group_id`,
    `insurance_id` (and `rank` ascending for priority lists).
  - **alphabetical by code/doc_type/artifact** — where specified.
  - **unordered set** — reason codes, blocker codes, issue codes, components. Emit these
    sorted anyway so output is deterministic; the grader treats them as sets.
- Use **uppercase IDs exactly as the portal returns them** (`REF0035`, `P001`, `TR0026`,
  `INS-27289`). Do not reformat, lowercase, or pad.

## Cohort summary

- All counts are integers.
- Include every bucket the template lists as a required key, with `0` where nothing falls
  in it.
- Reconcile totals: e.g. `total_patients` == sum of `counts_by_registration_status`;
  `total_referrals` == sum of `counts_by_readiness_status`;
  `total_candidates` == `eligible_count` + `ineligible_count`.
- Cross-tab lists (e.g. `counts_by_urgency_and_status`) must cover the cartesian product
  the template expects and be ordered as specified.

## Pre-submit self-check

Run this before emitting. If any answer is "no", fix it.

1. **Scope** — every entity the prompt requires is present; no distractor or out-of-scope
   row leaked in. Count of items matches the scoped set.
2. **Constants** — pinned top-level identifiers match the template/prompt exactly.
3. **Vocabulary** — every enum/code value is in the template's allowed list for its field.
4. **Keys** — every required key (top-level, per-item, summary) is present; no extra keys.
5. **Ordering** — each list is ordered per the template; set-arrays are sorted.
6. **IDs** — uppercase, exactly as returned by the portal.
7. **Counts** — integer; every bucket present; totals reconcile; cross-tabs complete.
8. **Traceability** — every non-obvious value traces to a portal field (not assumption).
9. **Format** — one JSON object only; no prose, no fences, valid JSON.

## Reducing HTTP round-trips

- Prefer `GET /patients/{id}` (the hub) over re-fetching each sub-resource for
  patient-scoped tasks.
- Use `POST /query` SQL for grouping/counts/duplicates instead of fetching and pivoting
  large lists by hand. Check `truncated` and raise limits or page if set.
- Cache list responses within the run; the portal is read-only so data does not change
  mid-task.
