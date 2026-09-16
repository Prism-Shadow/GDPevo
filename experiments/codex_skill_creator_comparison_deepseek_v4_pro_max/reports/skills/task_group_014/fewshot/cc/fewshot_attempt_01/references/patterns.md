# Domain Pattern Reference

This reference breaks down each of the five Northstar task domains with
field-by-field mappings, ordering conventions, and record classification rules.
It extends the main SKILL.md workflow with detail you can consult when a
specific domain requires deeper guidance.

## 1. UM Nurse Prior Authorization

**Task indicators**: prompt mentions "UM nurse", "prior authorization",
"determination summary", therapy CPT codes (97110, 97112, 97530), or
PT- prefixed criteria.

**Required output fields** (in addition to the universal basis_audit):

- `recommendation` — one of {approve, pend_for_information, escalate_to_md,
  deny, partial_approval}
- `final_status` — maps to the recommendation
- `route` — which team handles the next step
- `authorization` — auth_number, approved_units (integer), approved_start/end
  (dates), approved_cpt (ascending list), modifier
- `criteria_results` — PT-ACTIVE, PT-DEFICIT, PT-DX, PT-POC, PT-UNITS:
  {met, not_met, unclear, not_applicable}
- `evidence_documents` — current clinical doc IDs in ascending order
- `excluded_documents` — stale doc IDs in ascending order
- `determination_letter` — {approval, information_request,
  adverse_determination, partial_approval}
- `next_action` — {issue_approval, request_more_information, route_md_review,
  schedule_p2p, issue_denial, file_appeal, resubmit_corrected_claim,
  monitor_no_action}

**Record classification**: Current clinical documents (initial evaluation,
plan of care) are evidence. Anything marked stale or outdated by the
environment goes to excluded. The source-precedence rule is
`current_clinical_records_over_stale_export`.

**Criteria logic**: Each PT- criterion maps to a clinical requirement:
- PT-ACTIVE: member has an active therapy episode in the reporting period
- PT-DEFICIT: documented functional deficit justifying skilled therapy
- PT-DX: qualifying diagnosis code matches the plan coverage list
- PT-POC: current signed plan of care with measurable goals
- PT-UNITS: requested units are within the plan visit/frequency limit

When all five criteria are met, the recommendation is "approve" and the
route is "nurse_approval". The approved units come from the plan of care
frequency multiplied by the authorization period duration.

## 2. Pharmacy Appeal and Assistance Intake

**Task indicators**: prompt mentions "pharmacy appeals", "manufacturer
assistance", drug names (Vraylar, Dupixent, Humira, Ozempic, Rinvoq,
Skyrizi), or DRUG- prefixed criteria.

**Required output fields** (in addition to basis_audit):

- `appeal_id` — the Northstar appeal identifier
- `drug` — one of the six enumerated brand names
- `appeal_path` — {standard_internal, expedited_internal, external_review,
  not_eligible}
- `expedited` — boolean
- `appeal_deadline` — YYYY-MM-DD
- `owner` — {appeals-rx, um-nurse, medical-director, payment-integrity,
  member-services}
- `documented_failures` — lowercase medication names, alphabetical
- `undocumented_or_insufficient_failures` — lowercase medication names,
  alphabetical
- `criteria_results` — DRUG-AUTH, DRUG-DENIAL, DRUG-RATIONALE, DRUG-FAILURES:
  {met, not_met, partial, unclear, not_applicable}
- `required_packet_items` — operational packet order: payer appeal items
  before assistance items
- `missing_packet_items` — case-specific gap order: appeal evidence gaps
  before assistance information gaps
- `assistance` — program_name, status, missing_fields (alphabetical)
- `next_action` — {request_more_information, file_appeal,
  complete_expedited_appeal_and_request_income_proof,
  submit_assistance_application, issue_denial, close_not_eligible}

**Record classification**: The appeal record is the primary controlling
record. Drug trial records with clear failure evidence are controlling.
Trial records with insufficient documentation are exceptions. Missing
packet items like household_income_proof or lurasidone_fill_record are
also exceptions. The source-precedence rule is
`payer_appeal_before_manufacturer_assistance`.

**Drug failure classification**: A trial record shows a documented failure
when the environment data clearly indicates the medication was tried and
produced an inadequate response, intolerable side effect, or
contraindication. It is insufficient when a record exists but the outcome
is ambiguous, the dose/duration was subtherapeutic, or the documentation
lacks a clear conclusion.

**Assistance programs**: Each drug maps to its manufacturer program:
- Vraylar → Vraylar Connect
- Dupixent → Dupixent MyWay
- Humira → Humira Complete
- Others → not_applicable (unless a program is explicitly in the environment)

## 3. Payment Integrity / Claim Repricing

**Task indicators**: prompt mentions "payment integrity", "claim repricing",
"benchmark", "correction packet", or cardiac imaging CPT codes (78452,
A9500, 93016).

**Required output fields** (in addition to basis_audit):

- `claim_id` — the target claim identifier
- `auth_number` — the authorization number on the claim or payment record
- `benchmark_source` — {Northstar Commercial Imaging Schedule,
  Legacy Imaging Export, Northstar Distractor Schedule}
- `benchmark_version` — version string from the active schedule
- `stale_source_rejected` — which schedule was rejected as stale
- `paid_total` — sum of paid_amount across lines, rounded to cents
- `correct_allowed_total` — sum of correct_allowed_amount across lines
- `recovery_amount` — absolute difference between correct_allowed_total
  and paid_total
- `lines` — array of line objects in claim-line order:
  line_id, cpt_code, modifier (null if absent), units, paid_amount,
  correct_allowed_amount, recovery_amount, disposition
- `resubmission_route` — {payment_integrity_correction, provider_adjustment,
  appeal_reopen, no_resubmission}
- `priority` — {standard, expedited, urgent, monitor_only}

**Record classification**: The current benchmark schedule records (by
CPT code) control the repricing. The stale/legacy schedule is the
exception. The source-precedence rule is
`effective_benchmark_by_plan_modifier_and_date`.

**Line-level math**: For each line:
- `correct_allowed_amount` = benchmark rate for that CPT/modifier × units
- `recovery_amount` = |correct_allowed_amount − paid_amount|
- Sum line amounts for the claim totals

**Disposition**: When correct_allowed_amount > paid_amount →
`correct_upward`. When correct_allowed_amount < paid_amount →
`correct_downward`. When equal → `no_change`. When the line should be
denied outright → `deny_line`.

## 4. Peer-to-Peer Summary

**Task indicators**: prompt mentions "peer-to-peer", "P2P", "medical
director", PET MPI, CPT 78431, or PET- prefixed criteria.

**Required output fields** (in addition to basis_audit):

- `p2p_id` — the P2P event identifier
- `requested_cpt` — the CPT code from the auth line
- `p2p_outcome` — {not_applicable, overturn_to_approval,
  uphold_intended_adverse_decision}
- `final_status` — {approved, pended, md_review_required, denied,
  partially_approved, appeal_overturned, appeal_upheld}
- `criteria_results` — PET-IND, PET-FACTOR:
  {met, not_met, unclear, not_applicable}
- `unresolved_criteria` — criterion IDs that remain unresolved,
  ascending by ID
- `new_information_changed_review` — boolean
- `missing_pet_factors` — subset of {prior_equivocal_spect, bmi_limitation,
  attenuation_artifact} that remain unsupported
- `letter_type` — {approval, denial, partial_denial, no_letter}
- `recommended_alternative` — {SPECT MPI, PET MPI, none}
- `internal_appeal_deadline` — YYYY-MM-DD or null

**Record classification**: The P2P event record and the clinical cardiac
document are the controlling records. Unmet criteria IDs and unsupported
PET-over-SPECT factors are exceptions. The source-precedence rule is
`new_patient_specific_p2p_information`.

**PET MPI criteria**:
- PET-IND: the clinical indication for PET MPI is documented (e.g.,
  known CAD with prior equivocal test)
- PET-FACTOR: at least one PET-over-SPECT factor is supported (equivocal
  prior SPECT, BMI limitation, attenuation artifact)

When PET-IND is met but PET-FACTOR is not met (no PET-over-SPECT factor
supported), and the P2P did not supply new information that changed the
review, the outcome is "uphold_intended_adverse_decision" with
recommended_alternative "SPECT MPI".

**Internal appeal deadline**: When the final determination is adverse and
the plan specifies a 180-day window, calculate as determination_date +
180 calendar days. The determination date is typically the reporting date
or the date the final status is set.

## 5. Therapy Margin Queue

**Task indicators**: prompt mentions "margin queue", "UM-finance",
"therapy margin", "revenue-to-cost", or SM- prefixed queue row IDs.

**Required output fields** (in addition to basis_audit):

- `period` — YYYY-MM
- `threshold_revenue_to_cost_ratio` — number (typically 1.2)
- `rows` — array in the order of queue_row_ids from task_context:
  month_id, payer_segment, service_domain, cpt_code, total_cost, margin,
  revenue_to_cost_ratio, below_threshold, charge_sensitive,
  recommended_action
- `below_threshold_segments` — payer segments with below-threshold rows,
  alphabetical
- `charge_sensitive_segments` — payer segments with charge-sensitive
  rows, alphabetical
- `top_issue` — {medicaid_97110, commercial_97530, workers_comp_97112,
  none}
- `gap_to_120pct` — dollar gap for the top below-threshold issue

**Record classification**: The queue rows (SM-*) are the controlling
records. Below-threshold rows are also exceptions since they drive the
action. The source-precedence rule is
`margin_threshold_then_charge_sensitivity`.

**Math definitions** (from the task_context finance_memo):
- `total_cost` = variable_cost + fixed_cost_allocated
- `margin` = revenue − total_cost
- `revenue_to_cost_ratio` = revenue / total_cost (4 decimal places)
- `below_threshold` = ratio < threshold_revenue_to_cost_ratio
- `charge_sensitive` = flag from the source data
- `gap_to_120pct` = (threshold × total_cost) − revenue, for the
  below-threshold row with the lowest ratio

**Recommended actions**:
- below_threshold → `payer_contract_review` (payer reimbursement is below
  cost coverage target)
- charge_sensitive (not below threshold) → `monitor_charge_sensitive`
  (margins are healthy but sensitive to charge fluctuations)
- neither → `monitor_no_action`

**Top issue naming**: Combine payer_segment + cpt_code with underscore,
e.g., "medicaid_97110". Only below-threshold rows qualify. When there is
exactly one below-threshold row, it is the top issue. When there are
multiple, the one with the lowest revenue_to_cost_ratio is the top issue.
When there are none, use "none".

## Universal basis_audit reminder

Every task template includes the basis_audit with these four keys:

- `source_precedence`: one of the six rules, selected by domain
- `precedence_record_order`: controlling records first, then exceptions,
  highest priority at index 0
- `controlling_record_ids`: records that directly control the result
- `exception_record_ids`: gaps, stale records, missing criteria,
  ordered with criteria/route gaps before stale records

Non-record gaps (criterion IDs, missing packet item names like
"household_income_proof") belong in exception_record_ids when they are
the reason for a pending, denial, or information request. This is not
an error — it is the expected pattern when a required element is absent
from the environment.
