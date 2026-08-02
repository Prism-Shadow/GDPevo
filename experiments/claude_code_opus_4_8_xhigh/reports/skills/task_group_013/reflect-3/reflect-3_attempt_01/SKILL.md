---
name: intake-coordination-portal-audit
description: >-
  Produce the required normalized JSON audit for a Cedar Ridge Intake
  Coordination Portal task — patient access verification, referral readiness /
  referral-to-chart activation, dialysis transfer review, or program enrollment
  panel. Use when a task points at an intake-coordination portal base URL plus an
  answer_template.json and asks for a batch/roster/program-level JSON report of
  statuses, blockers, reason codes, and cohort counts. Covers how to discover the
  data, apply the classification rules, and emit template-conformant JSON.
---

# Intake Coordination Portal Audit

## What this covers

A family of read-only clinical-operations audits served by an "Intake
Coordination Portal." Each task hands you:

- a **prompt** naming one target id — a roster, referral batch, transfer batch,
  or program code — and a portal **base URL** (given as a placeholder such as
  `<TASK_ENV_BASE_URL>`; read it from the task, never hardcode one);
- an **`input/payloads/answer_template.json`** describing the exact JSON you must
  return (required keys, per-item keys, allowed enum values, orderings, and
  summary/count structure);
- an **environment access note** listing the portal's available read endpoints.

Your job is always the same shape: pull the target records plus their reference
data, classify each item into the template's controlled vocabulary, roll up
cohort counts, and return **one JSON object, JSON only, no prose**.

The five recurring task types and their per-type rules are in
[`reference/decision-rules.md`](reference/decision-rules.md). The portal's tables
and fields are in [`reference/data-model.md`](reference/data-model.md). Read the
matching playbook before writing code.

## Method (applies to every task)

1. **Read the answer template first.** It is the contract. Extract: the required
   top-level keys and their constant values (e.g. `task_id`, and the roster/
   batch/program id); the per-item required keys; every `allowed_values` enum;
   the `ordering` rule for each list; and the exact count keys the summary
   expects. Note which arrays are "unordered sets" (reason/issue/blocker codes)
   vs. id lists that must be sorted ascending.

2. **Discover the data.** Read the environment access note for the base URL and
   the endpoint list. The portal exposes per-resource read endpoints (patients,
   coverage/insurance, referrals, transfers, documents, charts, program
   candidates, ICD codes, pharmacies, facility capacity) and, when listed, a
   **read-only SQL query endpoint** — the fastest path. If SQL is available,
   inspect the schema first (`SELECT name,sql FROM sqlite_master`), then pull the
   batch rows and JOIN in the reference tables. Otherwise fetch the per-resource
   endpoints. Pull **all** patients/records named by the roster/batch/program,
   not a sample.

3. **Fix the reference date.** Date-sensitive logic (coverage in-force, document
   freshness, capacity) is evaluated against the record's own requested date
   (`requested_service_date` / `requested_start_date` / candidate or program
   date), **not** wall-clock "today." Take it from the target record.

4. **Classify each item.** Map raw fields to the template enums using the
   per-type playbook. Build each code array as the **union of independent
   checks** (each condition contributes one code). Keep codes inside the
   template's `allowed_values` only.

5. **Assign the item's overall status by severity precedence.** The general
   ladder is: *hard-ineligible / blocked* (missing eligibility, missing records,
   denied auth, wrong target) **>** *needs clinical or coding review* **>**
   *administrative follow-up* (duplicates, shared insurance, scheduling) **>**
   *ready / approved*. Each playbook gives the concrete ordering.

6. **Build the derived collections** the template asks for — duplicate groups,
   blocker sets, ready lists, chart-activation needs, correspondence queue,
   priority order — using the item classifications.

7. **Compute the cohort summary.** Initialize **every** enum key to `0` before
   counting so no key is missing. Counts are integers and must reconcile with the
   per-item rows (totals equal the number of items).

8. **Emit and self-check.** Output only the JSON object. Verify: all required
   keys present; constants match; every value is in its allowed enum; id lists
   sorted ascending; set-valued code arrays de-duplicated; counts sum correctly;
   no extra prose or trailing text.

## Output conventions (all task types)

- **One JSON object**, nothing else — no markdown, no commentary.
- **Ordering:** item lists ascending by their id unless the template says
  otherwise; code/reason/issue arrays are unordered sets (sort them for
  determinism, but order is not scored). A few lists have explicit orderings
  (e.g. alphabetical by code, or highest-priority-first) — follow the template.
- **Controlled values only.** Never invent a status/reason string; if a
  condition has no matching enum value, it is not reported.
- **Ids** are echoed exactly as the portal returns them (case included).
- **Counts** are integers; include a key for every allowed enum value, even when
  the count is `0`.

## Cross-cutting field rules worth memorizing

These recur across task types (details and per-type nuances in the playbook):

- **Insurance/coverage:** valid ⇔ status `active` and the service date is within
  `effective_date`..`termination_date`; `expired`/out-of-window ⇒ invalid;
  `pending` ⇒ not-yet-valid; no row ⇒ missing. A covered service line must appear
  in `coverage.service_lines`, else it is an excluded-service-line issue
  (separate from the coverage validity itself).
- **Pharmacy benefit (PBM):** valid ⇔ `active` + `status=approved` +
  `formulary_status=covered`; `rejected`/inactive/`not_found`/`pending`/`review`
  ⇒ invalid; policy number not matching the coverage policy ⇒ a policy-mismatch
  issue.
- **ICD coding:** `icd_codes.service_family` vs. the referral's `service_line`
  drives clinical-code / chapter mismatch; `icd_codes.laterality` and `chapter`
  support laterality/chapter checks. A code whose `service_family` already equals
  the referral's service line is **not** a mismatch even if its chapter letter
  differs.
- **Records/imaging/auth (referrals):** driven by the boolean
  `records_received` / `imaging_received` flags and by
  `auth_required` + `auth_status` (`pending`/`denied`/`not_submitted` = blocker).
  `appointment_scheduled` before clearance is its own flag.
- **Documents / packets:** a required item counts as present only when a matching
  document is **finalized** (`finalized=1`/status `final`); `draft` or absent ⇒
  missing. Some required "documents" are satisfied by a field on the parent
  record (e.g. transportation on the transfer request).
- **Chart artifacts:** `chart_artifacts.status` of `current` = usable;
  `stale`/`draft`/absent ⇒ needs refresh or is missing. `existing_chart` on the
  patient/candidate is the flag for whether a chart record exists.
- **Duplicates:** true duplicates are the **same patient** repeated within a
  batch/service line; keep the lowest id as primary. A shared `insurance_id`
  across **different** patients is an insurance anomaly, not a duplicate.
- **Contact/outreach:** a preferred channel is usable only if its contact point
  exists (email preferred ⇒ needs an email on file; phone/sms ⇒ needs a phone);
  otherwise flag it / fall back.
- **Capacity:** sum open chairs/slots across locations for the modality on the
  requested date; a date with no capacity row means the site is closed that day
  (zero availability), not missing data.

## Pitfalls

- Don't skip reading the template — key names, enum spellings, and count keys
  vary between task types.
- Don't treat `draft` documents or `stale` chart artifacts as present.
- Don't classify a same-service-family ICD code as a chapter mismatch.
- Don't evaluate freshness/coverage against today; use the record's requested
  date.
- Don't emit reason/blocker codes outside the template's `allowed_values`, and
  don't omit zero-valued summary count keys.
- Reconcile: every per-item status must be reflected in the summary counts.
