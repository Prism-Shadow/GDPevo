# Workflow Patterns by Task Type

## UM Nurse Determination (Physical Therapy)

**Role:** UM nurse reviewer
**Domain:** physical_therapy
**Criteria:** PT-ACTIVE, PT-DEFICIT, PT-DX, PT-POC, PT-UNITS
**Key decision:** Whether all PT criteria are met based on current clinical documents.

Workflow:
1. Query the case record for case details and associated document IDs.
2. Query the active member and plan context from the case.
3. Retrieve the applicable PT policy and its criteria.
4. Retrieve all documents attached to the case. Classify each as current clinical evidence or stale/excluded.
5. Evaluate each PT criterion against the evidence documents.
6. If all criteria are met: recommend approve, route nurse_approval. Determine authorization details (auth number, approved units, date range, CPTs, modifier).
7. Include current clinical documents in evidence_documents; stale or unrelated documents in excluded_documents.
8. Source precedence: `current_clinical_records_over_stale_export`.

## Pharmacy Coverage Appeal Disposition

**Role:** pharmacy appeals coordinator
**Domain:** pharmacy (Vraylar, Dupixent, Humira, Ozempic, Rinvoq, Skyrizi)
**Criteria:** DRUG-AUTH, DRUG-DENIAL, DRUG-RATIONALE, DRUG-FAILURES

Workflow:
1. Query the appeal record for appeal routing, deadlines, expedited flag.
2. Query the case for associated drug trial records and document evidence.
3. Query the applicable pharmacy policy for criteria.
4. Classify drug trials as documented failures (successful documentation of trial and failure) vs. undocumented/insufficient failures (missing records or insufficient documentation).
5. Determine required packet items (denial notice, member authorization, prescriber rationale, formulary failure evidence, and assistance-specific items like household income proof).
6. Identify missing packet items.
7. Screen manufacturer assistance: program name, eligibility status, missing fields.
8. Determine next action based on completeness: request_more_information if gaps exist; file_appeal or submit_assistance_application if ready.
9. Source precedence: `payer_appeal_before_manufacturer_assistance`.

## Payment Integrity Claim Repricing

**Role:** payment integrity analyst
**Domain:** cardiac_imaging or other service domains
**Key concepts:** benchmark source, benchmark version, stale source rejection, line-level corrections.

Workflow:
1. Query the claim and its claim lines (in claim-line order).
2. Query the associated case and authorization record.
3. Query rate schedules/benchmarks for each line's CPT code and modifier.
4. Identify the effective benchmark (current schedule by plan modifier and effective date) and reject stale sources.
5. For each line, compute correct allowed amount from the benchmark * units. Calculate recovery = correct_allowed - paid (positive = correct_upward, negative = correct_downward, zero = no_change).
6. Sum line totals for paid_total, correct_allowed_total, recovery_amount.
7. Determine resubmission_route and priority.
8. Source precedence: `effective_benchmark_by_plan_modifier_and_date`.

## Peer-to-Peer Summary

**Role:** peer-to-peer coordinator
**Domain:** cardiac_imaging (PET MPI)
**Criteria:** PET-IND, PET-FACTOR

Workflow:
1. Query the case for the requested CPT and attached documents.
2. Query the applicable PET MPI policy for criteria.
3. Query the P2P event for outcome, new information flag, and discussion details.
4. Evaluate PET-IND and PET-FACTOR criteria against evidence.
5. If P2P upholds intended adverse decision: final_status denied, letter_type denial.
6. Identify unresolved criteria and missing PET factors (prior_equivocal_spect, bmi_limitation, attenuation_artifact).
7. Calculate internal appeal deadline: 180 calendar days from the adverse determination date.
8. Recommend alternative modality based on what the policy supports (typically SPECT MPI when PET is denied).
9. Source precedence: `new_patient_specific_p2p_information`.

## Therapy Margin Queue Analysis

**Role:** UM-finance operations analyst
**Domain:** physical_therapy, speech_therapy, occupational_therapy
**Key concepts:** revenue_to_cost_ratio threshold, below-threshold classification, charge sensitivity.

Workflow:
1. Query service_margin records for the listed queue row IDs.
2. Compute total_cost = variable_cost + fixed_cost_allocated for each row.
3. Compute revenue_to_cost_ratio = (total_cost + margin) / total_cost, or equivalently 1 + margin/total_cost.
4. Classify below_threshold: true when ratio < threshold_revenue_to_cost_ratio.
5. Separate below-threshold segments from charge-sensitive segments (rows not below threshold but flagged charge_sensitive).
6. Identify the top issue as the below-threshold row with the largest margin shortfall.
7. Compute gap_to_120pct as the dollar amount needed to bring the top issue's revenue to 120% of its total cost: (total_cost * 1.2) - actual_revenue.
8. Source precedence: `margin_threshold_then_charge_sensitivity`.
