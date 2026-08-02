---
name: ehr-governance-packet
description: >-
  Produce the normalized JSON deliverable for an EHR quality-governance task —
  duplicate-merge readiness packets, specialty referral coordination packets,
  care-transition handoff packets, duplicate-review + ServiceRequest QA, and
  referral-batch audits. Use when a prompt gives clinical/governance object IDs
  (patients, duplicate candidates, referrals, ServiceRequests, batches) plus an
  `input/payloads/answer_template.json`, and asks for normalized JSON that
  reconciles a read-only EHR/referral environment against that template. Read
  this before gathering data or writing the answer.
---

# EHR quality-governance packet / audit tasks

These tasks share one shape: a prompt names some governance objects (patient IDs,
a duplicate candidate, a referral, a ServiceRequest, a batch) and points to an
`input/payloads/answer_template.json`. A read-only EHR/referral environment is
described in the task's own access file. Your job is to gather evidence from that
environment and emit **JSON that conforms exactly to the answer template** —
right keys, right enum tokens, right ordering, no prose.

The winning approach is evidence-driven and template-driven, not narrative. The
template is the spec; the environment is the source of truth; your output is a
faithful reconciliation of the two.

## Workflow

1. **Read the template first, in full.** `answer_template.json` defines every
   required key, the allowed enum values, which arrays are "sets", and the
   ordering rules. Build your output object to mirror its structure key-for-key.
   Note every `enum:` list — your value MUST be one of those tokens verbatim.
   Note every ordering note ("sorted alphabetically", "sort by code",
   "newest to oldest", "set semantics") and obey it.

2. **List the entities you must resolve.** Every ID in the prompt, plus every ID
   the template asks you to output (providers, documents, encounters, codes…).

3. **Discover the environment from the task's own access description** (the file
   the task provides listing the available read-only resource families — patient
   detail, active clinical lists, encounters, immunizations, disclosures,
   documents, service-requests, audit logs, duplicate candidates, referrals,
   ICD-10 directory, provider directory, service-code directory, etc.). Query
   only what you need for the entities above. Do not hardcode or assume specific
   URLs — read them from the provided access description each run.

4. **Gather evidence** for every template field. Prefer the primary record
   endpoints (a patient's own active lists) over any pre-computed "preview" or
   summary the environment offers — the primary records are authoritative.

5. **Apply the decision rules** in `references/decision-rules.md` to turn raw
   records into the template's normalized fields.

6. **Normalize and self-check** (below), then output JSON only.

## Core principles (transfer across all of these tasks)

- **Active-list unions preserve everything active.** When a field asks for a
  union of active condition / medication / allergy keys, take the `normalized_key`
  of every record whose `status == "active"` across all in-scope patients, and
  include *all* of them — even generic-looking filler keys. Dropping an active
  key (a med, an allergy) is a clinical-safety error and loses points. Records
  with any non-active status (`inactive`, `entered-in-error`) are the
  "excluded distractors", never part of the union.

- **Primary records beat previews.** A duplicate candidate's `merge_preview` (or
  any summary) can be incomplete or null. Reconcile against the patients' own
  active-list endpoints; where a "reconciliation / added-from-active-endpoints"
  field exists, it captures exactly what the preview missed.

- **Separate the classification from the action.** Identity/duplicate status
  (confirmed / needs-review / not-duplicate) is a *different* decision from the
  action (merge / hold-for-review / do-not-merge). Strong identity matches
  (same DOB + insurance + address) can mean a *confirmed* duplicate that is still
  *held for review* because conflict signals exist. A benign conflict signal
  → review-with-conflict, not do-not-merge. Only record a concrete merge
  target/source when a merge is actually proceeding; if the environment's
  preferred target/source is null and the action is a hold, leave them null.
  Merge target = the active/canonical record; source = the record flagged
  duplicate/possible_duplicate.

- **Readiness follows real data completeness, not reminders.** A soft
  coordination note ("confirm the allergy before sending") does not make a fully
  populated active record incomplete. Base readiness/blocking status on whether
  the required structured data and documents actually exist.

- **Relevance beats recency for evidence selection.** Pick the encounter /
  document / audit row that is *topically tied to the packet's purpose* and has a
  final/signed status — not merely the newest row. Exclude generic exports
  (chart summaries / EHR exports), stale/out-of-window records, and rows about
  other patients or other candidates. Where the template wants both selected and
  excluded IDs, list every reviewed-but-rejected ID in the exclusion field.

- **Referral code sets are narrow.** The codes that "belong in the letter" are
  the referral's primary diagnosis plus the narrative's symptom code — not every
  cardiovascular/comorbid condition on the chart. Mark only those
  `referral_relevant`. Validate each code against the ICD directory: compare its
  chapter to the service line and its `expected_terms` to the narrative.

- **Emit every evidenced flag; don't prune.** For risk-flag / signal fields,
  output every value that has chart evidence (a condition, a med+condition pair,
  an allergy, a care-plan note), including chronic conditions. Provide the
  per-flag evidence the template asks for.

- **Providers come from the directory verbatim.** Resolve the relevant
  provider_id (receiving / performer / recipient, or the provider tied to an
  external continuity document) in the provider directory and copy
  name/role/facility/phone/fax exactly.

See `references/decision-rules.md` for the field-by-field playbook, including the
batch-audit rules (single canonical expected chapter, in-chapter
laterality/narrative mismatches, same-patient duplicates, shared-insurance
anomalies, data-driven follow-up queues, and issue-based tiering).

## Normalization conventions

- **Enums:** copy the exact token from the template's `enum:` list. Never invent
  a variant or add a suffix. For controlled labels/reason-codes that mirror
  environment signals, reuse the environment's own token strings.
- **Ordering:** obey each field's ordering note. Default for "set" arrays is
  ascending/alphabetical; sort even set-semantics arrays for determinism.
  Object arrays: sort by the key the template names (e.g. `referral_id`, `code`).
- **Verbatim values:** copy IDs, names, phone/fax, dates, `normalized_key`, and
  code strings exactly as returned. Dates are `YYYY-MM-DD`.
- **Nulls:** use `null` (not "", not omitted) where the template types a field as
  nullable and the evidence is genuinely absent/undetermined.
- **Output:** a single JSON object with the template's keys only. No commentary,
  no markdown, no fields the template did not define.

## Self-check before finishing

- Every required top-level key present; no extra keys.
- Every enum value is one of the template's allowed tokens.
- Every array obeys its ordering rule; set arrays sorted.
- Every emitted ID / value is traceable to a fetched record.
- Active unions include all active keys; distractors (inactive / unrelated /
  stale / generic-export) are excluded (and listed where the template asks).
- Counts (if any) equal the lengths of the sets you actually produced.
- The output parses as JSON and matches the template's shape exactly.
