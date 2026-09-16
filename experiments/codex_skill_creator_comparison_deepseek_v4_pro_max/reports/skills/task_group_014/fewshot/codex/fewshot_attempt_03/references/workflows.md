# Northstar Payer Operations - Detailed Workflows

Step-by-step procedures, extra SQL patterns, computation rules, and field-mapping notes for each business operation.

## 1. UM Prior Authorization Determination

**Role:** UM nurse reviewer
**Target tables:** cases, members, plans, request_lines, documents, document_facts, case_criteria, policy_criteria, authorizations

### Extra Queries

```sql
SELECT * FROM members WHERE member_id = (SELECT member_id FROM cases WHERE case_id = '{target}')
SELECT * FROM plans WHERE plan_id = (SELECT plan_id FROM members WHERE member_id = '{mbr_id}')
SELECT * FROM request_lines WHERE case_id = '{target}'
SELECT * FROM documents WHERE case_id = '{target}'
SELECT * FROM document_facts WHERE case_id = '{target}'
SELECT * FROM case_criteria WHERE case_id = '{target}'
SELECT * FROM policy_criteria WHERE policy_id = (SELECT policy_id FROM cases WHERE case_id = '{target}')
SELECT * FROM authorizations WHERE case_id = '{target}'
```

### Criteria Mapping

For PT policies: PT-ACTIVE (member active coverage), PT-DEFICIT (functional deficit), PT-DX (diagnosis), PT-POC (plan of care), PT-UNITS (unit limit).

### Authorization Fields

- `auth_number` from the authorization record.
- `approved_units` from request_lines.requested_units when criteria met.
- `approved_start` / `approved_end` from request lines; when reporting_date is after requested_start, use reporting_date + 1 day as start.
- `approved_cpt`: ascending list from request_lines cpt_code values.
- `modifier` from request_lines.

### Evidence Classification

- **evidence_documents**: document_ids with is_current = 1 that support criteria. Ascending.
- **excluded_documents**: document_ids with is_current = 0 (stale). Ascending.

### Determination Logic

- All criteria met -> recommendation: approve, final_status: approved, route: nurse_approval.
- Any not_met with result_if_missing = deny -> deny, route: medical_director_review.
- Any not_met/unclear with result_if_missing = pend -> pend_for_information.

### basis_audit.source_precedence

Use `current_clinical_records_over_stale_export` when stale documents exist alongside current ones. If no stale records, the rule still applies.

---

## 2. Pharmacy Appeals Intake with Manufacturer Assistance

**Role:** Pharmacy appeals coordinator
**Target tables:** cases, members, appeals, drug_trials, assistance_screen, documents, policy_criteria

### Extra Queries

```sql
SELECT * FROM appeals WHERE case_id = '{target}'
SELECT * FROM drug_trials WHERE case_id = '{target}'
SELECT * FROM assistance_screen WHERE case_id = '{target}'
```

### Trial Classification

- documented = 1 -> documented_failures (alphabetical by medication name)
- documented = 0 -> undocumented_or_insufficient_failures (alphabetical by medication name)

### Packet Items

- required_packet_items: Operationally required items. Order: payer appeal items first, then assistance items.
- missing_packet_items: Items absent from the packet. Order: appeal evidence gaps before assistance information gaps.

### Assistance Screen

- program_name from assistance_screen.program_name.
- status from assistance_screen.assistance_status (eligible_ready, eligible_missing_information, not_eligible, not_applicable).
- missing_fields: parse assistance_screen.missing_fields (comma-separated). Alphabetical order.

### Criteria Results

- DRUG-AUTH (member authorization), DRUG-DENIAL (denial notice), DRUG-RATIONALE (prescriber rationale), DRUG-FAILURES (formulary failures).
- DRUG-FAILURES is partial when some trials are documented and some are not.

### basis_audit.source_precedence

Use `payer_appeal_before_manufacturer_assistance` - appeal evidence controls before assistance program data.

---

## 3. Payment Integrity Claim Repricing

**Role:** Payment integrity analyst
**Target tables:** claims, claim_lines, members, payment_benchmarks, cases

### Extra Queries

```sql
SELECT * FROM claims WHERE claim_id = '{target}'
SELECT * FROM claim_lines WHERE claim_id = '{target}' ORDER BY line_number
SELECT * FROM members WHERE member_id = (SELECT member_id FROM claims WHERE claim_id = '{target}')
SELECT * FROM payment_benchmarks WHERE plan_type = '{plan_type}' AND cpt_code IN ({cpt_list}) ORDER BY effective_start DESC
```

### Benchmark Selection

1. Get member plan_type.
2. Query payment_benchmarks for that plan_type and the claim line CPT codes.
3. Use benchmarks with effective_start <= service_date <= effective_end (current benchmarks).
4. Match on both CPT and modifier; prefer exact modifier match. Use null-modifier benchmarks when no modifier-specific benchmark exists.
5. Reject benchmarks from stale source_names (e.g., Legacy Imaging Export with outdated effective_end).

### Line Correction Math

- correct_allowed_amount = benchmark.allowed_amount x claim_line.units
- recovery_amount = correct_allowed_amount - claim_line.paid_amount (positive = underpayment, negative = overpayment)
- correct_allowed_total = sum of all line correct_allowed_amount
- recovery_amount (top-level) = correct_allowed_total - paid_total
- Currency: round to two decimal places.

### Disposition

- recovery > 0 -> correct_upward
- recovery < 0 -> correct_downward
- recovery = 0 -> no_change

### basis_audit.source_precedence

Use `effective_benchmark_by_plan_modifier_and_date` - benchmark selection by current effective dates, rejecting stale schedules.

---

## 4. Peer-to-Peer Final Determination

**Role:** Peer-to-peer coordinator
**Target tables:** cases, members, p2p_events, documents, case_criteria, policy_criteria, request_lines, authorizations

### Extra Queries

```sql
SELECT * FROM p2p_events WHERE case_id = '{target}'
SELECT * FROM documents WHERE case_id = '{target}'
SELECT * FROM case_criteria WHERE case_id = '{target}'
SELECT * FROM policy_criteria WHERE policy_id = (SELECT policy_id FROM cases WHERE case_id = '{target}')
```

### P2P Outcome Determination

- p2p_outcome from p2p_events.outcome: overturn_to_approval, uphold_intended_adverse_decision.
- final_status: overturn -> approved; uphold -> denied.
- new_information_changed_review: true when new_information column is non-null and substantive.
- p2p_id from p2p_events.p2p_id. requested_cpt from request_lines.cpt_code.

### PET-Specific Criteria

- PET-IND: covered cardiac indication. PET-FACTOR: at least one PET-over-SPECT factor (prior equivocal SPECT, BMI limitation, attenuation artifact).
- unresolved_criteria: list of criterion IDs where result is not_met or unclear after P2P. Ascending order.
- missing_pet_factors: unsupported PET-over-SPECT factors. Order: prior_equivocal_spect, bmi_limitation, attenuation_artifact.
- recommended_alternative: SPECT MPI when PET denied; none when approved.
- letter_type: approval when approved; denial when denied.

### Internal Appeal Deadline

- When final_status is denied: deadline = final adverse determination date + 180 days.
- When approved: null.
- Use the P2P event scheduled_at date (or reporting_date if unavailable) as the final adverse determination date.

### basis_audit.source_precedence

Use `new_patient_specific_p2p_information` - P2P discussion outcome controls, with clinical records as supporting evidence.

---

## 5. Therapy Margin Queue Analysis

**Role:** UM-finance operations analyst
**Target tables:** service_margin

### Extra Queries

```sql
SELECT * FROM service_margin WHERE month_id IN ({row_id_list})
```

### Row Computation

For each queue row:
- total_cost = variable_cost + fixed_cost_allocated
- margin = net_revenue - total_cost
- revenue_to_cost_ratio = net_revenue / total_cost (4 decimal places)
- below_threshold = true when revenue_to_cost_ratio < threshold_revenue_to_cost_ratio
- charge_sensitive = true when charge_sensitive column = 1

### Segment Classification

- below_threshold_segments: payer_segments with below_threshold = true. Alphabetical by enum value.
- charge_sensitive_segments: payer_segments with charge_sensitive = true. Alphabetical by enum value.

### Top Issue and Gap

- top_issue: the below-threshold segment-CPT combination with the lowest revenue_to_cost_ratio. Format: {segment}_{cpt} (e.g., medicaid_97110).
- gap_to_120pct: (threshold x total_cost) - net_revenue for the top-issue row. Round to 2 decimal places.

### Recommended Actions

- below_threshold -> payer_contract_review
- charge_sensitive (not below_threshold) -> monitor_charge_sensitive
- neither -> monitor_no_action

### basis_audit.source_precedence

Use `margin_threshold_then_charge_sensitivity` - below-threshold rows control the result; charge-sensitive rows are secondary.
