# Licensing Board Review Decision Skill

## When to use

Use this skill for any task that asks you to act as a licensing examiner / analyst for the State licensing environment and return a structured JSON decision package. The skill applies whenever the task points you at the shared licensing environment (the `<TASK_ENV_BASE_URL>` / `task-env` service) with a defined set of `GET /api/...` endpoints and (optionally) `POST /api/sql`, and asks for a JSON answer conforming to an `answer_template.json`.

The skill is reusable across the review families the environment supports:
- **Contractor batch eligibility review** (a set of `C-…` applications: bonds, insurance, license history, violations, correspondence, inspections, endorsements, experience).
- **Restricted liquor-license staff package** (a single `L-…` application at a `LOC-…` location: settlements, privileges, incidents, site evidence, control obligations).
- **Alcohol renewal manual-review queue** (a ranked queue over `AL-…` licenses with a release boundary date: licensees, violations, renewal rules).

The shape of the answer differs per family and is fully described by that task's own `answer_template.json`. This skill never hard-codes per-task values — it tells you how to find, verify, and decide.

## Inputs you will be given

For each task, the staged working tree contains:
- a `prompt.txt` that names the role, the target identifiers (application/license/location ids or an id range), any review date or release boundary, and the endpoints to use;
- an `input/payloads/answer_template.json` that is the **authoritative schema** — its required keys, allowed enum values, ordering rules, length constraints, and "additional output" restrictions define exactly what JSON you may return;
- an `environment_access.md` describing how to reach the running environment over the network (base URL, any required request header, the allow-list of endpoints).

Read the prompt, the template, and `environment_access.md` before touching the environment.

## Procedure

1. **Parse the prompt for the contract.** Extract: review family, target identifiers / id range, the review/boundary date (if any), the target queue/batch size (if any), and which endpoints the prompt calls out. The prompt's endpoint list is authoritative for that task; do not call endpoints it does not list.

2. **Read the answer template as the schema.** Before producing any output, internalize the template's: required top-level keys, per-field allowed enum values, list ordering rules (ascending lexical, by date, by rank, "operational sequence", etc.), required list lengths, and the explicit "do not include prose / markdown / extra keys" clause. When two families look similar (e.g. two liquor staff-package tasks) **do not assume the codes match** — the enum vocabularies differ between tasks; always re-read that task's template.

3. **Reach the environment the way `environment_access.md` says.** Use the documented base URL and the allow-listed endpoints exactly. If `environment_access.md` requires a header for an endpoint (e.g. `X-Task-Token` for `POST /api/sql`), send it. Do not invent paths, do not hit endpoints outside the allow-list, and do not attempt paths the prompt did not list for that task. Treat the base URL placeholder literally — substitute it from `environment_access.md`.

4. **Pull the policies first.** `GET /api/policies` (every family uses it) gives the current policy baseline. Several families carry a `policy_impacted` flag whose semantics — *"True when a current 2025 policy standard creates a deficiency/flag that would not have applied under the prior baseline"* — must be read from the policies endpoint, not guessed. Always fetch policies before deciding policy-impacted fields.

5. **Fetch the family's record endpoints.** Pull every endpoint the prompt lists for that family (one request per endpoint). For batch tasks, fetch the full collection once and index by id rather than re-fetching per item.

6. **Correlate records to targets.** For each target id in the prompt, gather its application/core record plus all related records (bonds, insurance, history, violations, correspondence, inspections / settlements, privileges, incidents, site-evidence / licensees, violations). Match on the id fields the data uses. For the alcohol queue, also handle **non-exact address matches** (old/alternate location records) — note them as `close_address`/`uncertain` confidence rather than forcing an exact match.

7. **Apply the family decision rubric.** See `references/decision_rubric.md` for the reusable per-family decision logic (deficiency detection, risk tiering, posture/next-step determination, policy-impact reasoning, boundary-date handling, and the optional `POST /api/sql` cross-check). The rubric is the procedure, not the answers — it maps *evidence in the records* to *codes in that task's template*, so the same rubric produces different output per task.

8. **Build the JSON exactly to the template.** Emit only the keys the template lists, each field drawn from the template's allowed enum values, every list in the template's required order, with the required list lengths (batch size / queue size), and `[]` where the template says to use empty arrays. For summary objects, derive counts and id lists *from the application-level decisions you just made* so they stay internally consistent (e.g. `approve_count` + `hold_count` + `deny_count` = batch size; `high_risk_application_ids` = every application you tiered `high`, sorted).

9. **Return only the JSON.** No prose, no markdown fences, no citations, no keys outside the template — the templates consistently forbid exactly these. Validate against your checklist before returning.

## Critical pitfalls to avoid

- **Do not copy codes or ids from any train example into a live answer.** Each task's allowed values live in its own `answer_template.json`. A code that is valid in one contractor batch may not exist in another; the liquor vocabularies differ between the two liquor tasks. Always read the live template.
- **Do not skip `GET /api/policies`.** `policy_impacted` is baseline-relative and unguessable without it.
- **Honor list order and length precisely.** "ascending lexical order", "ascending by rank with no gaps", "sort by date ascending then id ascending", "operational sequence", and a fixed `required_length` / `length` are all scored constraints — re-sort every list before returning.
- **Keep summary fields consistent with the per-item decisions.** They are derived, not independent.
- **Use `POST /api/sql` only as an optional verification/cross-check** and only if `environment_access.md` documents the required token header — never as a way to bypass the public endpoints or to mutate data.

## Files in this skill

- `SKILL.md` — this entry point.
- `references/decision_rubric.md` — reusable per-family decision logic and environment protocol.
