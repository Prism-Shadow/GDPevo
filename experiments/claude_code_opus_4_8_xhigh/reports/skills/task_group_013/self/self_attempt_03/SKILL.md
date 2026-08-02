---
name: cedar-ridge-intake-coordination
description: >-
  Complete a Cedar Ridge Intake Coordination Portal reconciliation task and
  return a single JSON object that conforms to a provided answer_template.json.
  Use whenever a prompt points at the "Cedar Ridge Intake Coordination Portal"
  (a read-only HTTP + SQL portal reached via <TASK_ENV_BASE_URL>) and asks you
  to audit / verify / review a named roster, referral batch, transfer batch, or
  program candidate list and emit structured JSON (patient-access verification,
  referral readiness audit, dialysis transfer review, chronic-care enrollment
  panel, or referral-to-chart activation). Covers how to reach the portal, which
  data source feeds each output field, the decision rules per task family, and
  the strict output contract (controlled vocab, ordering, summary counts).
---

# Cedar Ridge Intake Coordination Portal — Intake Reconciliation

## What these tasks are

Every task in this group is the same shape: you are handed a read-only
"Cedar Ridge Intake Coordination Portal" and asked to reconcile a **named work
unit** (a roster, a referral batch, a transfer batch, or a program candidate
list) against clinical/administrative data, then return **one JSON object** that
exactly follows the task's `input/payloads/answer_template.json`. The portal data
and the target vary per task; the *method* does not.

There are five recognizable task families. Identify which one you have from the
prompt and from the template's top-level keys, then follow that family's
playbook in `references/task_families.md`.

| # | Family | Prompt/target cue | Template top-level keys (distinctive) |
|---|--------|-------------------|----------------------------------------|
| A | New-patient access verification | "roster", `roster_id`, access/insurance verification | `roster_id`, `requested_service_date`, `service_line`, `patient_results`, `cohort_summary` |
| B | Referral readiness audit | "referral batch", audit before scheduling | `referral_reviews`, `icd_discrepancies`, `duplicate_groups`, `shared_insurance_anomalies`, `blocker_sets`, `ready_to_schedule`, `action_plan`, `summary` |
| C | Dialysis transfer review | "transfer batch", packet/chair capacity | `patients` (keyed by `transfer_id`), packet completeness, `requested_start`, `cohort_summary` |
| D | Chronic-care enrollment panel | "program `CODE`", candidates/eligibility | `program_code`, `as_of_date`, `patients`, `summary` |
| E | Referral-to-chart activation | "activation", which referrals move forward | `readiness_by_referral`, `clinical_code_discrepancy_referrals`, `blocker_sets`, `duplicate_handling`, `ready_referral_chart_needs`, `correspondence_queue`, `priority_order` |

## Operating procedure (every task)

1. **Read the prompt and the template first.** The template
   (`input/payloads/answer_template.json`) is the authoritative output contract:
   required keys, enum `allowed_values`, ordering rules, and constant/required
   values (e.g. `task_id`, `batch_id`, `roster_id`, `program_code`). Read any
   other payloads too (e.g. a `target_roster.json` listing patient ids).
2. **Resolve the base URL.** The prompt uses the placeholder
   `<TASK_ENV_BASE_URL>`. The real base URL is in `environment_access.md`
   (`GDPEVO_ENV_BASE_URL`, e.g. `http://task-env:9013/`). Use **only** the
   endpoints listed there. No credentials are needed.
3. **Identify the family** (table above) and open its playbook.
4. **Pull the work unit's data.** Prefer the read-only SQL endpoint
   (`POST /query`) to fetch **all** rows for the target in one shot — REST list
   endpoints paginate (default `limit` ~10) and can hide rows. Use the REST
   aggregators (`/patients/{id}`, `/chart/{id}`, `/transfers/{id}`) when you want
   everything about one entity at once. See `references/portal.md` for the schema
   and the field→source map.
5. **Apply the family decision rules** to each row, drawing every value from
   portal data. Map only to the template's controlled vocabulary.
6. **Assemble the JSON** in the exact shape, ordering, and key set the template
   specifies. Compute the summary/cohort counts from your own rows.
7. **Validate before returning** against the checklist below.
8. **Return JSON only** — no prose, no markdown fences, nothing outside the
   single JSON object (several prompts state this explicitly; treat it as
   universal).

## Rules that hold across all families

- **Constants come from the template, verified against the prompt.** Fields with
  a `required_value` / `constant` / `expected_value` (e.g. `task_id: "train_00X"`,
  `batch_id`, `roster_id`, `program_code`) must be emitted verbatim. The task id
  matches the task folder name; the batch/roster/program id matches the prompt's
  named target.
- **Controlled vocabulary only.** Every enum/status/reason/code value must be one
  of the template's `allowed_values` for that field. Never invent codes, never
  emit free text where an enum is required, never carry a raw DB value through
  unmapped (e.g. map coverage `status`/`auth_status` to the template's enum).
- **Ordering is part of correctness.** Honor each list's stated ordering:
  `ascending by <id>`, `alphabetical by code`, `highest priority first`, or
  "treat as unordered set." For unordered-set fields, still emit each code at
  most once (deduplicate). Use the portal's IDs verbatim, preserving their exact
  uppercase form as returned.
- **Emit every required key, including zero counts.** Count objects must contain
  **all** enum keys the template lists, with integer `0` where nothing matched.
- **Counts must reconcile.** Totals equal the number of rows; per-category counts
  sum to the total; a referral/patient is counted once per breakdown. Derive
  counts from the rows you actually emit, not from a separate pass.
- **Dates are `YYYY-MM-DD`.** Take service/requested dates from the record the
  prompt points to (e.g. the roster row), not from the prompt text.
- **Read-only.** Only GET the allowed endpoints and POST read-only `SELECT`
  statements to `/query`. Do not attempt writes.
- **Distractors exist by design.** Extra batches/rosters/programs, unrelated
  "distractor" referrals, and misleading free-text `notes` (e.g.
  `"possible duplicate"`) are planted. Filter strictly to the named target and
  decide from structured fields, not from `notes`.

## Pre-return validation checklist

- [ ] Output is a single JSON object; nothing printed outside it.
- [ ] All `required_*` / top-level keys present; constants match the template.
- [ ] Every enum/code value ∈ the template's `allowed_values`; sets deduplicated.
- [ ] Every list obeys its ordering rule; IDs use the portal's exact case.
- [ ] One row per required entity (roster patient / batch referral / transfer /
      candidate); none missing, none duplicated, target filter applied.
- [ ] Summary/cohort objects include all enum keys (zeros included) and reconcile
      with the emitted rows.
- [ ] Dates are `YYYY-MM-DD` and sourced from portal records.

## Reference files

- `references/portal.md` — endpoints, the read-only SQL interface, the full table
  schema, and the field→data-source map.
- `references/task_families.md` — the per-family playbooks: recognition, data to
  pull, decision rules for each output field, and the output contract.
