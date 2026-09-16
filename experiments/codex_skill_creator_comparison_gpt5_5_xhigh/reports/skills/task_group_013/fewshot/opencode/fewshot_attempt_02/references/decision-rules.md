# Cedar Ridge Decision Rules

These rules generalize the Cedar Ridge intake examples. Use the prompt and
template for the exact schema and controlled vocabulary on the current task.

## Shared Rules

- Filter to the target roster, referral batch, transfer batch, or program code
  before deriving statuses. Ignore distractor records from other groups.
- Use IDs exactly as supplied by the portal.
- For patient-level rows, sort by the template's key, usually patient ID,
  referral ID, or transfer ID ascending.
- For set-like code arrays, deduplicate and emit a stable order.
- For summaries, count from the final emitted row objects.

## Primary-Care Access Verification

Join roster rows to patient demographics, coverage, PBM, preferred pharmacy,
lifestyle, and clinical history.

Insurance:

- `valid`: active coverage, in network, service date within coverage dates, and
  requested service line included in `coverage.service_lines`.
- `invalid`: expired coverage, pending coverage, out-of-network coverage, or the
  requested service line is excluded.
- `missing`: no coverage row.

Prescription benefits:

- `valid`: PBM row is active/approved, formulary is covered, and payer/policy
  matches coverage.
- `invalid`: inactive/rejected/pending PBM, non-covered formulary, or PBM
  payer/policy mismatch.
- `missing`: no PBM row.

Preferred pharmacy:

- Use the rank-1 `patient_pharmacy` row and `pharmacies.network_status`.
- Map in-network to `in_network`, out-of-network to `out_of_network`, and no
  usable pharmacy/network to `unknown`.

Reason codes:

- Coverage: `coverage_expired`, `coverage_pending`, `excluded_service_line`.
- PBM: `pbm_invalid`, `pbm_missing`, `pbm_policy_mismatch`.
- Pharmacy: `pharmacy_out_of_network`, `pharmacy_unknown`.
- Demographics: `missing_address`, `emergency_contact_missing`,
  `preferred_contact_unavailable` when the preferred contact route lacks the
  needed phone/email.
- Risk: add `overall_risk_high` when the derived overall risk is high.

Risk:

- Lifestyle risk is high for current smoking, heavy alcohol use, no exercise, or
  short sleep. It is medium for former smoking, moderate alcohol, or otherwise
  borderline lifestyle data; otherwise low.
- Overall risk should be at least lifestyle risk and should rise to high for
  explicit clinical risk flags, recent hospitalization, or high lifestyle risk.

Registration:

- Reject when coverage is expired, missing, or explicitly excludes the requested
  service line.
- Approve only when required coverage/PBM/pharmacy/demographic/risk checks are
  clean.
- Use clinical review or hold for unresolved but non-rejection blockers; follow
  the template's allowed values.

## Referral Readiness And Chart Activation

Join target referrals to ICD metadata. Use referral row flags for records,
imaging, authorization, appointment scheduling, duplicate hints, and urgency.
Use chart artifacts only when the output schema asks for chart activation work.

Clinical code discrepancies:

- If `icd_codes.service_family` does not match the referral service line, mark a
  clinical/code discrepancy. In correspondence schemas, use a wrong-service
  reason when available.
- For orthopedics, the expected chapter is musculoskeletal (`M00-M99`); injury
  chapter codes are chapter mismatches even when the metadata service family is
  orthopedics.
- For pulmonary, pulmonary disease and symptom chapters can be acceptable when
  the referral reason is clinically pulmonary. A pain-focused referral reason
  paired with a pulmonary diagnosis is a narrative/clinical-reason mismatch.
- If the ICD has laterality, compare it with any narrative laterality in the
  referral text and flag laterality mismatch only on a direct conflict.

Operational blockers:

- `records_received == 0` means records missing.
- `imaging_received == 0` means imaging missing when the template tracks imaging.
- Authorization is blocked when authorization is required and status is pending,
  denied, or not submitted.
- A scheduled appointment on a referral that is not otherwise clear is an
  appointment/clearance issue.

Duplicate and insurance handling:

- Same patient in the same batch with duplicate notes, same insurance, or same
  referring contact pattern forms a duplicate group; keep the earliest or
  non-duplicate-looking referral as primary.
- Same insurance ID across different patients is a shared insurance anomaly.
- "Possible duplicate" notes that do not form a same-patient group should be
  treated as cleared duplicate review when the schema asks for cleared reviews.

Readiness:

- `blocked`: records, imaging, or authorization blockers are present.
- `admin_followup`: only administrative anomalies are present, such as shared
  insurance without clinical/operational blockers.
- `under_review`: clinical code, narrative, laterality, duplicate, or scheduled
  clearance issues are present without hard operational blockers.
- `ready`: no unresolved blockers remain.

Priority:

- Tier 1 for urgent clinical discrepancies or urgent non-ready referrals.
- Tier 2 for routine clinical review or operational blockers.
- Tier 3 for administrative-only follow-up.
- For ranked priority lists, sort by tier first, then scheduled-before-clearance
  or multi-blocker cases, then referral ID.

Chart activation:

- For ready referrals, inspect required chart artifacts from the template.
- `create_chart` when the patient has no existing chart, `update_chart` when a
  chart exists but required artifacts are missing or stale, and `no_chart_action`
  when nothing is missing.
- Artifacts to create are required artifacts absent from `chart_artifacts` or
  present with stale/non-current status. Sort as the template specifies.

## Dialysis Transfer Review

Filter `transfer_requests` by target batch and join packet `documents`.

Packet completeness:

- A required packet document counts as present only when a matching document is
  final and finalized.
- Draft, non-final, or absent required packet documents are missing.
- If the template includes a non-document operational item such as
  `transportation`, satisfy it from the transfer request field rather than from
  the documents table.
- Packet completeness is `complete` only when no required document is missing.

Freshness:

- Check stale documents separately from missing documents.
- Use requested start date as the comparison date.
- Common freshness limits are 30 days for HBsAg, monthly labs, and PPD/CXR, and
  365 days for history and physical. Do not mark a document stale solely because
  it appears in the missing-document enum; only apply freshness checks to the
  document types the packet rules treat as freshness-sensitive.
- Emit stale document objects only for final documents that are older than the
  applicable limit.

Capacity:

- Sum `facility_capacity.open_chairs` for the requested start date and modality
  across locations.
- Capacity is available when the total is greater than zero.

Decision:

- Accept only when packet is complete, no freshness blockers remain, and capacity
  is available.
- Hold when the packet is otherwise ready but capacity is unavailable.
- Use clinical review when documents are missing or stale.
- Contact the clinical nurse/referring facility for packet problems, scheduling
  for capacity-only problems, and no contact when accepted.

## Chronic-Care Enrollment

Join program candidates to patient demographics, clinical history, and chart
artifacts.

Eligibility:

- Infer the expected target condition from the program code and candidate list.
  Use an explicit program definition if exposed; otherwise use the dominant
  target condition for that program.
- A candidate is clinically eligible when the target condition matches and the
  active clinical history contains the required diagnoses for that program.
- Mark wrong target or missing active diagnosis when those checks fail.

Disposition:

- `enroll`: eligible, consent signed, active chart, and required chart artifacts
  are current.
- `hold`: eligible but consent is missing or chart artifacts must be updated.
- `reject`: wrong target/diagnosis, declined consent, or a hard inactive-chart
  condition that the template treats as rejection.

Reason codes, follow-up, and packages:

- Emit the positive "meets criteria" reason only for candidates who actually move
  into enrollment. For rejected or held candidates, use the blockers that explain
  why the panel cannot enroll them now.
- For ineligible wrong-target candidates, suppress soft chart cleanup reasons
  unless a hard blocker such as declined consent or inactive chart is itself part
  of the disposition.
- Weekly high-touch follow-up for recent hospitalization, recent ED flag, or low
  adherence.
- Biweekly follow-up for CKD when no higher-touch trigger applies.
- Monthly follow-up for standard eligible enrollments.
- Deferred for holds and none for rejects.
- High-touch packages include monitoring devices, lab order, medication
  reconciliation, and care-plan setup when those components are allowed.
- Standard packages include monitoring devices and labs; add medication
  reconciliation for CKD/biweekly cases when allowed.
- Deferred packages should include consent and chart update work when allowed.

Outreach:

- Start with candidate preferred outreach.
- If the preferred channel is unusable, fall back to an available patient route:
  phone or SMS require a phone number, email requires an email address, and
  portal generally requires an active existing chart.
