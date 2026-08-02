---
name: ehr-governance-packet
description: >-
  Build a normalized JSON packet for a read-only EHR quality-governance case
  (duplicate-chart merge readiness, specialty referral coordination, care-transition
  handoff, ServiceRequest quality review, or a referral-batch coding audit). Use
  whenever a task gives you a `prompt.txt` describing an EHR/referral case plus a
  `payloads/answer_template.json` output schema and an `environment_access.md`
  pointing at a read-only EHR quality API, and asks for a single normalized JSON
  answer that conforms to that template. Triggers: "merge readiness packet",
  "duplicate candidate", "referral coordination packet", "care transition packet",
  "ServiceRequest quality", "referral audit", "conforms to answer_template.json".
---

# EHR quality-governance packet builder

## What this skill is for

A family of tasks that all share the same shape:

1. A **case** is described in `prompt.txt` (patient IDs, a duplicate `candidate_id`,
   a `referral_id`, a `ServiceRequest` id, a referral `batch_id`, a recipient
   `provider_id`, etc.).
2. An exact **output schema** is given in `input/payloads/answer_template.json`
   (top-level keys, field types, enum vocabularies, ordering/sorting rules,
   `set_semantics`). Some tasks add extra request payloads (e.g. a
   `merge_packet_request.json`) that only restate the requested outputs.
3. A read-only **EHR quality-governance API** is reachable per `environment_access.md`.

Your job: pull the evidence from the API, normalize it, apply the domain decision
rules, and return **one JSON object that conforms to the template — JSON only, no
prose, no extra keys**.

The specific case objects, values, and outcomes differ every time. **Derive every
value from the live API for the case in front of you.** Never reuse an ID,
disposition, count, or code list from a prior run or example — the environment is
the single source of truth and may have been reseeded since any example was written.

## Fixed procedure

Work in this order for any case:

1. **Read the three inputs.**
   - `prompt.txt` → identify the task type and every case object ID it names.
   - `input/payloads/answer_template.json` → the contract. Note every top-level key,
     each field's type/enum, every ordering rule, and any `required_value`
     (e.g. a `task_id` that must equal the task directory name such as `train_004`).
   - `environment_access.md` → the base URL (`GDPEVO_ENV_BASE_URL`, substitute it
     wherever the prompt writes `<TASK_ENV_BASE_URL>`) and the allowed endpoints.
     No credentials; all calls are `GET`.

2. **Classify the task type** and open the matching playbook in
   `references/task_playbooks.md`:
   - duplicate-chart **merge readiness** packet,
   - specialty **referral coordination** packet,
   - **care-transition** handoff packet,
   - **ServiceRequest quality** review,
   - **referral-batch coding audit**.
   (A case may combine two, e.g. a duplicate review plus a ServiceRequest review.)

3. **Pull evidence** from the allowed endpoints for the case objects. See
   `references/api_reference.md` for each endpoint's response shape and the
   important quirks (list wrapper keys, which query filters are ignored, 404 =
   not-found). Fetch the full active clinical lists, referral/candidate/ServiceRequest
   detail, provider directory entries, and ICD-10 / service-code lookups you need.

4. **Normalize** using the shared rules in `references/normalization_rules.md`:
   active-only `normalized_key` unions, distractor exclusion, ICD-10 validation and
   laterality/narrative checks, provider-contact resolution, date formatting, and
   the sorting / set-semantics each template field demands.

5. **Apply the decision rules** for the task type (dispositions, readiness,
   risk flags, tiering, follow-up queues) from `references/task_playbooks.md`.
   Every enum you emit must be one of the template's allowed values and must be
   justified by evidence you actually fetched.

6. **Assemble and self-check** against the template before returning — see the
   checklist below. Output the JSON object and nothing else.

## Output discipline (check every time)

- Emit a single JSON object with **exactly** the template's top-level keys — no
  more, no fewer. Match nested field names and types precisely.
- Every enum value is drawn from the template's `allowed_values` for that field.
- Apply each field's ordering rule. Where the template marks a list as a set /
  `set_semantics`, still sort deterministically (alphabetical, or by the stated
  key) so output is stable.
- Dates are `YYYY-MM-DD`. Use `null` only where the template allows it.
- If a `required_value` is specified (e.g. `task_id`), emit it verbatim.
- No narrative, SOP text, comments, or markdown around the JSON.
- Counts/summaries must be internally consistent with the arrays you emit
  (e.g. a `*_count` equals the length of its list).

## Supporting files

- `references/api_reference.md` — endpoints, response shapes, and quirks.
- `references/normalization_rules.md` — shared normalization + evidence-selection rules.
- `references/task_playbooks.md` — per-task-type field-by-field decision logic.
- `scripts/ehr_get.py` — generic, value-free API helper (resolves the base URL from
  `environment_access.md` and GETs an endpoint as pretty JSON). Optional convenience.
