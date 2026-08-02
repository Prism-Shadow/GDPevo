---
name: ehr-governance-packet
description: >-
  Build normalized-JSON deliverables for EHR quality-governance tasks against a
  read-only EHR/referral API — duplicate-chart merge readiness packets, referral
  coordination packets, care-transition/handoff packets, duplicate-review +
  ServiceRequest quality checks, and referral-batch audits. Use whenever a task gives a
  prompt plus an `answer_template.json` (and an `environment_access.md` base URL) and
  asks for normalized JSON covering merge dispositions, active clinical-list unions,
  identity match/conflict signals, ICD-10 / service-code validation, provider contacts,
  document/audit evidence, risk flags, follow-up queues, or tiered action plans.
---

# EHR quality-governance packet & audit builder

## What these tasks look like
Each task ships an `input/prompt.txt`, one `input/payloads/answer_template.json` (the
output contract), sometimes an extra request payload (e.g. `*_request.json`), and an
`environment_access.md` giving a read-only EHR API base URL. You inspect the live API
and return **one normalized JSON object** that conforms exactly to the answer template —
no prose. Task families seen: (1) duplicate-chart **merge readiness packet**,
(2) specialty **referral coordination packet**, (3) **care-transition / handoff packet**,
(4) **duplicate-review + ServiceRequest** quality signals, (5) **referral-batch audit**.

## Operating procedure

1. **Read the contract first.** Read `prompt.txt`, the `answer_template.json`, and any
   extra payload. The template's top-level keys, field types, **enum lists**, ordering
   notes, and required constants (e.g. `task_id: train_00X`) are the final spec — build
   to them exactly. List the concrete entity ids named in the prompt (patient ids,
   candidate id, referral/batch id, ServiceRequest id, recipient provider id).

2. **Set up access.** Get the base URL from `environment_access.md`
   (`GDPEVO_ENV_BASE_URL`, substituted for `<TASK_ENV_BASE_URL>`). Everything is
   **GET, read-only, no auth**. Only call endpoints listed there. See
   `references/environment_api.md` for the endpoint catalog and response shapes. Global
   list endpoints (`/api/referrals`, `/api/audit-logs`, `/api/patients`) return
   everything — filter to your case client-side.

3. **Gather evidence for each entity the template needs**, e.g.:
   - patient detail + `conditions`/`medications`/`allergies` (+ `encounters`,
     `immunizations`, `documents`, `disclosures`, `service-requests` as required);
   - the duplicate candidate (`/api/duplicates/{id}`) and/or referral/batch;
   - `/api/icd10/{code}` for every diagnosis/reason code; `/api/service-codes/{code}`;
   - the provider directory for the recipient/specialist and PCP.

4. **Apply the reusable decision rules** in `references/decision_rules.md`. The core
   invariants:
   - **Active records only**, keyed and de-duplicated by `normalized_key`.
   - **Live patient endpoints override** any `merge_preview` — reconcile and record what
     the endpoints add.
   - **Canonical target/source** come from `canonical_status`/`canonical_patient_id`
     pointers (corroborated by `merge_preview`); hard conflicts (opposite laterality,
     different name/phone/dob/insurance) block a merge.
   - **Validate every code** against the ICD-10 directory (`chapter`, `expected_terms`,
     `requires_laterality`; 404 ⇒ unknown) for chapter-range, narrative, and laterality
     checks; validate service codes for existence/active/service-line match.
   - **Evidence filtering**: identity/external-continuity `final` documents only; audit
     logs scoped to the case's patients and this merge; drop chart summaries and
     other-patient/other-batch records as distractors.
   - **Provider contacts** by service line; **risk flags**, **handoff-encounter
     selection**, **batch audit** (duplicates, queues, tiering, counts), and
     **readiness/blocking** all as specified in the rules file.

5. **Assemble strictly to the template.** Emit exactly the required top-level keys and
   field types. Use only allowed enum values. Sort every set array ascending (or by the
   template's stated order). Dates `YYYY-MM-DD`. Fill required constants.

6. **Self-check before returning:**
   - JSON only; every top-level key present; all enums within `allowed_values`.
   - Every emitted id (document/audit/encounter/referral/provider) traces to a case
     entity — no distractors leaked; excluded items sit in the right exclusion bucket.
   - Set arrays sorted & de-duped; ordered arrays in the stated order; fixed-length
     arrays have the right count.
   - Summary counts (audit tasks) are internally consistent with the arrays.
   - Booleans/status/disposition enums agree with each other (e.g. `ready_to_send`
     matches the readiness enum and the presence/absence of blockers).

## References
- `references/environment_api.md` — endpoints, response field shapes, identity/canonical
  fields, provider/service-code/ICD-10 directories.
- `references/decision_rules.md` — the full reusable decision logic (R0–R9) plus the
  recurring-distractor checklist. Read it before assembling any packet.

## Guardrails
- Read-only: never attempt writes/POSTs; use only allowlisted GET endpoints.
- Distill from the live evidence — do **not** hardcode values from prior tasks. Provider
  contacts, code chapters, and enums must come from the current environment/template.
- When a derived rule and the answer template conflict, the **template wins**.
