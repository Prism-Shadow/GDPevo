# Basis Audit Construction Guide

Every Northstar payer-operations determination must include a basis_audit object.
This reference explains how to select the correct precedence rule and populate
each of the four required arrays.

## Required Keys

- **source_precedence** (string enum) — The business rule governing how conflicting records are prioritized.
- **controlling_record_ids** (list of strings) — Environment record IDs that directly determine the outcome.
- **exception_record_ids** (list of strings) — IDs explaining gaps, exclusions, denials, missing information, or route priority.
- **precedence_record_order** (list of strings) — All controlling and exception records combined, ordered by source precedence priority.

## The Six Precedence Rules

### 1. current_clinical_records_over_stale_export

**When to use:** Prior authorization or clinical determination where both current and stale document versions exist in the environment.

**Priority ordering:**
1. Current clinical documents (is_current = 1, sourced from provider_portal, fax, or emr) — highest priority.
2. Stale or export-batch documents (is_current = 0, sourced from export_batch) — excluded, lowest priority.

**Record ID conventions:**
- controlling_record_ids: Current document IDs and related clinical record IDs that support the criteria results.
- exception_record_ids: Stale document IDs, listed after any criterion-gap identifiers.
- precedence_record_order: Current documents first (ascending document_id), then stale documents (ascending document_id). If criterion gaps exist, list them after current documents but before stale documents.

### 2. payer_appeal_before_manufacturer_assistance

**When to use:** Pharmacy coverage appeal where both payer-side appeal processing and manufacturer assistance screening occur.

**Priority ordering:**
1. Payer appeal record (the appeal_id and related trial evidence) — highest priority, primary coverage path.
2. Manufacturer assistance screen record — secondary, evaluated after appeal processing.
3. Missing information identifiers (field names, criterion gaps) — lowest priority.

**Record ID conventions:**
- controlling_record_ids: The appeal ID and documented trial IDs that support the criteria results.
- exception_record_ids: Undocumented trial IDs, missing field names, or assistance gaps. List payer-side gaps before assistance-side gaps.
- precedence_record_order: Appeal records first, then trial evidence (documented before undocumented), then assistance records, then gap identifiers.

### 3. effective_benchmark_by_plan_modifier_and_date

**When to use:** Claim repricing against rate schedules.

**Priority ordering:**
1. Current benchmark records whose effective window (effective_start to effective_end) covers the service date — highest priority, grouped by plan_type and modifier match.
2. Stale or expired benchmark records — excluded.

**Record ID conventions:**
- controlling_record_ids: The claim line IDs (in line_number order) and the matching current benchmark IDs. List claim lines first, then benchmarks.
- exception_record_ids: Stale benchmark IDs.
- precedence_record_order: Current benchmarks first (sorted by benchmark_id ascending), then stale benchmarks (sorted ascending). Claim line IDs are typically included in controlling_record_ids but not repeated in precedence_record_order unless they are the sole controlling records.

### 4. new_patient_specific_p2p_information

**When to use:** Peer-to-peer determination where P2P discussion introduces new clinical information.

**Priority ordering:**
1. P2P event record — highest priority, as new patient-specific information from the discussion takes precedence.
2. Pre-P2P clinical documents — secondary, supporting context.
3. Unresolved criterion IDs — lowest priority, representing gaps not resolved by the P2P.

**Record ID conventions:**
- controlling_record_ids: The P2P event ID and the clinical document IDs that support the criteria results.
- exception_record_ids: Unresolved criterion IDs and unsupported factor identifiers. List criterion gaps first, then factor identifiers.
- precedence_record_order: P2P event ID first, then current clinical documents (ascending), then unresolved criterion IDs, then factor identifiers.

### 5. margin_threshold_then_charge_sensitivity

**When to use:** Therapy margin queue analysis.

**Priority ordering:**
1. Below-threshold rows (margin row IDs where revenue_to_cost_ratio < threshold) — highest priority, these drive the primary findings.
2. Charge-sensitive but above-threshold rows — secondary observations.
3. Above-threshold and non-charge-sensitive rows — lowest priority for action but still part of the complete picture.

**Record ID conventions:**
- controlling_record_ids: All queue row month IDs in the order they appear in the task context queue_row_ids list.
- exception_record_ids: Below-threshold row IDs (duplicated from controlling since they are both controlling and exceptional).
- precedence_record_order: Below-threshold rows first (by month_id ascending), then charge-sensitive above-threshold rows, then remaining rows.

### 6. appeal_deadline_then_clinical_then_payment_integrity

**When to use:** Appeal scenarios where deadline compliance, clinical evidence, and payment review all interact.

**Priority ordering:**
1. Appeal deadline record — first gate, deadline compliance determines whether the appeal proceeds.
2. Clinical evidence records — second gate, clinical documentation supports or refutes the appeal.
3. Payment integrity findings — third level, payment corrections follow clinical determination.

**Record ID conventions:**
- controlling_record_ids: Records that gate or determine the outcome at each level.
- exception_record_ids: Records that explain why certain levels were not reached or why the determination is adverse.
- precedence_record_order: Deadline records first, then clinical records, then payment records, then gap identifiers.

## Building the Arrays

### controlling_record_ids

These are environment record IDs (from database primary keys) whose data values directly produce the determination result. They answer: "Which records, if changed, would change the outcome?"

Valid source tables:
- documents (document_id)
- document_facts (fact_id) — use sparingly, prefer document_id
- case_criteria (criterion_id) — when the criterion result itself is the controlling factor
- drug_trials (trial_id)
- appeals (appeal_id)
- p2p_events (p2p_id)
- payment_benchmarks (benchmark_id)
- claim_lines (claim_line_id)
- service_margin (month_id)
- authorizations (auth_id)
- cases (case_id)

Ordering: Use the operational evidence order appropriate for the domain. For clinical domains, order by document date or document_id ascending. For payment domains, order by claim line number or benchmark_id ascending. For queue domains, follow the task context ordering.

### exception_record_ids

These explain gaps, exclusions, denials, or missing information. Include both record IDs and non-record identifiers:

- **Stale/excluded document IDs** — documents rejected because is_current = 0 or from wrong source.
- **Gap criterion IDs** — e.g., "PET-FACTOR" when a criterion is not_met or unclear.
- **Missing field identifiers** — field names like "household_income_proof" when a required packet item is absent.
- **Unresolved factor identifiers** — e.g., "prior_equivocal_spect", "bmi_limitation", "attenuation_artifact" when PET-over-SPECT factors remain unsupported.

Ordering: Criteria or route gaps before stale or excluded records. When both appear, list gaps first, then stale records second.

### precedence_record_order

The combined list of all controlling and exception records in source-precedence order. This is the full audit trail.

Rules:
- Highest priority records first (per the selected precedence rule).
- When two records share the same priority level, list controlling records before exception records.
- Within each group, use ascending ID order as the tiebreaker.
- Do not duplicate records that appear in both controlling and exception arrays (list once at their highest-priority position).

## Verification Checklist

Before finalizing the basis_audit:

1. Does source_precedence match the domain? Check the SKILL.md domain-to-rule table.
2. Are all controlling_record_ids real database keys from the environment queries?
3. Do exception_record_ids include both record IDs and gap identifiers where appropriate?
4. Does precedence_record_order contain every ID from both arrays without duplicates?
5. Are the ordering conventions followed for the selected precedence rule?
6. Are missing fields (like household_income_proof) represented as string identifiers in exception_record_ids?
