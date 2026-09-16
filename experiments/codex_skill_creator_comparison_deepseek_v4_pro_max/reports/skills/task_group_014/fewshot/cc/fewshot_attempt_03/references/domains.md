# Domain Reference

Each supported task domain defines its own criteria set, source-precedence
rule, and output-signaling pattern. Use this reference to identify the domain,
evaluate its criteria, and select the correct determination route.

## How to Identify the Domain

Check the task context (`input/payloads/task_context.json`) for these signals
in order of priority:

1. **`service_domain`** field: `physical_therapy`, `cardiac_imaging`, or absent
   (margin tasks omit it).
2. **`work_type`** or **`work_item.request_type`**: `coverage appeal`,
   `peer_to_peer`, `claim repricing`, or absent.
3. **`requester_role`**: `UM nurse reviewer`, `pharmacy appeals coordinator`,
   `payment integrity analyst`, `peer-to-peer coordinator`, or
   `UM-finance operations analyst`.

Cross-reference with the domain table in the main SKILL.md to confirm.

---

## UM Clinical Review (Physical Therapy)

**Signal:** `service_domain: "physical_therapy"`, `requester_role: "UM nurse reviewer"`.

**Criteria:**

| ID | Meaning | Evidence Needed |
|----|---------|-----------------|
| `PT-ACTIVE` | Policy is active for the member on the requested service dates. | Member coverage record, plan effective dates. |
| `PT-DEFICIT` | Documented functional deficit matching a covered diagnosis. | Clinical evaluation document, diagnosis codes. |
| `PT-DX` | Diagnosis is covered under the applicable plan. | Policy coverage criteria, evaluation document. |
| `PT-POC` | A signed plan of care exists with frequency, duration, and CPT codes. | Plan-of-care document with provider signature. |
| `PT-UNITS` | Requested units fall within policy maximums for the service period. | Policy unit caps, plan-of-care unit count. |

**Enum choices:**
- `recommendation`: `approve`, `pend_for_information`, `escalate_to_md`, `deny`, `partial_approval`
- `route`: `nurse_approval`, `pending_information`, `medical_director_review`
- `final_status`: `approved`, `pended`, `md_review_required`, `denied`, `partially_approved`
- `determination_letter`: `approval`, `information_request`, `adverse_determination`, `partial_approval`

**Workflow notes:**
- Stale records out of effective-date range are excluded and listed in
  `excluded_documents`. Active clinical records become evidence.
- If all five PT criteria are met, route `nurse_approval`, status `approved`,
  and set `next_action` to `issue_approval`.
- If any clinician-only criterion is not met (`PT-DEFICIT`, `PT-DX` are the
  primary ones), route `medical_director_review`.
- Construct the authorization block from the plan-of-care: extract CPT codes
  ascending, set approved units from the plan, and derive start/end from the
  service date range.

---

## Pharmacy Appeals and Manufacturer Assistance

**Signal:** `work_type` contains `appeal` and `manufacturer assistance`,
`requester_role: "pharmacy appeals coordinator"`.

**Criteria:**

| ID | Meaning | Evidence Needed |
|----|---------|-----------------|
| `DRUG-AUTH` | A prior authorization or denial for the requested drug exists. | Authorization or denial record for the drug. |
| `DRUG-DENIAL` | The denial reason is documented and available for appeal. | Denial record with rationale text. |
| `DRUG-RATIONALE` | Prescriber rationale for the requested drug is on file. | Prescriber statement or appeal rationale. |
| `DRUG-FAILURES` | Sufficient documented formulary failures or contraindications. | Drug trial records, fill history, documented failures. |

**Enum choices:**
- `drug`: `Vraylar`, `Dupixent`, `Humira`, `Ozempic`, `Rinvoq`, `Skyrizi`
- `appeal_path`: `standard_internal`, `expedited_internal`, `external_review`, `not_eligible`
- `owner`: `appeals-rx`, `um-nurse`, `medical-director`, `payment-integrity`, `member-services`
- `next_action`: `request_more_information`, `file_appeal`, `complete_expedited_appeal_and_request_income_proof`, `submit_assistance_application`, `issue_denial`, `close_not_eligible`

**Workflow notes:**
- Distinguish documented failures (have a trial record with outcome) from
  undocumented or insufficient failures (mentioned but no supporting record).
  List lowercased medication names, alphabetical.
- If the drug requires step therapy, count documented failures against the
  step count. A partial `DRUG-FAILURES` result means some steps are documented
  but others are missing or insufficient.
- The appeal deadline is 30 calendar days from the denial date for standard
  internal appeals. For expedited, compute per plan rules.
- Packet items follow operational order: payer appeal items (denial notice,
  member authorization, prescriber rationale, formulary failure evidence)
  before manufacturer assistance items (household income proof).
- When the assistance program status is `eligible_missing_information`, list
  the missing fields in alphabetical order by field identifier.
- Use `payer_appeal_before_manufacturer_assistance` as the source precedence.
  Appeal records control the clinical determination; assistance records are
  subordinate.

---

## Payment Integrity Claim Repricing

**Signal:** `requester_role: "payment integrity analyst"`, claim repricing or
benchmark validation language.

**Criteria (per CPT line):**
Benchmark rates by CPT code, modifier, and the effective schedule version for
the plan modifier and date of service. Each claim line is corrected
independently.

**Enum choices:**
- `benchmark_source`: `Northstar Commercial Imaging Schedule`, `Legacy Imaging Export`, `Northstar Distractor Schedule`
- `stale_source_rejected`: one of the above or `none`
- `disposition`: `correct_upward`, `correct_downward`, `no_change`, `deny_line`
- `resubmission_route`: `payment_integrity_correction`, `provider_adjustment`, `appeal_reopen`, `no_resubmission`
- `priority`: `standard`, `expedited`, `urgent`, `monitor_only`

**Workflow notes:**
- Read the claim and its lines from the environment. Read all available rate
  schedules. Compare the schedule effective dates against the claim service
  date and plan modifier.
- The effective benchmark is the most recent schedule whose effective date
  precedes or equals the service date and whose plan modifier matches the
  claim.
- Reject stale schedules (effective date too old or before a known
  superseding version) and list the stale source in `stale_source_rejected`.
- Compute `correct_allowed_amount` as the benchmark rate times units for each
  line. `recovery_amount` is `correct_allowed_amount - paid_amount` (positive
  means upward correction; use the absolute underpayment amount when
  `correct_allowed_total > paid_total`).
- Aggregate line amounts for the claim-level totals.
- Use `null` for absent modifiers; never an empty string.
- Lines are listed in claim-line order from the source claim.

---

## Peer-to-Peer Coordination (Cardiac Imaging)

**Signal:** `service_domain: "cardiac_imaging"` with P2P or peer-to-peer
language, `requester_role: "peer-to-peer coordinator"`.

**Criteria:**

| ID | Meaning | Evidence Needed |
|----|---------|-----------------|
| `PET-IND` | The clinical indication for PET MPI is documented. | Cardiology consult, clinical evidence document. |
| `PET-FACTOR` | At least one PET-over-SPECT factor is supported by evidence. | Clinical documentation of BMI limitation, prior equivocal SPECT, or attenuation artifact. |

**Enum choices:**
- `p2p_outcome`: `not_applicable`, `overturn_to_approval`, `uphold_intended_adverse_decision`
- `final_status`: `approved`, `denied` (primary outcomes for P2P)
- `letter_type`: `approval`, `denial`, `partial_denial`, `no_letter`
- `recommended_alternative`: `SPECT MPI`, `PET MPI`, `none`
- `missing_pet_factors`: `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`

**Workflow notes:**
- Both `PET-IND` and `PET-FACTOR` must be met for approval.
- When `PET-FACTOR` is `not_met`, list all three PET-over-SPECT factors in
  `missing_pet_factors` (in the order shown in the template: prior_equivocal_spect,
  bmi_limitation, attenuation_artifact).
- If the P2P provided new patient-specific information that changed the review,
  set `new_information_changed_review` to `true`. This is true when the clinical
  evidence or P2P discussion added material facts not in the original
  authorization file.
- `p2p_outcome` `uphold_intended_adverse_decision` means the P2P did not change
  the original adverse determination.
- Internal appeal deadline: 180 calendar days from the final adverse
  determination date (the date the P2P outcome was recorded).
- Recommended alternative: `SPECT MPI` when PET is denied but the indication
  is met; `PET MPI` when approved; `none` when neither applies.
- Use `new_patient_specific_p2p_information` as the source precedence for P2P
  tasks.

---

## Margin Queue Analysis (Therapy Finance)

**Signal:** `requester_role: "UM-finance operations analyst"`, margin queue
language, `service_margin` table, `revenue_to_cost_ratio`.

**Concepts:**
- **Total cost:** `variable_cost + fixed_cost_allocated` from the finance memo.
- **Margin:** `revenue - total_cost`.
- **Revenue-to-cost ratio:** `revenue / total_cost`, rounded to four decimal
  places.
- **Below threshold:** `revenue_to_cost_ratio < threshold_revenue_to_cost_ratio`.
- **Charge sensitive:** The row is flagged as having variable charge patterns
  (indicated in the environment record).

**Enum choices:**
- `payer_segment`: `medicaid`, `commercial`, `workers_comp`
- `service_domain`: `physical_therapy`, `speech_therapy`, `occupational_therapy`
- `recommended_action`: `payer_contract_review`, `monitor_charge_sensitive`, `monitor_no_action`
- `top_issue`: `medicaid_97110`, `commercial_97530`, `workers_comp_97112`, `none`

**Workflow notes:**
- Collect each margin row by its `queue_row_id`. Query the `service_margin`
  table for the exact row IDs listed in the task context.
- Compute `total_cost`, `margin`, and `revenue_to_cost_ratio` for each row.
- A row is below threshold when revenue_to_cost falls below the threshold
  value from the task context memo. A row is charge sensitive when the
  environment record carries a charge-sensitivity flag.
- Rows below threshold with no charge-sensitivity flag take
  `payer_contract_review`. Rows not below threshold but flagged charge-sensitive
  take `monitor_charge_sensitive`. Rows with neither issue take
  `monitor_no_action`.
- `below_threshold_segments` lists payer segments (alphabetical) for rows
  where `below_threshold` is true.
- `charge_sensitive_segments` lists payer segments (alphabetical) for rows
  where `charge_sensitive` is true.
- `top_issue` is the below-threshold row with the largest absolute gap between
  revenue and the threshold (revenue minus 120% of cost). Format as
  `{payer_segment}_{cpt_code}`.
- `gap_to_120pct` is `(threshold * total_cost) - revenue` for the top issue,
  computed as a dollar amount rounded to two decimal places. It represents how
  much additional revenue would be needed to reach exactly 120% cost coverage.
- Source precedence: `margin_threshold_then_charge_sensitivity`.
