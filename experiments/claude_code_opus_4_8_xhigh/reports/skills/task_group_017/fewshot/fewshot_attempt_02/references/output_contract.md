# Conforming to the task's answer_template.json

The template in the task's `input/payloads/answer_template.json` is the **only** authority for
output shape. It is a *description* of the schema (keys, types, enums, ordering, precision), not
an example answer — it contains no values to copy. Different tasks use different top-level keys
(e.g. `critical_findings` / `top_risks` / `readiness_statuses` / `retention_events`), different
enum vocabularies, and different metric names. Re-read it every run and follow it literally.

## Checklist
1. **Top-level keys.** Emit exactly the `required_top_level_keys`, no more, no fewer. First key
   is normally `matter_id` (echo the hub/task matter id verbatim).
2. **Enums only.** For every enum field, use a value from that field's list in *this* template.
   Never carry an enum value over from another task. If the closest concept isn't offered, pick
   the nearest allowed value (e.g. an `other`/`unknown`/`not_applicable` member) — do not invent.
3. **Ordering.** Apply every rule in `ordering_rules` exactly: sort findings/risks by their id or
   by `priority_rank`/`rank` ascending (1 = highest); sort category lists by `category_code`;
   sort `source_refs`/`issue_refs`/`target_refs` and every category-code list **ascending**.
4. **Required item keys.** Each list item must contain exactly its `item_required_keys`. Include
   count fields even when `0`; include nullable fields as `null` when not applicable.
5. **Precision.** All counts are whole integers. Booleans are real booleans. Dates as
   `YYYY-MM-DD` or `null` per the template.
6. **IDs verbatim.** Use stable hub record IDs exactly as returned (matter, source, event, QC
   finding, document, privilege entry, action, category). `finding_id`/`risk_id` should anchor on
   the single hub record that best represents the issue; `source_refs` lists all supporting IDs.
7. **Metrics.** Provide every key in the metrics object. Derive values from the material set
   (see `domain_playbook.md`); use `0` / `[]` / `false` where the matter has no such fact; obey
   each metric's own description (some are scoped to "selected blockers only").
8. **Coverage vs findings.** Category-coverage/status lists summarize *per category* (union of
   supporting IDs, a representative status/impact/action, an open-issue count); findings/risks
   lists are *per issue*. Keep them consistent — every category referenced by a finding should
   appear in coverage, and vice-versa.
9. **Output hygiene.** Return **one** JSON object and nothing else — no markdown fences, no prose
   before or after. Valid JSON (double quotes, no trailing commas, no comments).

## Common shapes across this task family (names vary — always defer to the template)
- **matter_id** — string.
- **findings / risks / issue ledger** — one object per material issue: an anchoring id, issue
  type, severity/risk level, status, source status, production impact, affected categories,
  supporting refs, count fields (document/withheld/logged/unlogged/volume), and a recommended
  action (often with owner/priority).
- **category coverage / statuses / readiness** — one object per affected category: status,
  production impact, supporting refs, recommended action, open-issue count.
- **retained_or_available_sources / available_archives** — remediation sources that limit loss
  (empty list when none remain).
- **privilege_corrections / communication_gaps** — task-specific breakouts when present.
- **metrics** — a fixed object of derived integer counts + a readiness boolean.
- **priority_actions / action_plan** — ranked actions with action_type, owner, priority
  (P0–P3), target refs, affected categories (and `due_days` when the template asks).

## Self-check before returning
- Does the JSON validate, with exactly the required top-level keys?
- Is every enum value drawn from this template's lists?
- Are all lists sorted per `ordering_rules`, and all id/category lists ascending?
- Are all counts integers, `unlogged = withheld − logged`, readiness `false` if any gap exists?
- Are all IDs real hub IDs, with decoys excluded and material issues covered?
- No prose outside the single JSON object?
