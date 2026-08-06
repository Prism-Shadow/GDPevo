# Audit Logic Reference

The portal serves several intake-audit domains (new-patient access verification,
referral readiness, transfer review, chronic-care enrollment panels). The
*classifications* differ per domain, but the underlying evidence-checking patterns
are shared. Apply these patterns, then map the evidence to the exact enum members
defined in the current task's `answer_template.json`.

Throughout: "the template" means `input/payloads/answer_template.json` for the
current task. Its allowed enum values are the only values you may emit.

## 1. Completeness checks

- **Missing records / imaging (referrals):** `records_received = 0` → missing
  records; `imaging_received = 0` → missing imaging. Emit the matching blocker /
  issue code only when the template lists it.
- **Missing required documents (transfers):** compare the required packet document
  set (per the template's allowed doc types) against the documents actually
  received *and finalized* for the transfer. Any required doc absent (or only
  present as a non-final draft) goes in `missing_required_documents`, ordered as
  the template specifies.
- **Missing chart artifacts (enrollment):** compare required chart artifacts
  (chart_record, active_problems, vitals, labs, medications, consent, per the
  template) against `chart_artifacts[]` / `active_problems[]` /
  `recent_vitals_labs[]` / `meds_allergies[]` and the candidate's `consent_status`
  / `existing_chart`. Absent artifacts go in `missing_chart_artifacts`.
- A packet/chart is "complete" only when no required item is missing.

## 2. Freshness checks

- For documents that carry a `freshness_limit_days` (labs, serology, PPD/CXR,
  history & physical, etc.), compute age = `as_of_date − received_date` (calendar
  days). If age > `freshness_limit_days`, the document is **stale**.
- Stale items go in `stale_documents` with `doc_type`, `received_date`, and
  `freshness_limit_days`, ordered as the template specifies.
- Use the task's reference date (`as_of_date` / `requested_service_date`) as
  "today" — read it from the environment, not the prompt.

## 3. Clinical coding consistency (referrals)

For each referral, fetch `GET /icd/{icd10_code}` and compare against the referral's
`service_line`, `diagnosis_description`, and `referral_reason`:

- **Chapter / service-family mismatch:** the ICD code's `service_family` or
  `chapter` does not match the service line the batch is for (e.g., an injury
  chapter code on a musculoskeletal-service batch). Record `observed_chapter` and
  `expected_chapter`.
- **Narrative mismatch:** the `diagnosis_description` / `referral_reason`
  contradicts the coded condition.
- **Laterality mismatch:** the code's `laterality` conflicts with the site
  described in the reason.

Each discrepancy drives a `clinical_code_discrepancy` / ICD-discrepancy entry and
the matching issue code. These are clinical clarifications → typically route to
under_review and a code-clarification correspondence.

## 4. Duplicate detection (referrals)

- Group referrals in the same batch that share the same `patient_id` (and same /
  similar service). Two+ referrals for one patient in one batch = a duplicate
  group.
- Pick the **primary** per the batch rule (commonly the earliest `date_received`,
  tie-broken by lowest `referral_id`). Recommendation is usually
  `consolidate_to_primary`; only `keep_separate` when evidence shows genuinely
  distinct services.
- Referrals that are **not** part of any duplicate group are "cleared" of
  duplicate review — list them where the template asks for cleared referrals.
- A duplicate flag is an *administrative* follow-up, not a hard clinical block.

## 5. Shared-insurance anomalies (referrals)

- Group referrals by `insurance_id`. The same `insurance_id` appearing across
  referrals for **different** `patient_id`s is an anomaly → disposition
  `verify_distinct_patient_policy_id` (could be two patients on one policy, or a
  data-entry collision — needs verification).
- The same `insurance_id` for the **same** patient is a legitimate duplicate →
  `legitimate_duplicate_same_patient`.
- This is an administrative follow-up, not a clinical block.

## 6. Authorization (referrals)

- When `auth_required = 1`: `auth_status` of `pending`, `denied`, or
  `not_submitted` is an **auth blocker** (hard block). `approved` is not.
- When `auth_required = 0` / `auth_status = not_required`: no auth blocker.
- Auth blockers make a referral `blocked`, not merely under_review.

## 7. Capacity & feasibility (transfers)

- Look up `facility_capacity` for the transfer's `requested_start_date` (and
  modality / chair window). `capacity_status` = `available` when open chairs > 0
  on that date, else `unavailable`. `open_chairs_total` is the sum of open
  in-center hemodialysis chairs across Cedar Ridge locations for that date.
- **Feasibility** combines packet readiness with capacity:
  - complete packet + capacity available → `ready_on_requested_start`
  - packet not ready + capacity available → `packet_not_ready_capacity_available`
  - packet not ready + capacity unavailable → `packet_not_ready_capacity_unavailable`
  - complete packet + capacity unavailable → `capacity_unavailable`

## 8. Risk classification (new-patient access)

- `lifestyle_risk` is derived from the `lifestyle` record's risk factors.
- `overall_risk` rolls up `lifestyle_risk` plus the chart's `clinical_history`
  risk flags / recent hospitalization. High overall risk typically emits an
  `overall_risk_high` blocker.
- Insurance / prescription / pharmacy statuses (`valid|invalid|missing`,
  `in_network|out_of_network|unknown`) come from `coverage`, `pbm`, and
  `patient_pharmacy`+`pharmacies` respectively. Each gap emits its specific
  blocker code from the template's allowed list.

## 9. Eligibility & enrollment (chronic-care panels)

- **Eligible** when the candidate's `target_condition` matches the program's
  target AND an active target diagnosis is present in the chart AND the candidate
  is otherwise in scope. Otherwise **ineligible** (e.g., wrong target condition,
  missing active diagnosis).
- **Enrollment status:**
  - `enroll` — eligible, consent signed, chart active and complete enough to start.
  - `hold` — eligible but missing consent and/or chart artifacts that must be
    remediated first.
  - `reject` — consent declined, wrong target condition, or chart not active.
- `reason_codes` capture *why* (meets-criteria driver + any high-touch/CKD driver,
  or the blocking reasons). Use only the template's allowed reason codes.
- `follow_up_cadence` and `initial_monitoring_package` follow acuity:
  high-touch drivers (recent hospitalization, recent ED, low adherence) → weekly
  cadence + `high_touch_dm_htn` package; CKD driver → biweekly + biweekly
  monitoring; standard eligible → monthly + `standard_dm_htn`; hold → deferred;
  reject → none / `not_applicable`. `first_checkin_days` follows cadence
  (e.g., weekly ≈ 7, biweekly ≈ 14, monthly ≈ 30; null for deferred/reject).

## 10. Readiness taxonomy (referrals)

Map evidence to the template's `readiness_status` enum (commonly
`ready / blocked / under_review / admin_followup` — confirm members from the
template):

- **ready** — no issues whatsoever (no coding discrepancy, no missing records /
  imaging, no auth blocker, not a duplicate, no shared-insurance anomaly, not
  already scheduled). Any issue at all disqualifies "ready".
- **blocked** — a hard blocker: missing records, missing imaging, or an auth
  blocker (pending/denied/not_submitted).
- **under_review** — a clinical/coding discrepancy needing clarification (ICD
  chapter/narrative/laterality mismatch).
- **admin_followup** — administrative: shared-insurance anomaly, duplicate, or
  already-scheduled appointment.

A single referral can carry multiple issue codes; its `readiness_status` is the
*most severe* applicable (blocked > under_review > admin_followup > ready).

## 11. Priority tiering (non-ready items)

Rank non-ready referrals for follow-up. Map urgency × readiness to the template's
priority tiers (commonly `tier_1_immediate / tier_2_short_term /
tier_3_administrative` — confirm from the template):

- **tier_1_immediate** — urgent clinical need, typically an urgent referral with a
  coding/clinical discrepancy.
- **tier_2_short_term** — routine blockers and routine under-review items.
- **tier_3_administrative** — admin follow-ups (shared insurance, duplicates,
  already-scheduled).

When the template asks for a `priority_order` list, rank non-ready referrals
1..N (rank 1 = highest priority) with a deterministic tiebreak (e.g., referral_id
ascending), including only non-ready referrals.

## 12. Contact routing & action plans

- **Correspondence queue (referrals):** one entry per non-ready referral that
  needs outbound contact. `template_type` follows the issue family (code
  clarification for coding discrepancies; auth/records request for auth or
  missing-records blockers; duplicate resolution for duplicates; appointment-hold
  notice for already-scheduled). `reason_codes` are the specific drivers.
- **Action plan (referrals):** per-referral `action_codes` mapped from its issue
  codes (request corrected ICD, confirm narrative/laterality, consolidate
  duplicate, verify insurance id, request records/imaging, resolve authorization,
  review existing appointment).
- **Transfer contact routing:** `final_intake_decision` (accept / hold /
  clinical_review) follows feasibility; `next_contact_owner` and
  `next_contact_route` follow the decision and the dominant gap (packet gaps →
  clinical nurse via fax to referring facility; scheduling gaps → scheduling
  coordinator via internal queue; etc.). Use only the template's allowed values.
- **Enrollment outreach:** `outreach_channel` follows the candidate's
  `preferred_outreach` when available, else a fallback the template allows.

## 13. Building the summary / cohort counts

- Every summary is **integer counts** keyed exactly by the template's required
  count keys.
- Counts must reconcile: the total equals the number of per-entity rows; the
  per-status counts sum to the total; cross-tab counts (e.g., urgency ×
  readiness) sum to the total. Re-derive counts from your final per-entity lists,
  not from memory.
- Include a key for every status the template lists, even when its count is 0.
