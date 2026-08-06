---
name: cedar-ridge-intake-audit
description: Audit a batch of Cedar Ridge Intake Coordination Portal records — new-patient access verification, referral readiness, dialysis transfer review, or a chronic-care enrollment panel — and produce one JSON object that conforms to the task's answer_template.json. Use whenever a task points at the Cedar Ridge Intake Coordination Portal (or a `<TASK_ENV_BASE_URL>` intake portal) and asks for a JSON intake/referral/transfer/enrollment audit file. Reads the portal over the network, classifies each in-scope record, and emits JSON only.
---

# Cedar Ridge Intake Audit

Use this skill for any task that asks you to audit a batch/roster/program of records
in the **Cedar Ridge Intake Coordination Portal** and return a single JSON object
describing readiness, eligibility, risk, blockers, action plans, and cohort counts.

The portal serves several domains that share one procedure:

- **New-patient access verification** (a roster of patients → insurance /
  prescription / pharmacy / risk / registration status).
- **Referral readiness audit** (a referral batch → coding discrepancies,
  duplicates, shared-insurance anomalies, blockers, action plan, priority tiers).
- **Dialysis transfer review** (a transfer batch → packet completeness/freshness,
  capacity feasibility, intake decision, contact routing).
- **Referral-to-chart activation** (a referral batch → readiness, code
  discrepancies, chart-activation needs, correspondence queue, priority order).
- **Chronic-care enrollment panel** (a program's candidates → eligibility,
  enrollment disposition, reason codes, follow-up cadence, monitoring package).

The *vocabulary* and *output shape* differ per task and per domain. The exact
allowed enum values, required keys, and ordering rules for the current task are
defined **only** in that task's `input/payloads/answer_template.json`. Read it
first and treat it as the binding contract — never rely on vocabulary remembered
from other tasks.

## What you must produce

A single JSON object that conforms exactly to the task's
`answer_template.json`. **JSON only** — no prose, no markdown fences, no
commentary. See `references/output_assembly.md` for the full contract rules and
self-check.

## Principles

1. **The template is the contract.** Emit only its required keys, only its
   allowed enum values, and follow its ordering rules. Inventing a value or
   omitting a required key is a failure.
2. **Filter to scope.** Portal list endpoints return *all* records across every
   batch/roster/program, including distractors from unrelated batches. Always
   restrict to the `batch_id` / `roster_id` / `program_code` named in the prompt.
3. **Pull every related record.** A referral needs its patient, chart, ICD
   metadata, documents, coverage, and authorization. A transfer needs its patient,
   packet documents, and facility capacity. A candidate needs its chart and
   clinical history. A missing related record is the top cause of wrong codes.
4. **Dates and service lines come from the environment, not the prompt.** A
   roster's `requested_service_date` / `service_line`, a panel's `as_of_date`,
   etc., live in portal tables (`intake_rosters`, etc.) — fetch them.
5. **JSON only.** The whole response must parse as one JSON object.

## Procedure

### Phase 0 — Parse the task

From the prompt, identify:

- The **scope key and value**: a `roster_id` (new-patient access), a `batch_id`
  (referral / transfer batches), or a `program_code` (enrollment panel).
- The **in-scope entity set**: an explicit id list (e.g., a set of patient ids),
  "all referrals in batch `<batch_id>`", or "all current candidates for
  `<program_code>`".
- The **domain**, which selects the classification logic in
  `references/audit_logic.md`.
- The **deliverable dimensions** the office asks for (these map to the template's
  sections).

### Phase 1 — Read the contract

Read `input/payloads/answer_template.json`. Extract: required top-level keys;
constant/required-value fields; per-list ordering rules; per-item required keys;
enum allowed values; summary count keys and value types. Also read
`environment_access.md` for the base URL and the allowed endpoint list. If a
`payloads/target_roster.json` (or similar payload) is present, use it for the
patient-id list and notes, but still confirm scope metadata against the portal.

### Phase 2 — Connect and gather (filtered)

Use only endpoints from `environment_access.md`. See
`references/portal_endpoints.md` for response schemas and the SQL endpoint.

- **Referral / transfer batch:** `GET /referrals` (or `/transfers`), then keep
  only rows whose `batch_id` equals the scope key. Re-check the filtered count.
- **New-patient roster:** fetch the `intake_rosters` row for the `roster_id`
  (via `POST /query`) for `requested_service_date` / `service_line`; use the
  patient-id list from the prompt/payload.
- **Enrollment panel:** `GET /programs/{program_code}/candidates` for the
  candidate list.
- **Per entity,** pull all related records (patient identity, chart, documents,
  ICD metadata, coverage, PBM, pharmacy, lifestyle, facility capacity as the
  domain requires). Use `POST /query` (`{"sql": "..."}`) for joins, duplicate
  detection, shared-insurance grouping, and capacity-on-date lookups.

### Phase 3 — Classify and derive

Apply the shared evidence-checking patterns from `references/audit_logic.md`:

- Completeness (missing records / imaging / documents / chart artifacts).
- Freshness (document age vs. `freshness_limit_days`).
- Clinical coding consistency (ICD chapter/service_family/narrative/laterality
  vs. referral service line and reason).
- Duplicate detection (same patient, multiple referrals in one batch).
- Shared-insurance anomalies (same `insurance_id` across *different* patients).
- Authorization blockers (`pending` / `denied` / `not_submitted` when required).
- Capacity & feasibility (open chairs on the requested start date × packet
  readiness).
- Risk (lifestyle + clinical flags → overall risk).
- Eligibility & enrollment (target condition + active diagnosis + consent + chart
  → enroll / hold / reject; acuity → cadence + monitoring package).
- Readiness taxonomy and priority tiering (urgency × readiness → tier).
- Contact routing / correspondence queue / action plans.

Map the evidence to the **exact enum members the current template lists**.

### Phase 4 — Assemble the JSON

Build one JSON object per `references/output_assembly.md`:

- All required top-level keys; constants (`task_id`, `batch_id`, `program_code`,
  …) at their required values.
- Lists ordered per the template (ascending by id unless it says otherwise;
  unordered sets emitted stably sorted).
- Only allowed enum values; ids uppercase exactly as the portal returns them.
- Summary counts as integers, keyed by the template's members, reconciling to the
  per-entity lists (include zero-valued keys).
- Empty sets as `[]`; `null` only where the template permits.

### Phase 5 — Self-check

Run the checklist in `references/output_assembly.md`: required keys present, no
extras, all enums allowed, ordering correct, ids cased correctly, counts sum to
totals, reference dates from the environment, JSON only. Then emit the JSON
object as the entire response.

## Files

- `references/portal_endpoints.md` — endpoint contract, response schemas, the SQL
  endpoint, gathering rules.
- `references/audit_logic.md` — the shared classification patterns per domain.
- `references/output_assembly.md` — the JSON contract rules and self-check.
