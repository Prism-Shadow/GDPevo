# Archetype B — Referral readiness / referral-to-chart activation

**Recognize it by:** a `batch_id` for a referral batch (single `service_line` such as
orthopedics or pulmonary) and an `answer_template.json` about per-referral **readiness_status**,
ICD/coding discrepancies, duplicates, blockers (records/imaging/authorization), and follow-up
priority. Two label vocabularies exist for the same engine:

- **"Readiness audit" variant** (orthopedic-style): `referral_reviews`, `icd_discrepancies`,
  `duplicate_groups`, `shared_insurance_anomalies`, `blocker_sets`, `ready_to_schedule`,
  `action_plan`, `summary`.
- **"Chart activation" variant** (pulmonary-style): `readiness_by_referral`,
  `clinical_code_discrepancy_referrals`, `blocker_sets`, `duplicate_handling`,
  `ready_referral_chart_needs`, `correspondence_queue`, `priority_order`.

Always take the exact allowed enum/code strings from the current task's template. Pull the batch:
`SELECT * FROM referrals WHERE batch_id=? ORDER BY referral_id`, then join `icd_codes` on
`icd10_code`, `patients` on `patient_id`, and `chart_artifacts` on `patient_id`.

## Per-referral atomic flags (pure column tests on the `referrals` row)

| flag | condition |
|---|---|
| missing records | `records_received = 0` |
| missing imaging | `imaging_received = 0` |
| auth blocker | `auth_required = 1 AND auth_status <> 'approved'` (pending/denied/not_submitted) |
| scheduled | `appointment_scheduled = 1` |

(The `documents` table is **not** the driver for records/imaging — the boolean columns on the
referral row are.)

## Coding discrepancy (ICD)

Look up the code → `icd_codes.chapter`, `service_family`, `laterality`. Each service line has an
**accepted-chapter set**; a code is a coding discrepancy when its chapter is **not** in that set:

| service_line | accepted chapters |
|---|---|
| orthopedics | M00-M99 only (injury chapter **S00-T88 is flagged**, even though its family is orthopedics) |
| pulmonary | J00-J99, R00-R99 |
| cardiology | I00-I99 |
| dialysis | Z00-Z99 |
| chronic_care | E00-E89, I00-I99, N00-N99 |

For a service line not listed, derive its accepted chapters from
`SELECT DISTINCT chapter FROM icd_codes WHERE service_family='<service_line>'`.

Label mapping:
- Readiness-audit variant → issue `icd_chapter_mismatch`; the `icd_discrepancies` entry reports
  `observed_chapter = icd_codes.chapter` and `expected_chapter` = the canonical accepted chapter
  for the line (e.g. `M00-M99`).
- Chart-activation variant → blocker `clinical_code_discrepancy`; the correspondence reason is
  `wrong_service_family`.

**Narrative mismatch** (separate check): the code family fits the line but `referral_reason`
belongs to another specialty's vocabulary (observed: `pain evaluation` — a musculoskeletal
reason — on a respiratory referral). Readiness-audit label `narrative_mismatch`; chart-activation
this still sets `clinical_code_discrepancy` with correspondence reason `clinical_reason_mismatch`.
If service family is wrong, use the family/chapter finding and do **not** also emit narrative.

**Laterality mismatch** (separate check): `icd_codes.laterality` is left/right and the free text
(`diagnosis_description`/`referral_reason`) explicitly names the opposite side. Rare; emit only on
a direct contradiction.

## Duplicates
Group batch referrals sharing the **same `patient_id`** and matching clinical content (same
`icd10_code`; corroborated by shared reason/phone/fax/insurance and any "possible duplicate" note).
- `group_id` = `"DUP-" + batch_id + "-" + 3-digit sequence` (`DUP-<BATCH>-001`), numbered by the
  group's smallest referral_id.
- `referral_ids` ascending; the kept/primary referral = the **lowest referral_id**.
- Readiness-audit `recommendation` = `consolidate_to_primary` for a true duplicate.
- A referral carrying a "possible duplicate" note whose patient is actually **unique** in the
  batch is a false alarm → in the chart-activation variant it goes to
  `duplicate_handling.cleared_duplicate_review_referrals` (and gets no duplicate blocker).
- Members carry issue `duplicate_referral` / blocker `duplicate_review` (review-tier).

## Shared-insurance anomaly (readiness-audit variant)
Group by `insurance_id`; flag when one `insurance_id` is used by **≥ 2 distinct patients**. Entry:
`insurance_id`, `referral_ids` (asc), `patient_ids` (asc, distinct), `disposition =
verify_distinct_patient_policy_id`. A shared insurance_id all belonging to one patient is the
duplicate case, not this. Involved referrals carry issue `shared_insurance_anomaly` (admin-tier).

## Blocker sets
- Readiness-audit: `missing_records` (asc ids), `missing_imaging` (asc ids), `auth_blockers` =
  `[{referral_id, auth_status}]` (asc) for the auth-blocker condition.
- Chart-activation: `authorization`, `records`, `imaging` — each an ascending list of referral_ids.

## Readiness status — severity buckets with precedence
Assemble each referral's code set (union of all flags/checks that fired), then take the highest
bucket. **blocked > under_review > admin_followup > ready.**

| bucket → status | codes |
|---|---|
| hard blocker → `blocked` | missing records, missing imaging, auth blocker |
| review → `under_review` | any coding discrepancy, duplicate, scheduled/already-scheduled |
| admin → `admin_followup` | shared-insurance anomaly (readiness-audit only) |
| none → `ready` | — |

`scheduled` and `duplicate` are review-tier, not hard blockers.

## Priority tier (for non-ready referrals)
1. `tier_1_immediate` if `urgency='urgent'`.
2. else `tier_3_administrative` if `readiness_status = admin_followup`.
3. else `tier_2_short_term`.
(`urgency='admin'` → treat as tier_3.) In `referral_reviews`, `priority_tier` is `null` when the
referral is `ready`.

## Action plan (readiness-audit variant)
One entry per non-ready referral: `{referral_id, priority_tier, action_codes}`, ascending. Map
each fired issue to an action code:

| issue | action |
|---|---|
| icd_chapter_mismatch | request_corrected_icd |
| narrative_mismatch | confirm_narrative |
| laterality_mismatch | confirm_laterality |
| duplicate_referral | consolidate_duplicate |
| shared_insurance_anomaly | verify_insurance_id |
| missing_records | request_records |
| missing_imaging | request_imaging |
| auth_blocker | resolve_authorization |
| already_scheduled | review_existing_appointment |

## Chart-activation-only outputs

**`clinical_code_discrepancy_referrals`** — ascending ids whose blocker set contains
`clinical_code_discrepancy`.

**`ready_referral_chart_needs`** — one entry per **ready** referral: `{referral_id, patient_id,
chart_action, artifacts_to_create}`, ascending.
- `chart_action`: `patients.existing_chart=1` → `update_chart`; `=0` → `create_chart`;
  `no_chart_action` if a chart exists and nothing needs creating/refreshing.
- `artifacts_to_create`: over the template's 7 artifact enums
  {demographics, active_problems, medications, allergies, vitals, labs, consent}, include one iff
  the patient has **no `chart_artifacts` row of that type with `status='current'`** (absent, or
  status stale/draft, both count). Sort **alphabetically by the enum string**. Ignore artifact
  types outside the enum (care_plan, outreach_preference).

**`correspondence_queue`** — one entry per **non-ready** referral: `{referral_id, template_type,
reason_codes}`, ascending. Reason codes (union of what fired):

| fired | reason_code |
|---|---|
| clinical code discrepancy via wrong family | wrong_service_family |
| clinical code discrepancy via narrative | clinical_reason_mismatch |
| records missing | records_missing |
| authorization blocked | authorization_denied |
| duplicate review | duplicate_review |
| scheduled before clearance | appointment_already_scheduled |

`template_type` = single highest-precedence category present, top first:
1. `appointment_hold_notice` if scheduled-before-clearance present.
2. `auth_records_request` elif authorization/records/imaging blocker present.
3. `clinical_code_clarification` elif a clinical code discrepancy present.
4. `duplicate_resolution` elif duplicate review present.

**`priority_order`** — rank the **non-ready** referrals, `{rank, referral_id, priority_tier}`,
`rank` from 1. Sort: (1) priority_tier tier_1→tier_2→tier_3; (2) has clinical_code_discrepancy
first; (3) more blocker_codes first; (4) referral_id ascending.

## Summary (readiness-audit variant)
- `total_referrals`; `ready_to_schedule_count` = #ready; `follow_up_count` = total − ready.
- `counts_by_urgency` over {urgent, routine, admin} from `referrals.urgency` (zero-filled).
- `counts_by_readiness_status` over {ready, blocked, under_review, admin_followup} (zero-filled).
- `counts_by_urgency_and_status` = `[{urgency, readiness_status, count}]` for **count>0 only**,
  ordered by urgency then readiness_status (plain alphabetical).
- `issue_counts`: lengths of icd_discrepancies, duplicate_groups, shared_insurance_anomalies, and
  the missing_records / missing_imaging / auth_blocker referral sets.

## Ordering
All referral lists ascending by `referral_id` (uppercase, exactly as stored) unless a section says
otherwise. Issue/blocker/action/reason arrays are unordered sets (ground truth tends to be
alphabetical — emit sorted to be safe). `ready_to_schedule` / empty sections stay `[]`.
