---
name: cedar-ridge-intake-coordination
description: Solving Cedar Ridge Intake Coordination Portal audit/intake tasks — reconcile patient, referral, transfer, chart, and program data into a strictly-templated JSON answer. Use whenever a task points at the Cedar Ridge portal (batches like NPI-JUN-01, ORTHO-JUN-01, DIAL-WINTER-01, DMHTN-2026A, PULM-JUN-02) and asks for a JSON activation/audit/enrollment file.
---

# Cedar Ridge Intake Coordination — Task Solving Skill

## What these tasks are

Each task targets one **batch** (a roster, referral batch, transfer batch, or program) in the Cedar
Ridge Intake Coordination Portal and asks you to produce **one JSON object** that follows a provided
`answer_template.json`. The portal is a shared, read-only store of intake, referral, transfer, chart,
and program data. The portal base URL is given in the task prompt as `<TASK_ENV_BASE_URL>`; the
per-task `environment_access.md` documents the available endpoints (treat that doc as the source of
truth for endpoint mechanics — do not hardcode URLs).

The work is **deterministic reconciliation + rule application**, not free-form narration. Every output
field is a controlled enum, a code from a fixed set, an ID, a count, or a date. There is no prose.

## Universal method (apply to every task)

1. **Read the prompt and `answer_template.json` together.** The template is the contract: it lists
   required top-level keys, per-item required keys, allowed enum values, list orderings, and count-key
   shapes. Print the template's allowed-values lists and keep them next to you while deriving. Most
   errors come from inventing a value not in the allowed set, omitting a required key, or wrong
   list ordering.
2. **Identify the batch identifier** and the entity set the batch spans (patient IDs, referral IDs,
   transfer IDs, or program candidate IDs). Pull the full list for that batch first, then fetch each
   entity's detail.
3. **Gather all related records per entity.** A single entity (e.g. a patient) typically fans out to
   coverage, PBM, pharmacies, lifestyle, clinical_history, chart_artifacts, and its own
   referrals/transfers/rosters. Fetch the detail record for every member; do not rely on list-level
   summaries. Cross-check with the read-only SQL endpoint (it accepts a SQL string) when you need to
   reconcile across tables (duplicates, shared insurance, capacity by date).
4. **Derive each output field by a stated rule** (see `references/derivation_rules.md`). Write the
   rule down before assigning values so the logic is consistent across all items — ad-hoc per-item
   judgments drift and produce inconsistent cohort counts.
5. **Assemble counts/summaries from the per-item results**, not by re-deriving. Every summary count is
   a rollup of the per-item fields; if a per-item field flips, recompute the affected counts.
6. **Validate against the template before submitting:** every required key present, every value in the
   allowed set, every list in the specified order (ascending ID unless noted), count objects have all
   required keys (including zero counts), integers are integers. Output JSON only — no surrounding prose.

## Data model (what to pull and from where)

See `references/data_model.md` for the full entity/field map. Key relationships:

- **patients** are the hub. A patient detail bundles: `patient` demographics, `coverage` (insurance),
  `pbm` (prescription benefit), `pharmacies` (preferred + network), `lifestyle`, `clinical_history`,
  `chart_artifacts`, and the patient's own `referrals`, `transfers`, `rosters`, `program_candidates`.
- **referrals** carry `icd10_code`, `diagnosis_description`, `referral_reason`, `records_received`,
  `imaging_received`, `auth_required`/`auth_status`, `appointment_scheduled`, `insurance_id`,
  `urgency`, `service_line`, `batch_id`.
- **icd_codes** map a code to `chapter`, `service_family`, `laterality`, `description`. Use
  `service_family` to detect clinical-code discrepancies (code's service family vs. referral's
  service line) and `laterality`/`description` for narrative/laterality checks.
- **transfer_requests** carry `requested_start_date`, `modality`, `days_requested`, `chair_window`,
  `transportation`. **facility_capacity** is keyed by `(location_id, date, modality)` with
  `open_chairs`; the requested start date may have **no capacity row** (treat as 0 / unavailable).
- **documents** are keyed by `transfer_id` (and sometimes `referral_id`); each has `doc_type`,
  `status` (final/draft), `finalized` (0/1), `received_date`. Packet completeness and freshness are
  derived from these.
- **program_candidates** carry `consent_status`, `preferred_outreach`, `adherence_score`,
  `target_condition`. Pair with the patient's `clinical_history` (chronic conditions) and
  `chart_artifacts` to determine eligibility.

## Core derivation rules (transferable across batches)

These are the rules that consistently drive correct field values. Full detail and edge cases in
`references/derivation_rules.md`.

**Status fields are conjunctive — a status is "valid" only when every sub-condition holds.**
- Insurance is valid only if coverage is active, in-date on the requested service date, **and** the
  requested service line appears in `coverage.service_lines`. A code on a referral whose ICD
  `service_family` differs from the referral `service_line` is a clinical-code discrepancy.
- Prescription (PBM) is valid only if `active=1`, `status=approved`, `formulary_status=covered`, and
  the PBM `policy_number` matches the coverage `policy_number`. Otherwise the specific failure maps to
  `pbm_invalid` / `pbm_policy_mismatch` / `pbm_missing`.
- Pharmacy status follows the **preference_rank=1** pharmacy's `network_status`.

**Missing vs. stale documents are different.**
- A required document is **missing** if its `doc_type` is absent from the packet **or** it is present
  but not finalized (`status != final` / `finalized != 1`). Drafts count as missing for completeness.
- A document is **stale** only among the freshness-limited types, comparing `received_date` to the
  relevant service/start date against the type's freshness limit. Only finalized documents are
  staleness-checked (a draft is already "missing").
- Some "required" documents are satisfied by a non-document field (e.g. `transportation` is the
  transfer's `transportation` arrangement, not a doc_type). A null arrangement = missing.

**Eligibility ≠ enrollment action.**
- For program panels, `eligible` reflects **clinical criteria** (correct target condition + the
  required diagnoses present). Consent, chart, and artifact problems are **enrollment barriers** that
  drive `enrollment_status` (enroll / hold / reject), not the eligible boolean. A patient can be
  clinically eligible yet rejected (e.g. consent declined) or held (consent missing).

**Capacity is summed across locations for the exact requested date.**
- `open_chairs_total` = sum of `open_chairs` across all locations for that date+modality. If no
  capacity row exists for the requested start date, it is 0 / unavailable.

**Cohort summaries roll up per-item decisions.** Re-derive every count object from the final per-item
list; include all required count keys even when zero.

## Output discipline (non-negotiable)

- Return a **single JSON object** — no prose, no markdown fences, no commentary outside the JSON.
- Use **only** values from the template's allowed sets; never invent codes or enum values.
- Preserve **exact key names** and include **every** required key (templates mark required keys/lists).
- Order lists as the template specifies: usually ascending by ID; some arrays are explicitly
  "unordered sets" (still emit them sorted for determinism). Count objects must contain **all**
  required count keys, including those whose value is 0.
- IDs are uppercase exactly as the portal returns them (`P001`, `REF0010`, `TR0001`, etc.).
- Dates are `YYYY-MM-DD`. Integers are integers, never strings.

## Task archetypes

The batch identifier signals the archetype; each has its own field set in
`references/derivation_rules.md`:

- **New-patient access verification** (roster, e.g. `NPI-JUN-01`): per patient, insurance /
  prescription / pharmacy status, lifestyle & overall risk, registration status, blocked reason
  codes, plus a cohort summary.
- **Referral readiness audit** (e.g. `ORTHO-JUN-01`): per-referral readiness, issue codes, ICD
  discrepancies, duplicate groups, shared-insurance anomalies, blocker sets, ready-to-schedule list,
  action plan, and multi-axis summary counts.
- **Transfer packet review** (e.g. `DIAL-WINTER-01`): per-transfer packet completeness, missing/stale
  docs, requested-start capacity feasibility, intake decision, next-contact owner/route, cohort
  summary.
- **Program enrollment panel** (e.g. `DMHTN-2026A`): per-candidate eligibility, enrollment
  disposition, reason codes, follow-up cadence, missing chart artifacts, outreach channel, initial
  monitoring package, summary counts.
- **Referral-to-chart activation** (e.g. `PULM-JUN-02`): readiness by referral, clinical-code
  discrepancy referrals, blocker sets, duplicate handling, ready-referral chart needs, correspondence
  queue, priority order.

For each, build the per-item records first, then the cross-item structures (duplicates,
shared-insurance, blocker sets, summaries), then validate the whole object against the template.
