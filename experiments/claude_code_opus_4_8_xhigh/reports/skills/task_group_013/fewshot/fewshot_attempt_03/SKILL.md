---
name: cedar-ridge-intake
description: >
  Solve Cedar Ridge Intake Coordination Portal tasks — read-only healthcare
  intake/referral/transfer/program data reconciled into a single strict-schema
  JSON answer. Use when a task points at a portal base URL (GDPEVO_ENV_BASE_URL /
  <TASK_ENV_BASE_URL>) and asks for a JSON object following an
  input/payloads/answer_template.json, covering patient access verification,
  referral batch readiness/activation, dialysis transfer review, or chronic-care
  program enrollment.
---

# Cedar Ridge Intake Coordination — task solver

Each task gives you (1) a running read-only portal, (2) a natural-language
`prompt.txt` naming a target **id** (roster / referral batch / transfer batch /
program) and, (3) an `input/payloads/answer_template.json` that specifies the
**exact output shape and controlled vocabularies**. Your job: pull the source
facts from the portal, apply the domain rules, and emit **one JSON object** that
conforms to the template. The portal never returns a finished answer — every
graded field is derived by you.

## Workflow

1. **Reach the environment.** Read `environment_access.md` for
   `GDPEVO_ENV_BASE_URL` (no credentials). Use it wherever the prompt shows
   `<TASK_ENV_BASE_URL>`. Confirm reachability (`GET /health`). See
   `references/environment.md` for endpoints, the read-only SQL endpoint
   (`POST /query` with `{"sql": "..."}`), the full table schema, and the
   controlled vocabularies. **Prefer the SQL endpoint** — it exposes every column
   and supports joins.

2. **Read the task template first.** Open `input/payloads/answer_template.json`.
   It is authoritative for: required top-level keys, list ordering, item keys,
   every enum's allowed values, count-object keys, and any `required_value`
   constants (e.g. `task_id`, `batch_id`, `program_code`). Never invent keys or
   emit values outside an enum's allowed set. Read `prompt.txt` for the target id
   and any dates/service line to echo.

3. **Identify the task family** (see routing table) and open its rule file.

4. **Scope to the target id.** The DB holds many sibling batches/rosters/programs
   and `distractor referral` rows. Filter strictly by the prompt's
   `batch_id` / `roster_id` / `program_code`. Never let out-of-scope rows leak in.

5. **Gather + compute.** Pull the needed tables for the in-scope entities and
   apply the family rules field by field. The logic is deterministic — write a
   small script (curl/python against `/query`) that fetches, computes, and
   assembles the object rather than eyeballing rows. Recompute, don't guess.

6. **Format per template & self-verify** (checklist below). Output **JSON only**
   — no prose, no markdown fences — unless the template/prompt says otherwise.

## Task-family routing

Match the prompt + template top-level keys to one family, then follow its file:

| If the task is about… | Family | Rules file |
|---|---|---|
| New-patient **access verification** for an intake **roster**; insurance / prescription / pharmacy / lifestyle / overall risk / registration status | A | `references/family_intake_verification.md` |
| **Referral batch audit** for scheduling readiness; icd/duplicate/shared-insurance/records/imaging/auth, action plan, summary | B | `references/family_referral_readiness.md` |
| **Dialysis transfer** batch review; packet completeness/freshness, chair capacity feasibility, intake decision | C | `references/family_transfer_review.md` |
| **Chronic-care program enrollment** panel for a program code; eligibility, reason codes, cadence, monitoring package | D | `references/family_program_enrollment.md` |
| **Referral-to-chart activation**; readiness, blocker sets, duplicate handling, chart-artifact needs, correspondence, priority | E | `references/family_referral_activation.md` |

A held-out task is almost certainly a **sibling instance** of one of these
families (a different id). The rules are written as general predicates over
source columns, so they transfer — but always re-derive from the live data;
never copy any value from the training examples.

## Global output conventions (apply to every family)

- **Constants**: set `task_id` / `batch_id` / `roster_id` / `program_code` to the
  template's `required_value` (or the prompt's id). Echo dates/`service_line` from
  the environment (e.g. roster row), not from memory.
- **Ordering**: honor each template's stated ordering exactly — usually ascending
  by `referral_id` / `transfer_id` / `patient_id`; groups by `group_id`;
  anomalies by `insurance_id`. When a field is a "set" (issue/reason/blocker/
  artifact codes), order is not graded, but sorting ascending/alphabetical is the
  safe default (and some templates require alphabetical, e.g. artifacts).
- **Count objects**: include **every** enum key, zero-filled — do not omit zero
  counts. "By-pair" count lists (e.g. urgency×status) include only occurring
  (count ≥ 1) combinations, in the template's stated order.
- **Enums only**: every enum/code value must be from the template's allowed list.
  If your derived signal has no matching allowed value, you mis-derived — re-check.
- **IDs verbatim**: use uppercase IDs exactly as the portal returns them.
- **Nulls**: use `null` (not 0/"") where the template allows null, e.g.
  `first_checkin_days`, `priority_tier` for ready referrals.

## Recurring gotchas (these bite)

- **Filter to the target id** and drop `distractor referral` rows.
- **Chapter vs service_family** (families B/E): icd_chapter_mismatch is a
  *chapter* comparison; a code can have the right service_family but wrong chapter.
  In family E, the clinical-code check keys on *service_family* + *referral_reason*.
- **Transfer freshness reference date = that transfer's `requested_start_date`**,
  not "today" (family C). Most error-prone parameter in the whole task set.
- **`notes='possible duplicate'`** is the duplicate-review flag in family E (and a
  distractor in family B, where duplicates are structural: same patient+ICD).
- **`existing_chart` vs artifact freshness** (families D/E) are independent:
  a patient can have `existing_chart==1` yet need every artifact recreated
  (artifact "needs creation" ⟺ absent OR `status != 'current'`).
- Records/imaging/auth truth comes from the **referrals integer flags**, not the
  documents table.
- Some fields are **INFERRED** (a branch no training batch exercised) — the rule
  files mark them. Apply the documented inference, and if the live data hits an
  unexercised branch, reason from the enum names + field semantics.

## Verification checklist (before returning)

- [ ] Output is valid JSON, only the required top-level keys, JSON-only if required.
- [ ] Every list has the right length and ordering; every constant matches the template.
- [ ] Every enum/code value ∈ the template's allowed set.
- [ ] Count objects are internally consistent: totals equal list lengths; each
      `*_counts` object sums to the number of rows; per-pair counts sum to the
      follow-up/total; zero keys present.
- [ ] Cross-field consistency: e.g. a referral in `ready_to_schedule`/`ready`
      has empty issues; a `blocked` referral has a blocking code; `missing_chart_
      artifacts` matches the artifact reason codes; ineligible program candidates
      have empty artifact lists.
- [ ] You scoped strictly to the target id and excluded distractors.
