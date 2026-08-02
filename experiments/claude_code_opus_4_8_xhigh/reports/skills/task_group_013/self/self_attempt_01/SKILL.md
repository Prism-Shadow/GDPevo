---
name: cedar-ridge-intake-audit
description: >-
  Produce the strict-JSON audit/verification report for a Cedar Ridge Intake
  Coordination Portal task. Use whenever a task points at the Cedar Ridge intake
  portal (`<TASK_ENV_BASE_URL>`, endpoints like /patients, /referrals,
  /transfers, /programs/{code}/candidates, /chart, /icd, /documents, POST /query)
  and asks for a single JSON object that follows a provided
  `answer_template.json` — new-patient access verification, referral readiness /
  referral-to-chart activation, dialysis transfer review, or chronic-care
  enrollment panels. Covers any batch / roster / program of that family, not just
  a specific one.
---

# Cedar Ridge Intake Coordination — Audit Report Builder

## What this family of tasks is

Every task in this family hands you:

1. A **prompt** naming the Cedar Ridge Intake Coordination Portal at
   `<TASK_ENV_BASE_URL>` and one **target** — a referral **batch** (e.g.
   `ORTHO-JUN-01`, `PULM-JUN-02`), an intake **roster** (`NPI-JUN-01`), a
   transfer **batch** (`DIAL-WINTER-01`), or a **program** code
   (`DMHTN-2026A`). The IDs vary per task; the portal holds many more targets
   than any one task names, so never assume a fixed target.
2. An **`answer_template.json`** (under the task's `input/payloads/`) that is the
   binding output contract: exact top-level keys, per-item keys, enum
   vocabularies, ordering rules, and required constant values.
3. **`environment_access.md`** giving the base URL and the allowed endpoints.

Your job: read the portal, apply the archetype's decision logic, and emit **one
JSON object** that conforms to the template exactly. **Output JSON only — no
prose, no markdown fences, no comments.**

## Operating procedure

1. **Read the contract first.** Open the task's `answer_template.json` and list
   every required key, every enum's allowed values, every ordering rule, and
   every `required_value`/`constant` (`task_id`, `batch_id`, `roster_id`,
   `program_code`). The template — not this skill — is the source of truth for
   shape and vocabulary; if they ever disagree, follow the template.
2. **Resolve the base URL.** Read `environment_access.md`; use
   `GDPEVO_ENV_BASE_URL` as `<TASK_ENV_BASE_URL>`. Confirm reachability with
   `GET /health` (returns `record_counts` per table).
3. **Identify the archetype** from the target and the template's key set. See
   `references/archetypes.md` for the five patterns, the endpoints/tables each
   uses, and the field→output derivations.
4. **Pull the working set.** Filter to the named target
   (`?batch_id=…`, `/programs/{code}/candidates`, or the roster's rows), then
   join the related records. Two efficient ways (`references/portal_api.md`):
   - **REST detail endpoints pre-join** the pieces you need
     (`GET /referrals/{id}` → referral+patient+icd+documents;
     `GET /chart/{patient_id}` → patient+clinical_history+chart_artifacts+…).
   - **`POST /query`** runs read-only `SELECT` SQL over the tables for exact
     reconciliation, counts, and multi-row joins. Prefer SQL when you need
     aggregate accuracy or to scan a whole batch at once.
5. **Classify each item** with the archetype's rules, using only the template's
   allowed values. Derive task parameters (requested service date, freshness
   limits, chair capacity, as-of date) from the data/prompt — never hardcode.
6. **Assemble the output** in template order and compute the summary/cohort
   counts **by tallying the item rows you just emitted** (internal consistency
   — see rules below).
7. **Validate before returning** against `references/output_checklist.md`.

## Cross-cutting rules (apply to every task)

- **Controlled vocabulary only.** Every enum/list value must be a literal from
  the template's `allowed_values`. Never invent codes, statuses, or tiers.
- **No extra or missing keys.** Emit exactly the required keys — nothing added,
  nothing dropped. Include an item for every required member (all listed
  patient/referral/transfer IDs, or every candidate the program returns).
- **Ordering is part of the spec.** Sort lists as the template says
  (usually ascending by `*_id`; sometimes alphabetical by code, or a stated
  priority order). Arrays labeled "unordered set" / "reason-code set" still must
  hold no duplicates — dedupe them.
- **IDs verbatim.** Use IDs exactly as the portal returns them (uppercase
  `REF0001`, `P001`, `TR0001`, insurance/`INS-` IDs). Do not re-case or renumber.
- **Constants exact.** Set `task_id`/`batch_id`/`roster_id`/`program_code` to the
  template's `required_value`/`constant`. Free date fields (`as_of_date`,
  `requested_service_date`) use the real value from the data or the task's
  as-of/current date, in `YYYY-MM-DD`.
- **Internal consistency.** Summary totals and every `counts_by_*` /
  `*_counts` / `decision_counts` object must be recomputed from the emitted item
  rows and must reconcile (e.g. the status counts sum to the item count; a
  referral in `ready_to_schedule` has `readiness_status: ready`; a blocker that
  drives a status also appears in the item's code list). Cross-check, don't
  guess.
- **Nulls deliberately.** Where the template allows `_or_null`
  (`priority_tier`, `first_checkin_days`, `observed/expected_chapter`), emit
  `null` — not `"none"`, `""`, or `0` — when the concept does not apply. Use the
  explicit `"none"`/`"not_applicable"` enum member only where the template lists
  it.
- **Read-only.** `POST /query` accepts only `SELECT`/read-only `PRAGMA`; there is
  no write path and none is needed. Treat all portal data as read-only evidence.
- **Determinism.** Apply one consistent policy across all items; break ties by
  the template's ordering key. The same inputs must always yield the same output.

## Supporting files

- `references/portal_api.md` — endpoint catalog, query params, response shapes,
  `POST /query` usage and constraints, error shapes.
- `references/data_model.md` — every table's columns and the observed value
  vocabularies (the reusable domain reference behind the decision rules).
- `references/archetypes.md` — the five task patterns: which tables/endpoints
  each uses and how raw fields map to the template's enums and codes.
- `references/output_checklist.md` — the pre-submit validation pass.
- `scripts/portal.py` — thin, decision-free client: resolves the base URL and
  wraps `GET` and `POST /query`. Optional convenience for pulling data.
