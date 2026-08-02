---
name: ehr-governance-packets
description: >-
  Produce normalized JSON for EHR quality-governance / care-coordination packet
  tasks against a read-only EHR "quality API": duplicate-chart merge-readiness
  packets, specialty referral coordination letters, care-transition/handoff
  packets, duplicate-review + service-request validation, and referral-batch
  audits. Use whenever a prompt hands you case objects (patient IDs, a duplicate
  candidate ID, a referral or referral-batch ID, a service-request ID, a
  recipient provider) plus an answer_template JSON schema and asks for a single
  normalized JSON object reconciling the chart, coding, evidence, provider
  contacts, and readiness/disposition. Triggers: "merge readiness", "referral
  coordination packet", "care transition packet", "duplicate review",
  "ServiceRequest quality", "referral audit", "normalized JSON conforming to
  answer_template".
---

# EHR governance / coordination packets

These tasks all share one shape: read a **read-only EHR quality API**, reconcile
the evidence, and emit **one normalized JSON object that conforms exactly to the
provided `answer_template`**. The template — not your prose — is the contract.
Getting these right is mostly about (a) obeying the template's keys/enums/
ordering literally and (b) applying a small set of reconciliation rules
consistently, while ignoring planted distractors.

## Procedure

1. **Read the answer template first.** It lists every required top-level key,
   the enum vocabulary for each field, ordering rules, and which arrays are
   "sets". Build your output to match its keys and types one-for-one. If it
   states a `required_value` (e.g. a `task_id`), emit it verbatim.

2. **Identify the case objects** named in the prompt: patient IDs, duplicate
   candidate ID, referral ID / batch ID, service-request ID, the recipient/
   specialist provider, service line.

3. **Pull every relevant record** from the environment's read-only endpoints
   before deciding anything: patient demographics, active clinical lists
   (conditions / medications / allergies), encounters, immunizations,
   disclosures, documents, service-requests, referrals, duplicate candidates,
   audit logs, the provider directory, the ICD-10 directory, and the
   service-code directory. Fetch the reference directories (ICD-10,
   service-codes, providers) so you can *validate* codes and fill contact
   details rather than guess.

4. **Trust structured records over free text.** `coordination_note`,
   `care_plan_notes`, a duplicate `merge_preview`, "confirm X before letter"
   hints, and similar prose are **non-authoritative and frequently
   distractors**. If the structured record is complete/valid, treat it as
   ready even when a note nags for confirmation; if a preview disagrees with the
   patient's own active-list endpoints, the **patient endpoints win**.

5. **Apply the reconciliation rules** in `references/reconciliation-rules.md`
   for the packet type at hand (active-key unions, canonical/duplicate
   resolution, evidence & document selection, provider selection, ICD-10 and
   service-code validation, encounter selection, batch-audit logic, risk flags,
   readiness/disposition).

6. **Obey ordering and set semantics.** Sort exactly as the template says
   (alphabetical / ascending by id or code / newest-to-oldest). For
   "set-semantics" arrays order is ignored but **membership must be exact** —
   include every correct member and nothing extra.

7. **Emit JSON only** — no commentary. Correct enums, `YYYY-MM-DD` dates,
   booleans as booleans, `null` where the schema allows it.

## Core reconciliation principles (memorize these)

- **Active means active.** Any union/key list of "active" conditions/meds/
  allergies = every record whose `status == "active"`, keyed by
  `normalized_key`, unioned across all in-scope patients. Include *all* active
  keys regardless of how generic the key name looks; exclude only non-active
  records (`inactive`, `entered-in-error`) — those are your `excluded`/
  distractor lists.

- **Structured data beats notes/previews** (see step 4). This single rule
  resolves most "is it ready?" ambiguities.

- **Report stored status faithfully for duplicates.** A duplicate candidate's
  `status` and each patient's `canonical_status` are the source of truth for
  the disposition; don't override them with your own clinical theory.

- **Validate codes, don't eyeball them.** Look each ICD-10 / service code up in
  the reference directory and compare chapter, laterality, and expected terms to
  the narrative and to the patient's own evidence.

- **Distractors are deliberate.** Namesake patients, stale/off-topic encounters,
  generic `chart_summary`/`ehr_export` documents, other patients' audit rows,
  inactive/legacy records, and nagging notes are planted to be *excluded*.

See `references/reconciliation-rules.md` for the detailed, per-packet rules and
`references/output-checklist.md` for a pre-submission check.
