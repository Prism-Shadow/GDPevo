# Output Contract & Failure Modes

The final deliverable is exactly one JSON object conforming to the task's `answer_template.json`. This file is the emission checklist and the list of mistakes to avoid.

## Emission checklist

Run every item before declaring done:

1. **One object, no prose.** Output is a single JSON object. No markdown fences, no leading/trailing commentary, no explanations. If the template has an `output_rule`, obey it literally.
2. **Top-level keys exact.** Include every key in `required_top_level_keys`, in that order, and no extra keys.
3. **Every list sorted.** Apply `ordering_rules` to each list. Defaults: record-ID-anchored lists ascending by that ID; `priority_rank`/`rank` ascending (1 = highest); category-code lists ascending, uppercase. Re-sort any `*_refs` / `*_impacts` sub-list ascending too.
4. **Enums exact.** Every status, severity, issue_type, source_status, production_impact, action_type, owner, and priority value is spelled exactly as in the template's enum lists. No synonyms, no mixed case, no values from a different template family.
5. **Stable IDs verbatim.** Every `finding_id`/`risk_id`/`issue_id`/`correction_id`/`event_id`/`source_id`/`action_id` and every member of a `*_refs` list is a real hub record ID, copied exactly. Never invent, renumber, or pretty-print IDs.
6. **Counts are whole integers.** All counts integers; `0` where not applicable (per the template's field notes). No floats, no strings where integers are required.
7. **Nulls only where allowed.** Use `null` only for fields the template marks nullable (dates, `third_party`, `policy_section`, `missing_component`, `cutoff_date`, etc.). Required enum/count fields are never null.
8. **Metrics cross-checked.** Each numeric metric recomputed a second way (SQL aggregate vs. summing the record list). `unlogged = withheld − logged` applied only over the selected blockers. `*_ready` boolean set after the issue set is final.
9. **Scope correct.** Only material/non-complete items appear in findings/risks/issues/category-status lists, unless the template explicitly demands full coverage. Pre-hold policy losses are reported as facts, not as P0/P1 actions.
10. **Category universe respected.** Every category code emitted exists in the matter's `subpoena_categories` set. No orphan codes.

## Common failure modes (avoid)

- **Summing all privilege entries instead of only incomplete-log blockers.** Read the metric's field note; apply the filter before summing.
- **Treating pre-hold policy destruction as a preservation breach.** It is `no_action` / low risk. Only post-hold loss and should-exist-missing are preservation risks.
- **Mixing enum vocabularies across template families.** The gap-analysis `issue_type` list differs from the dashboard `issue_type` list; the retention `action_type` list differs from the readiness `action_type` list. Use the current template's list only.
- **Unsorted or wrongly-sorted lists.** Sort by the field the `ordering_rules` name, not by insertion order. Re-sort nested ID/category lists.
- **Inventing IDs or counts to fill gaps.** If the hub has no record for something, omit it (or use `0`/`null` per the field note) — do not fabricate.
- **Including ready/closed items in the critical-findings list.** That list is for open material defects.
- **Setting `production_ready = true` while open P0/P1 issues remain.** The boolean must reflect the finalized open-item set.
- **Reading non-hub sources.** Local env files, DB files, seeds, manifests, setup scripts, generated data, hidden notes, and answer/eval files are off-limits. Only `environment_access.md` (for network access) and the task `input/` payloads are readable.
- **Emitting prose around the JSON.** Even a single sentence before/after the object can fail a strict parser.
