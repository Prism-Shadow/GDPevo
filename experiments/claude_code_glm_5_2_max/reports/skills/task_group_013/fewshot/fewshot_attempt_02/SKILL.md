---
name: cedar-ridge-intake-audit
description: Audit a Cedar Ridge Intake Coordination Portal batch (patients, referrals, transfers, or program candidates) and return a single JSON object that conforms to a staged answer_template.json. Use for any task pointing at the Cedar Ridge portal that demands template-conformant, controlled-vocabulary JSON output with cohort/summary counts.
---

# Cedar Ridge Intake Coordination — Portal Audit

## When to use

Use this skill for any task that:

- Points you at the **Cedar Ridge Intake Coordination Portal** (the base URL is given in `environment_access.md`; prompts refer to it as `<TASK_ENV_BASE_URL>`).
- Asks you to audit a **batch, roster, or program** of intake records — patients, referrals, transfers, or program candidates.
- Requires a **single JSON object** whose shape is defined by an `answer_template.json` staged at `input/payloads/answer_template.json`.
- Demands **JSON only** in the final response (no prose, no markdown fence).

If any of these is false, this skill does not apply.

## What you are given (per task)

- `prompt.txt` — names the batch/roster/program id, the target entities (explicit id list, or "all candidates for program X"), any requested service / as-of date, and the audit objective in plain language.
- `input/payloads/answer_template.json` — the **authoritative schema** for your output. It declares required top-level keys, per-item required keys, `allowed_values` (controlled vocabulary), ordering rules, count-key sets, and where `null` or empty lists are permitted.
- `input/payloads/` may also carry a manifest such as `target_roster.json` (roster id + patient id list + a pointer to the environment).
- `environment_access.md` — the **only** source for the live base URL and the allowed endpoint set.

Different tasks use **different schemas and different audit objectives.** Never assume a prior task's shape or token set.

## Core workflow

1. **Read the prompt.** Extract the batch/roster/program id, the target entity list (or "all candidates"), any requested service date / as-of date, and the objective.
2. **Read the template as a contract.** Record: required top-level keys; required item keys; every `allowed_values` set (the only tokens you may emit); any `required_value` / `expected_value` / `constant` (must be reproduced exactly); ordering rule per list; count-key sets; and where `null` / empty list is permitted.
3. **Resolve the base URL** from `environment_access.md` and substitute it for every `<TASK_ENV_BASE_URL>` in the prompt. Use **only** the endpoints listed in that file.
4. **Fetch the data** the objective requires. Use REST endpoints for targeted lookups and `POST /query` (read-only SQL) for batch reconciliation. See `references/portal_model.md` for the endpoint map, REST response shapes, and the full table/field model — the field names there tell you which columns carry the policy signals.
5. **Apply the audit decision logic** to map raw portal records onto the template's controlled tokens. See `references/decision_rules.md` for the known audit families and their evidence→token mappings. For anything not covered, read the relevant portal record's policy fields and map to the closest template token; do not invent tokens.
6. **Assemble the JSON** per `references/output_discipline.md`: correct keys, controlled values only, declared ordering, integer counts, `null` / `[]` where the template allows, no extra keys.
7. **Self-validate** against the template before returning (see the checklist in `references/output_discipline.md`): every required key present, every value in `allowed_values`, every list ordered as specified, every count a correct integer, summary/cohort counts consistent with the item list.
8. **Return the JSON object only.** No prose, no commentary, no code fence.

## Principles that always apply

- **The template is the contract.** When the template and your intuition disagree, the template wins.
- **Controlled vocabulary only.** Emit only strings that appear in the template's `allowed_values` (or a documented `required_value` / `expected_value` / `constant`). Never invent tokens or free-text values.
- **Ordering is graded.** Sort every list exactly as the template specifies (ascending id, alphabetical, "unordered set" — still emit it consistently sorted, e.g. ascending).
- **Counts are integers** and must reconcile with the item list (a count map's values sum to the total where the template implies it; include every required count key even when its value is 0).
- **`null` and `[]` are meaningful.** Use them where the template permits `enum_or_null` / `integer_or_null` / empty lists. Never omit a required key.
- **Dates are `YYYY-MM-DD`.** IDs are uppercase, exactly as the portal returns them.
- **No fabrication.** Every value must trace to a portal record. When a record is absent, use the "missing" / "unknown" / "not_applicable" token the template provides.
- **No prose in the final answer.** JSON only.

## References

- `references/portal_model.md` — endpoint map, REST response shapes, the read-only SQL endpoint, and the full underlying table/field data model.
- `references/decision_rules.md` — per-audit-family decision logic: which portal evidence maps to which template token.
- `references/output_discipline.md` — assembly rules, ordering, counting, null/empty handling, and the pre-submission validation checklist.
