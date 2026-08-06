---
name: licensing-review-decisions
description: >
  Produce structured regulatory decisions (contractor eligibility batches,
  restricted liquor-license staff packages, alcohol renewal manual-review queues)
  by reading records from a shared licensing data service and emitting ONLY JSON
  that conforms exactly to the task's answer_template.json. Use whenever a prompt
  casts you as a licensing examiner/reviewer, points at a task environment
  (<TASK_ENV_BASE_URL> + /api/... endpoints, optional POST /api/sql), and asks for
  an answer matching input/payloads/answer_template.json.
---

# Licensing-review decisions

## What this family looks like
A prompt assigns a regulatory persona (Senior Licensing Examiner, staff reviewer,
Renewal Unit analyst), names a **small set of target ids** (and sometimes a target
location and a review/boundary date), lists **API endpoints** on a shared licensing
environment, and requires an answer that matches `input/payloads/answer_template.json`
— **JSON only, no prose/markdown/citations/extra keys.**

Three sub-types seen; the method is the same, only the schema and codes differ:
- **Contractor batch eligibility** → `application_decisions[]` + `summary`
  (APPROVE/HOLD/DENY, deficiency codes, required actions, risk tier, policy_impacted).
- **Restricted liquor staff package** → one flat object (recommended_posture,
  same_premises_basis, covered risks, verification gaps, standard obligations,
  location controls, first_90_day_plan, escalation triggers).
- **Alcohol renewal manual-review queue** → ranked `queue[]` + `summary`.

## The one rule that matters most
**`answer_template.json` is the contract. Read it first and obey it literally.**
It fixes the exact top-level keys, the item schema, the **allowed enum values**
(which differ between otherwise-similar tasks — never carry codes over from another
task), the **ordering/dedup** rule for every list, and which ids to include. Use
empty arrays (never placeholders) when nothing applies. Emit only the keys it shows.

## Workflow
1. **Read the prompt and the template.** Extract: target ids, target location (if
   any), the review/boundary date, and which endpoints are allowed. Read the
   template's schema, enums, and ordering rules end to end.
2. **Load environment access** from `environment_access.md`: substitute
   `GDPEVO_ENV_BASE_URL` for every `<TASK_ENV_BASE_URL>`; grab the
   `X-Task-Token` for SQL. Only call endpoints the prompt/env file allow.
   `scripts/licensing_env.py` handles discovery, GET, filtered GET, and SQL.
3. **Pull the records for the targets.** Filter strictly to the target
   ids/location — tables are full of distractor rows (`-DIS-`, `-TE*-`, other
   `-TR*-` batches). **GET responses cap at ~200 rows**, so for the big tables
   (bonds, insurance, contractor/alcohol violations, correspondence, incidents,
   settlements) use `POST /api/sql` with a `WHERE` clause on the targets so no row
   is silently dropped. Always fetch `/api/policies` (and `/api/renewal/rules` for
   renewals) and parse each `details_json` for live thresholds/flags.
4. **Apply the sub-family playbook** (`references/decision_playbooks.md`): evaluate
   each requirement against the current record, map each finding to the matching
   code in *this template's* enum, choose the determination/posture/risk with a
   consistent ladder, and set derived flags (e.g. `policy_impacted`).
5. **Build the summary as a derived view** of your final per-item decisions so the
   counts/id-lists cannot disagree with the items.
6. **Order, dedupe, and validate** every list per the template, then emit JSON only.

## Reference material (in this skill)
- `references/environment_and_data_model.md` — how to reach the service, the SQL
  contract, the ~200-row GET cap, every record family's fields and join keys, and
  the policy/rule `details_json` keys.
- `references/decision_playbooks.md` — step-by-step method for each sub-family,
  including the deficiency→required-action mapping, determination/posture/risk
  ladders, `policy_impacted`, violation-matching confidence, and summary derivation.
- `scripts/licensing_env.py` — stdlib helper. Examples:
  - `python scripts/licensing_env.py survey` — base URL, token presence, row counts.
  - `python scripts/licensing_env.py filter /api/contractor/applications application_id C-XXX-001,C-XXX-002`
  - `python scripts/licensing_env.py sql "SELECT * FROM contractor_bonds WHERE application_id='C-XXX-001'"`
  It reads `environment_access.md` automatically (or pass `--env <path>`).

## Do / don't
- **Do** treat the target ids, target location, and review/boundary date as hard
  filters; read thresholds live from `/api/policies`; keep summaries internally
  consistent; sort/dedupe exactly as specified.
- **Do** apply one decision ladder consistently across a batch — internal
  consistency beats second-guessing any single borderline call.
- **Don't** hardcode base URL, token, thresholds, or enum vocabularies; don't reuse
  another task's codes; don't include distractor rows, prose, citations, markdown,
  or keys the template doesn't list; don't trust an unverified/stale correspondence
  letter as satisfying a requirement; don't let a >200-row GET silently hide a
  target's records.
