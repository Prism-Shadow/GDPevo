---
name: ehr-referral-quality-packets
description: Produce normalized JSON "quality-governance packets" from a read-only EHR/referral API — duplicate-chart merge packets, referral coordination packets, care-transition packets, duplicate+service-request reviews, and batch referral audits. Read BEFORE producing any answer JSON for an EHR-quality or referral-coordination task that supplies an answer_template.json.
---

# EHR / Referral Quality-Governance Packet Skill

## When to use

Use this skill whenever a task asks you to produce a **normalized JSON packet** from a read-only
EHR/referral environment and supplies an `answer_template.json` describing the required shape.
The task families this covers:

- **Duplicate-chart merge readiness packets** — verify a duplicate candidate, pick canonical
  target/source, compute active clinical-list unions, capture identity match/conflict signals,
  and gather document/audit/provider contact evidence.
- **Referral coordination packets** — reconcile a referral with the patient's active chart,
  validate the ICD-10 code against the narrative, check allergy/document/authorization readiness,
  and choose normalized referral-letter field values.
- **Care-transition packets** — select the most relevant recent handoff encounters for a service
  line, attach the latest immunization, applicable disclosure, and risk flags.
- **Duplicate + ServiceRequest reviews** — decide a duplicate-review disposition and validate a
  draft ServiceRequest's codes, provider routing, and SBAR coverage.
- **Batch referral audits** — over a referral batch, flag invalid/out-of-range codes, laterality
  or narrative mismatches, duplicate groups, insurance anomalies, follow-up queues, tiered
  action plans, and summary counts.

## Core procedure (every task)

### 1. Read the prompt, the answer template, and any request payload
- The **prompt** names the case objects (candidate IDs, patient IDs, referral IDs, batch IDs,
  provider IDs) and the goal. Copy these IDs verbatim — they are the join keys for every fetch.
- The **answer template** is the contract. Read every field's type and `enum`/`allowed_values`
  before fetching anything. Note which arrays are **sets** (`set_semantics: true` or "evaluation
  treats as a set") vs. ordered, and the required ordering ("sort ascending", "newest to oldest").
- Where a request payload exists (e.g. `merge_packet_request.json`), use its `requested_outputs`
  as a checklist of sections to populate.

### 2. Pull only what the prompt names, then fan out by the template's sections
Fetch the named object first, then the patient/provider/condition/etc. records the template's
fields imply. Do **not** fetch unrelated patients "in case" — the prompts are scoped, and the
environment contains distractor records deliberately planted to test filtering.

Common fan-out per patient: `conditions`, `medications`, `allergies`, `encounters`,
`immunizations`, `documents`, `disclosures`, `service-requests`. Per referral/duplicate/service
request: the object itself plus the referenced patient and provider. For codes: the ICD-10 and
service-code lookup endpoints.

Cache the raw JSON locally while working so re-classification rounds don't re-hit the API.

### 3. Filter by status, then normalize to keys
- **Active-list unions** use only records with `status: "active"`. Records with `status:
  "inactive"` (often a `legacy_import`/`external_note` of the *other* laterality) are
  **excluded distractors**, not part of the union — list them in the `excluded_distractors` block
  when the template asks for it.
- Use the record's `normalized_key` (not the free-text name or code) as the set element. A
  condition appearing twice (e.g. on `problem_list` and `pcp_note`) contributes **one** key.
- Duplicate-candidate `merge_preview` lists are usually a **subset** of the true active union.
  Reconcile against the per-patient active endpoints and record the keys present in the endpoints
  but missing from the preview in any `active_list_reconciliation` / "added from active endpoints"
  field. The authoritative source is the patient active-list endpoints, not the preview.

### 4. Classify identity / duplicate signals
- `match_signals` and `conflict_signals` come **straight from the duplicate-candidate record** —
  copy them, do not re-derive or relabel.
- A `name_variant` signal is a **match**, not a conflict — do not list name variation under
  conflicts. Treat only the candidate's listed conflict signals (e.g. `address_abbreviation`,
  `different_given_name`, `opposite_laterality_problem`) as conflicts.
- **Disposition mapping** (the single highest-value judgment call):
  - `confirmed_duplicate` / `merge` → set `merge_target`/`merge_source` to the canonical pair and
    emit `merge_ready`.
  - `needs_review` / mixed match+conflict signals (including an `opposite_laterality_problem`) →
    `needs_review` + `review_hold`, and leave `merge_target`/`merge_source` **null** (no merge is
    committed during a hold). Do **not** auto-reject to `do_not_merge` on the strength of an
    opposite-laterality conflict alone, and do **not** populate a tentative target during a hold.
  - A single minor conflict (e.g. `address_abbreviation`) on an otherwise strong match does **not**
    flip a `merge_ready` disposition to `merge_ready_with_conflict_review` — keep it plain
    `merge_ready`/`ready` with `manual_review_required: false`. Escalating a minor conflict to a
    review-note disposition is incorrect; only the candidate's own `needs_review` status warrants
    a hold.
- Canonical target = the record with `canonical_status: "active"` and `canonical_patient_id: null`;
  source = the record with `canonical_status: "duplicate"` (its `canonical_patient_id` points back
  to the target).

### 5. Validate codes against the ICD-10 directory
For each diagnosis/service code in scope, call the lookup endpoint and read `chapter`,
`expected_terms`, and `requires_laterality`. Then classify (this is the second highest-value
judgment call):
- Code not in the directory → `unknown_code` (invalid).
- Code valid but its `chapter` is outside the service line's expected chapters (e.g. a
  `Respiratory` J-code on an orthopedic batch; orthopedic = `Musculoskeletal` + `Injury`) →
  `out_of_range_chapter`.
- Code valid and in-chapter: compare the **referral narrative** to the directory `expected_terms`
  and to the code's laterality:
  - narrative laterality token (`left`/`right`) **conflicts** with the code's laterality token →
    `laterality_mismatch`.
  - none of the `expected_terms` appear in the narrative → `narrative_mismatch`.
  - code `requires_laterality: true` but the narrative carries no laterality token **and** is the
    same anatomical condition → `missing_laterality`. Do **not** append `missing_laterality` when
    the narrative is about a different body region entirely (that is a `narrative_mismatch` only).
- `matches_patient_evidence` / `referral_relevant`: true only when the patient's own active
  conditions/encounters contain that code or a same-site condition. For a code-vs-narrative
  mismatch on a *narrative* field (e.g. "HFpEF" vs a "diastolic HF" code), prefer the literal
  directory text: if the term does not appear, `valid_but_narrative_mismatch` with
  `narrative_match: false` is the safer classification than forcing a match.

### 6. Map clinical records to risk flags and readiness enums
- Risk flags and readiness enums are **closed lists**. Only emit a flag/enum value that appears in
  the template's `allowed_values`/`enum`. If nothing fits, prefer the enum whose name most
  literally matches the environment signal over an invented `other`.
- Drive readiness from the **most specific** environment signal available: a `coordination_note`
  like "confirm … details before letter" means that readiness dimension is
  `incomplete_needs_clarification` regardless of whether the sub-records look complete. Document
  "received" lists on a referral are authoritative for `received` booleans.
- Keep the readiness story **internally consistent**: the `overall_readiness`, the
  `blocking_issues` set, and any letter-field `*_choice` must all point at the same blocker. Don't
  emit `hold_for_allergy_clarification` in one place and `ready_to_send` in another.

### 7. Encounter / referral selection
- "Most relevant recent handoff encounters" for a service line: prefer the encounters on the
  **surgical-workup / care-transition trajectory** for the operated joint — the linked series of
  visits that track that joint's osteoarthritis and the preoperative plan — newest to oldest,
  capped at the requested count. Exclude clearly non-handoff visits (geriatric/memory, unrelated
  telehealth) and stale out-of-window follow-ups. Recency alone is **not** sufficient — a fresher
  unrelated visit should not displace a relevant older workup visit. Selecting the N newest visits
  while excluding only an obviously off-topic one is the wrong rule; the joint-workup trajectory
  is the right one.
- Record both `selected_encounter_ids` (in display order) and `excluded_encounter_ids` (all
  reviewed-but-excluded, sorted ascending) when the template asks.

### 8. Batch audits — classify every referral, then aggregate
- Build one classification record per referral (chapter validity, mismatch types, document
  presence, authorization status, urgency, receiving provider) **before** assembling any section.
  Derive every count and queue from those records programmatically so counts and arrays cannot
  drift apart.
- Tiering rule that fit the data:
  - **Tier 1** `urgent_coding_or_duplicate_blocker`: urgent urgency, OR the duplicate-resubmission
    row, OR an invalid/out-of-range code.
  - **Tier 3** `administrative_document_completion`: routine, clinically validated (no mismatch,
    not invalid), authorization approved, but missing a document (office note or imaging).
  - **Tier 2** `routine_coding_auth_or_document_blocker`: all other routine referrals (mismatch,
    auth-missing, or other document blocker).
- Duplicate groups: same `patient_id` with >1 referral → one `same_patient_resubmission` group,
  consolidated under the original; the resubmission row (often an ID ending `-DUP` or flagged
  "duplicate resubmission") is the Tier-1 duplicate blocker; the original stays a separate
  clinical review.
- Insurance anomalies: a shared `insurance_id` across *different* patients is a
  `shared_insurance_different_patients` anomaly with disposition `verify…_do_not_merge`. The
  same-patient separate-clinical-referrals case belongs to duplicate tiering, not the insurance
  anomaly list — don't double-count.
- Follow-up queues are keyed by **referral_id**, sorted ascending. `authorization_missing` and
  `authorization_pending` come from the referral's `authorization_status`
  (`missing`/`pending`). `records_request` = referrals missing the office-note document.
  `imaging_follow_up` = referrals missing imaging **or** flagged "imaging pending" in a
  coordination note — check both signals.

### 9. Emit normalized JSON only
- Output exactly one JSON object conforming to the template, with every required top-level key.
  No prose outside the object.
- Sort all set/ID arrays as the template specifies (usually ascending; encounters often newest to
  oldest; objects in arrays sorted by their ID unless stated).
- Use `null` (not omitted, not empty string) for nullable fields the template marks
  `string | null` — e.g. merge target/source during a review hold, or a missing document's
  `document_id`.
- Dates as `YYYY-MM-DD`. Booleans as JSON `true`/`false`.

## Cross-task pitfalls observed
- **Do not escalate minor conflicts.** A single address-abbreviation or name-variant signal on a
  strong match keeps `merge_ready`; only the candidate's own `status: needs_review` justifies a
  `review_hold`.
- **Do not auto-populate merge target/source on a hold.** Review-hold means no merge is decided;
  both stay `null`.
- **Do not trust the duplicate `merge_preview` as the full clinical picture.** Re-derive active
  unions from the per-patient endpoints and reconcile the delta.
- **Do not mix readiness stories.** Pick one dominant blocker and align every readiness/choice
  field to it.
- **Do not over-flag `missing_laterality`** when the narrative is about a different body region —
  that is `narrative_mismatch` only.
- **Do not let counts drift from arrays.** Aggregate counts from the same classification records
  that produce the arrays.
- **Prefer the literal, template-aligned enum value.** When a classification is genuinely
  ambiguous, choose the allowed value whose name most literally matches the environment's explicit
  signals (status fields, coordination notes, resubmission ID markers) over a reasonable-but-invented
  classification. Closed-enum and selection fields are where internally-consistent candidates most
  often diverge from the intended answer, so be strict and literal there.

## Scope note
This skill describes how to read the prompt, gather and filter environment data, classify it, and
shape the normalized JSON output. It is instance-independent: it carries no specific task IDs,
answer values, or environment addresses, and it applies to any EHR-quality or referral-coordination
packet task that provides an answer template.
