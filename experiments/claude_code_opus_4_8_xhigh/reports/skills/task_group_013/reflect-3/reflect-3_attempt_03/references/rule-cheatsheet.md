# Rule & enum-mapping cheatsheet

Concrete derivations for each field family. Apply only what the active template asks for, and always
constrain outputs to the template's `allowed_values`. Column/flag names refer to
`references/portal-schema.md`.

## Insurance status (per patient, for a service line + service date)
```
row = coverage for patient
if no row:                                     -> "missing"
lines = row.service_lines split on ","
expired  = row.status == "expired" OR (row.termination_date and row.termination_date < service_date)
pending  = row.status == "pending"
excluded = service_line not in lines
valid    = row.status == "active" and not expired and not excluded
status   = "valid" if valid else "invalid"
reason codes: coverage_expired if expired; coverage_pending if pending; excluded_service_line if excluded
```

## Prescription / PBM status (per patient)
```
p = pbm for patient
if no row:                                     -> "missing"  (+ pbm_missing)
mismatch = p.policy_number != coverage.policy_number  (or specialty_required indicates a mismatch)
if mismatch:                                   -> "invalid"  (+ pbm_policy_mismatch)
good = p.active==1 and p.formulary_status=="covered" and p.status=="approved"
-> "valid" if good else "invalid" (+ pbm_invalid)
```

## Pharmacy network (per patient)
```
take patient_pharmacy row with min preference_rank; join pharmacies.network_status
in_network / out_of_network ; if none -> unknown (+ pharmacy_unknown)
out_of_network -> reason pharmacy_out_of_network
```

## Lifestyle risk (per patient)  [validated point rule]
```
pts = (smoking_status=="Current") + (alcohol_use=="Heavy")
    + (exercise_frequency in {None, null}) + (sleep_hours < 6)
0 -> low ; 1..2 -> medium ; 3+ -> high
```

## Overall risk (per patient)
Composite of lifestyle risk and clinical acuity. Clinical signal: `recent_hospitalization`,
non-empty `risk_flags`, chronic-condition count. Escalate lifestyle upward for real clinical acuity;
absent acuity, do not push everything to high. `overall_risk == high` => reason `overall_risk_high`.

## Contact/demographic reason codes (per patient)
```
missing_address              : address is null
emergency_contact_missing    : emergency_contact_present == 0
preferred_contact_unavailable: preferred channel field is null
   (preferred_contact=="email" and email null) OR (preferred_contact in {phone,sms} and phone null)
```

## ICD discrepancy (per referral)  [service_family rule]
```
c = icd_codes[referral.icd10_code]
icd_chapter_mismatch : c.service_family != referral.service_line
   observed_chapter = c.chapter ; expected_chapter = canonical chapter of the service line's family
laterality_mismatch  : referral narrative states a side that contradicts c.laterality
narrative_mismatch   : referral narrative contradicts c.description
A family-matching code is NOT a chapter mismatch even if its chapter letter differs.
```

## Duplicates & shared insurance (across cohort)
```
duplicate group : same (patient_id, icd10_code) on >1 referral
   primary = lowest referral_id ; recommendation = consolidate_to_primary
   the non-primary members are the ones to consolidate/drop
shared insurance: same insurance_id on >1 referral
   patients differ -> verify_distinct_patient_policy_id
   same patient    -> legitimate_duplicate_same_patient
```

## Referral blocker codes
```
records_missing            : records_received == 0
imaging_missing            : imaging_received == 0
authorization_blocked      : auth_required == 1 and auth_status in {pending, denied, not_submitted}
scheduled_before_clearance : appointment_scheduled == 1 while not cleared
duplicate_review           : member of a duplicate group (esp. the non-primary)
clinical_code_discrepancy  : ICD family/chapter mismatch (see above)
```

## Document completeness & freshness (per transfer)
```
required set = template's missing_required_documents allowed_values
satisfied  : a matching document exists AND finalized == 1
missing    : required item not satisfied (draft or absent)
staleable doc types are a subset (labs, H&P, immunology/imaging screens, etc.)
stale : satisfied but age > freshness_limit_days
   age = reference_date - received_date ; reference_date = requested start / service date
freshness limits are policy; infer from data, defaults ~ monthly labs 30, H&P 180, screens 365
packet_completeness_status = "complete" if nothing missing else "incomplete"
```

## Capacity & feasibility (per transfer)
```
open_chairs_total = SUM(facility_capacity.open_chairs) for requested date & modality across locations
capacity_status = "available" if open_chairs_total > 0 else "unavailable"
feasibility:
  complete   & available   -> ready_on_requested_start
  incomplete & available   -> packet_not_ready_capacity_available
  incomplete & unavailable -> packet_not_ready_capacity_unavailable
  complete   & unavailable -> capacity_unavailable
```

## Chart action (per referral/patient)
```
existing_chart == 0                 -> create_chart (artifacts to create = required set)
existing_chart == 1 & missing types -> update_chart (artifacts to create = absent required types)
otherwise                           -> no_chart_action
artifacts_to_create ordered alphabetically by enum string.
absent (no row of that type) is different from stale (row exists, status=stale).
```

## Program eligibility (per candidate)
```
eligible: target_condition matches the program condition AND required active diagnosis present
  else -> wrong_target_condition (+ missing_active_<program>_diagnosis)
consent_status == declined -> reject (active refusal)
consent_status == missing  -> hold (recoverable) ; code consent_missing
chart/data gates: chart_not_active, stale_active_problems, missing_recent_vitals,
                  missing_recent_labs, missing_medication_list
high-touch triggers (raise cadence + package, shorten first check-in):
   recent_hospitalization, recent ED, low adherence, CKD (biweekly monitoring)
enrollment_status: enroll (eligible, consent signed, chart active, data current);
                   hold (eligible but recoverable gaps); reject (ineligible or declined)
```

## Status → tier / action mapping
```
Status precedence (first match wins):
  hard operational blocker / invalid coverage  -> blocked | rejected
  coding discrepancy / high clinical risk       -> under_review | clinical_review
  administrative only                           -> admin_followup | hold
  none pending                                  -> ready | approved
Administrative-only flags may still be schedulable: a record can be ready/approved while
carrying an issue code that is only tracked for follow-up.

Priority tiers:
  tier_1_immediate      : urgent clinical need OR time-critical (e.g. scheduled_before_clearance)
  tier_2_short_term     : routine clinical follow-up (missing records/imaging/auth on routine cases)
  tier_3_administrative : duplicate consolidation, shared-insurance verification, already-scheduled review

Action codes (referral audits):
  request_records | request_imaging | resolve_authorization | request_corrected_icd |
  confirm_narrative | confirm_laterality | consolidate_duplicate | verify_insurance_id |
  review_existing_appointment
Correspondence templates (chart activation):
  clinical_code_clarification | auth_records_request | duplicate_resolution | appointment_hold_notice
```

## Summary counts
Build every count object by iterating your finished per-record rows. Initialize each enum key to 0,
increment per row, so all keys (including zero counts) are present. Cross-tab counts (e.g. urgency ×
status) list only the combinations that occur, in the template's stated order. Never tally by hand.
