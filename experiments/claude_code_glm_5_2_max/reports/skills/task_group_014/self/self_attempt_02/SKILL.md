---
name: northstar-payer-operations
description: Solve Northstar Health Plan payer-operations determination tasks against the shared read-only environment — UM prior-auth, pharmacy appeal + assistance, claim repricing, peer-to-peer, and therapy margin queue — and return one strict JSON object matching the task's answer template. Read BEFORE working any task whose prompt references Northstar, a TASK_ENV base URL, the /sql/query bearer token, or an input/payloads/answer_template.json.
---

# Northstar Payer Operations — Structured Determination Skill

This skill produces one strict JSON object for a Northstar Health Plan payer-operations
task. Each task points at a shared read-only environment, names a target business record,
and ships an `answer_template.json` that defines the exact output contract. The work is
always: read the inputs → query only the target record(s) from the environment → apply the
decision rules → emit JSON that matches the template, including a `basis_audit` trail.

## When to use

Use this skill for any task that:
- references Northstar Health Plan, utilization management (UM), appeals, payment
  integrity, peer-to-peer (P2P), or a therapy margin queue; **or**
- gives a `<TASK_ENV_BASE_URL>` / `task-env` environment, a `POST /sql/query` bearer token,
  and an `input/payloads/answer_template.json`.

Do **not** use this skill for tasks about a different payer or a different environment.

## Inputs — read all three before doing anything else

For the target task directory, read every file under `input/`:

1. `input/prompt.txt` — the business request and the reporting date.
2. `input/payloads/task_context.json` — the **target business ID** and operational context.
   The target ID lives in different keys depending on archetype: `target_business_id`,
   `target_appeal_id`, `target.claim_id` / `target.case_id`, `work_item.case_id`,
   `business_id`, or `finance_memo.queue_row_ids`. Find it and use **only** it to filter.
3. `input/payloads/answer_template.json` — the **output contract**. It is the source of
   truth for required fields, enum choices, list ordering, and numeric precision. Treat any
   conflict between this skill and the template in favor of the template.

## Environment access — `environment_access.md` is the only network source

- Read the staged `environment_access.md` (at the repo/run root, beside `train_tasks/`) for
  the base URL, the bearer token, and the allowed endpoint list. Use **only** those
  endpoints. Never invent endpoints, tokens, or base URLs.
- `GET /api/...` business endpoints are open. `POST /sql/query` requires
  `Authorization: Bearer <token>`.
- SQL call shape: `POST /sql/query` with JSON body `{"sql": "<SELECT ...>"}` and the bearer
  header. The response is `{"columns": [...], "rows": [...], "row_count": N, "limited": bool,
  "max_rows": 500}`. Errors come back as `{"error": "sql_error"|"invalid_sql", "message": ...}`.
- The SQL engine is standard SQLite: `LIKE`, `JOIN`, `GROUP BY`, `COUNT/SUM/ROUND`, and
  subqueries all work. Results are capped at **500 rows** — always filter with `WHERE` on the
  target ID so you stay well under the cap.
- **API only.** Never inspect environment source files, generated data files, SQLite files,
  manifests, or setup scripts. If a prompt repeats this prohibition, treat it as binding.
- Do **not** call any judge or scoring endpoint — none is available to this skill.

## Operating procedure

1. **Read the three inputs** (above). Identify the archetype from the target ID prefix and
   the template shape (see Archetypes below, and `decision_rules.md` for full logic).
2. **Discover the schema once** via `GET /api/tables` if you have not already this session;
   cross-check against `data_model.md`. The environment holds 19 tables.
3. **Gather only the target record(s).** Filter every query by the target business ID (or the
   explicit `queue_row_ids` list for margin tasks). The environment contains many records you
   must ignore: parallel `*-TR-*` (train), `*-TE-*` (test), and `*-D-*` / `SM-D-*`
   (distractor) rows, plus duplicate benchmark rows and non-matching "Distractor" schedules.
   Never let a distractor bleed into the answer.
4. **Apply the decision rules** for the archetype (`decision_rules.md`). Compute derived
   values (units, currency, ratios, deadlines) using the formulas there, rounded to the
   precision the template requires.
5. **Build the `basis_audit`** (`basis_audit.md`): pick the `source_precedence` rule for the
   archetype, then list `controlling_record_ids`, `exception_record_ids`, and the merged
   `precedence_record_order` using the ordering rules.
6. **Emit exactly one JSON object** matching the template. No markdown, no prose, no comments
   outside the JSON. Respect every field's type, enum, ordering, precision, and null rule.

## Archetypes (one-line map; full logic in `decision_rules.md`)

| Archetype | Target shape | Source-precedence rule |
|---|---|---|
| UM nurse prior-auth determination | `CASE-*`, physical/speech/occupational therapy | `current_clinical_records_over_stale_export` |
| Pharmacy coverage appeal + manufacturer assistance | `APPEAL-*` / `APL-*`, specialty drug | `payer_appeal_before_manufacturer_assistance` |
| Claim repricing / payment integrity | `CLAIM-*`, imaging/surgery | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer final summary | `P2P-*`, imaging | `new_patient_specific_p2p_information` |
| Therapy margin queue | `QUEUE-*`, margin rows | `margin_threshold_then_charge_sensitivity` |

A sixth rule, `appeal_deadline_then_clinical_then_payment_integrity`, applies when a task's
controlling factor is the appeal deadline and routing must weigh deadline → clinical urgency
→ payment integrity in that order.

## Output discipline (applies to every archetype)

- **One JSON object only.** No trailing prose, no markdown fences, no comments.
- **Use the template as the contract.** Required top-level keys, nested required keys, and
  enum choices are non-negotiable. `additional_fields_allowed: false` means emit no extra
  keys; if additional properties are allowed, you may still omit them.
- **Ordering** matters and is graded:
  - CPT code lists → ascending CPT code (split comma-strings from the DB into a sorted list).
  - document_id lists → ascending document_id.
  - margin-queue rows → the exact order of `task_context.finance_memo.queue_row_ids`.
  - segment lists → alphabetical by enum value.
  - criterion / record ID lists → ascending ID unless the template says otherwise.
- **Null vs empty:** use JSON `null` (not `""`) for absent modifiers, absent auth numbers,
  and dates that do not apply. Use `0` only for genuine zero counts/units.
- **Precision:** currency → dollars rounded to 2 decimals; ratios → 4 decimals (per
  template); dates → `YYYY-MM-DD` (or `YYYY-MM` for periods); units → integers.
- **Currency** values are JSON numbers in USD (e.g. `1234.56`), never strings.
- **Copy IDs verbatim** from the environment (`case_id`, `auth_number`, `appeal_id`,
  `p2p_id`, `document_id`, `month_id`, benchmark `source_name`/`source_version`). Do not
  reformat or rename them.

## Contamination & scope guard

- Work only from the staged `/work` inputs plus the live environment via
  `environment_access.md`. If you find unexpected files in `/work` (anything outside
  `environment_access.md` and the `train_tasks/` tree), stop and report instead of proceeding.
- Never read the environment's backing files (SQLite, manifests, setup scripts) — API only.
- Never mix records across targets. One task = one target business ID (or its explicit
  queue-row list).

## Supporting files (read the ones relevant to your archetype)

- `data_model.md` — the 19 tables, key columns, natural keys, and how they join.
- `decision_rules.md` — per-archetype decision logic, derived-value formulas, and the full
  `source_precedence` taxonomy.
- `basis_audit.md` — how to assemble `source_precedence`, `controlling_record_ids`,
  `exception_record_ids`, and `precedence_record_order` with their ordering rules.
- `queries.md` — reusable, parameterized SQL templates per archetype (substitute the target
  ID; never hardcode a specific record's answer values).
