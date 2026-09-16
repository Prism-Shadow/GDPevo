# Northstar Business Rules

Domain rules, classification logic, and operational patterns for payer workflows.

## Payer Segments

| Segment | plan_type value | Typical Plans |
|---------|----------------|---------------|
| Commercial | commercial | Employer-sponsored, individual |
| Medicaid | medicaid | State Medicaid managed care |
| Medicare | medicare | Medicare Advantage |
| Workers' Comp | workers_comp | Occupational injury |

## Policy Criteria Patterns

### Physical Therapy (PT)

Policy criteria keys and their meaning:

| Key | What it Checks | Typical Evidence Source |
|-----|---------------|------------------------|
| PT-ACTIVE | Member is actively participating in therapy | Evaluation notes, attendance records |
| PT-DEFICIT | Documented functional deficit | Evaluation (eval) document |
| PT-DX | Qualifying diagnosis | Diagnosis codes in request_lines or document_facts |
| PT-POC | Plan of care with measurable goals | POC document |
| PT-UNITS | Requested units are within medical necessity limits | POC frequency x duration |

### Pharmacy (DRUG)

| Key | What it Checks |
|-----|---------------|
| DRUG-AUTH | Prior authorization record exists |
| DRUG-DENIAL | A formal denial has been issued |
| DRUG-RATIONALE | Prescriber has provided clinical rationale |
| DRUG-FAILURES | Required number of formulary alternatives have been tried and failed |

### Cardiac Imaging (PET MPI)

| Key | What it Checks |
|-----|---------------|
| PET-IND | Clinical indication for PET MPI is documented |
| PET-FACTOR | PET-over-SPECT factors (equivocal prior SPECT, BMI limitation, attenuation artifact) are supported |

Criteria results: `met`, `not_met`, `unclear`, `not_applicable`.

## Document Classification

### is_current Flag

- `is_current = 1`: Current, valid clinical evidence to be used in determination.
- `is_current = 0`: Stale, superseded, or legacy export. Exclude from evidence but note in exclusion list.

### Document Types

| Type | Description |
|------|-------------|
| eval | Initial or re-evaluation |
| poc | Plan of care |
| cardiology_report | Cardiology consult or imaging report |
| pharmacy_claim | Pharmacy fill/claim record |
| appeal_letter | Member or provider appeal letter |
| denial_notice | Issued denial letter |
| income_proof | Household income documentation |

## Appeal Rules

### Appeal Path

- `standard_internal`: Standard 30-day internal appeal timeline.
- `expedited_internal`: Expedited review for urgent medical need.
- `external_review`: Independent external review after internal appeal exhausted.
- `not_eligible`: No valid appeal path.

### Appeal Deadline Calculation

- Standard internal: 30 calendar days from denial_date.
- External review: Per state/plan rules, typically 60 days from internal appeal outcome.
- Internal appeal (adverse determination): 180 calendar days from final adverse determination date (P2P or MD review date).

### Packet Item Ordering

Appeal packet items follow this operational order:
1. Payer appeal items first: denial_notice, member_authorization, prescriber_rationale, formulary_failure_evidence
2. Manufacturer assistance items second: household_income_proof, pharmacy_claim_history, diagnosis_confirmation, expedited_risk_attestation

Missing items follow case-specific gap order: appeal evidence gaps before assistance information gaps.

## Drug Trial Classification

| documented Flag | Classification | Where it Goes |
|----------------|---------------|---------------|
| 1 | Documented failure | documented_failures list |
| 0 | Undocumented or insufficient | undocumented_or_insufficient_failures list |

List medications in lowercase, alphabetical order within each group.

## Manufacturer Assistance Programs

| Program | Drug | Requirements |
|---------|------|-------------|
| Vraylar Connect | Vraylar (cariprazine) | Commercial insurance, pending/proof of denial, income verification |
| Dupixent MyWay | Dupixent (dupilumab) | Commercial insurance, denial notice, prescriber enrollment |
| Humira Complete | Humira (adalimumab) | Commercial insurance, denial notice |

### Assistance Status

- `eligible_ready`: All fields complete, application can be submitted.
- `eligible_missing_information`: Eligible but missing required fields; request missing items.
- `not_eligible`: Does not meet program criteria (e.g., medicaid enrollee).
- `not_applicable`: No applicable assistance program for this drug.

### Missing Fields Ordering

Alphabetical by field identifier: denial_notice, household_income_proof, insurance_card, member_signature, prescriber_signature.

## Claim Repricing Rules

### Benchmark Selection

1. Query `payment_benchmarks` for the claim's payer and plan_type.
2. Filter by service_domain (usually from the claim's associated case).
3. For each CPT code on the claim, find the benchmark whose `effective_start` <= claim service date <= `effective_end`.
4. If multiple benchmarks exist for the same CPT, the most recent `effective_start` wins.
5. Explicitly identify the stale source(s) in `stale_source_rejected`. Use `none` if no stale source exists.

### Line Calculations

- `correct_allowed_amount` = benchmark `allowed_amount` × `units`
- `recovery_amount` (per line) = `correct_allowed_amount` − `paid_amount`
- Positive recovery = underpayment, disposition `correct_upward`
- Negative recovery = overpayment, disposition `correct_downward`
- Zero recovery = no change, disposition `no_change`

### Claim-Level Calculations

- `paid_total` = sum of all line `paid_amount`
- `correct_allowed_total` = sum of all line `correct_allowed_amount`
- `recovery_amount` (claim) = `correct_allowed_total` − `paid_total`
- If recovery is negative (overpayment), the recovery_amount value can be negative.

### Modifier Handling

- Use exact modifier from claim_line, always a string (e.g., "TC", "26").
- Use JSON `null` when modifier is absent or NULL — never an empty string.

## Margin Queue Rules

### Cost and Margin Formulas

- `total_cost` = `variable_cost` + `fixed_cost_allocated`
- `margin` = `net_revenue` − `total_cost`
- `revenue_to_cost_ratio` = `net_revenue` / `total_cost` (round to 4 decimal places)

### Threshold Classification

- `below_threshold`: true when `revenue_to_cost_ratio` < `threshold_revenue_to_cost_ratio` (typically 1.2)
- `charge_sensitive`: true when the row's `charge_sensitive` column = 1

### Action Recommendation

| Condition | Action |
|-----------|--------|
| below_threshold = true AND charge_sensitive = false | payer_contract_review |
| below_threshold = true AND charge_sensitive = true | payer_contract_review |
| below_threshold = false AND charge_sensitive = true | monitor_charge_sensitive |
| below_threshold = false AND charge_sensitive = false | monitor_no_action |

### Gap Calculation

`gap_to_120pct` = (`threshold_revenue_to_cost_ratio` × `total_cost`) − `net_revenue`

This is the dollar amount by which revenue falls short of 120% of total cost for the most impactful below-threshold row.

### Top Issue

The `top_issue` is `{payer_segment}_{cpt_code}` of the below-threshold row with the largest `gap_to_120pct`. If no rows are below threshold, use `none`.

## Basis Audit Construction

### Step-by-Step

1. **Choose source_precedence**: Match the evidence hierarchy to the task domain (see options below).
2. **Identify controlling records**: Every environment record ID that directly supports the determination result. Include case criteria records, current documents, approved authorizations, selected benchmarks, P2P events, etc.
3. **Identify exception records**: Stale documents, unresolved criteria IDs, missing packet items, rejected benchmarks, below-threshold rows, etc.
4. **Build precedence_record_order**: Concatenate controlling and exception records in priority order. For most workflows, controlling records come first, followed by exception/gap records.

### Source Precedence Rules (Full Definitions)

| Rule | Domain | Controlling Priority | Exception Priority |
|------|--------|---------------------|-------------------|
| current_clinical_records_over_stale_export | UM nurse review | Current clinical documents → current criteria results → authorization | Stale documents → excluded records |
| payer_appeal_before_manufacturer_assistance | Pharmacy appeal | Appeal record → documented drug trials → criteria results | Undocumented trials → missing packet items → assistance gaps |
| effective_benchmark_by_plan_modifier_and_date | Payment integrity | Effective benchmarks (by CPT, most recent first) → claim lines | Stale/outdated benchmarks |
| new_patient_specific_p2p_information | Peer-to-peer | P2P event → supporting clinical document → met criteria | Unmet/unresolved criteria → missing PET factors |
| margin_threshold_then_charge_sensitivity | Margin queue | Below-threshold rows first → above-threshold charge-sensitive rows → remaining rows | The below-threshold row(s) that drive the top_issue |
| appeal_deadline_then_clinical_then_payment_integrity | Mixed workflows | Appeal records → deadline-driven items → clinical evidence → payment records | Gaps in any tier |

## Determination Status Mapping

### UM Nurse

| Criteria Result | Recommendation | Final Status | Route | Letter |
|----------------|---------------|-------------|-------|--------|
| All met | approve | approved | nurse_approval | approval |
| Some unclear | pend_for_information | pended | pending_information | information_request |
| Some not_met, simple issue | escalate_to_md | md_review_required | medical_director_review | — |
| All or critical not_met | deny | denied | medical_director_review | adverse_determination |
| Some met, some not | partial_approval | partially_approved | nurse_approval | partial_approval |

### Peer-to-Peer

| P2P Outcome | Final Status | Letter | Recommended Alternative |
|-------------|-------------|-------|------------------------|
| overturn_to_approval | approved | approval | none |
| uphold_intended_adverse_decision | denied | denial | SPECT MPI (when PET denied) |
