# Source Precedence Rules and Basis Audit

Every Northstar task resolves conflicting or overlapping records through a `source_precedence` rule. The rule determines which records control the result and which are treated as exceptions or gaps.

## Precedence Rules

### current_clinical_records_over_stale_export

Used for UM nurse prior-authorization determinations.

- Current clinical documents (`is_current = 1`) control the determination.
- Stale documents (`is_current = 0`) are excluded from evidence and recorded as exceptions.
- When a document fact from a current document supports a criterion, that criterion result stands.
- Stale export records must never override current clinical findings.

**Controlling records**: Current documents, request lines, and case_criteria results tied to current evidence.

**Exception records**: Documents with `is_current = 0`.

**Order**: Current documents first (ordered by document_date ascending), then stale documents last.

### payer_appeal_before_manufacturer_assistance

Used for pharmacy coverage-exception appeals.

- Appeal records (from `appeals` table) and clinical drug-trial evidence control the determination first.
- Manufacturer assistance screens (from `assistance_screen`) are evaluated second.
- Payer-side packet gaps (missing appeal evidence) take precedence over manufacturer assistance gaps (missing income proof, etc.) in determining next action.

**Controlling records**: The appeal record itself, plus documented drug trials.

**Exception records**: Undocumented drug trials, missing packet items, and assistance-screen gaps.

**Order**: Appeal record first, then documented trials, then undocumented trials, then missing packet items (appeal gaps before assistance gaps).

### effective_benchmark_by_plan_modifier_and_date

Used for payment integrity claim repricing.

- The benchmark with the most recent effective date that matches the claim's payer, plan_type, service_domain, cpt_code, and modifier controls the allowed amount.
- Stale benchmarks (with effective_end before the claim's service date) must be rejected.
- Benchmark selection is per claim line: each line matches independently on cpt_code and modifier.

**Controlling records**: The claim lines and the winning benchmark rows.

**Exception records**: Stale benchmarks that were considered and rejected.

**Order**: Winning benchmarks first (ordered by cpt_code ascending), then rejected stale benchmarks last.

### new_patient_specific_p2p_information

Used for peer-to-peer review summaries.

- The P2P event record (`p2p_events`) is the highest-priority source because it captures the live discussion outcome.
- Clinical documents and policy criteria are evaluated second, after incorporating any new information from the P2P.
- When the P2P supplies no new patient-specific information, the pre-P2P clinical records and criteria results stand unchanged.

**Controlling records**: P2P event and the clinical documents that support the criteria results.

**Exception records**: Unresolved criteria (criteria that remain not_met or unclear after P2P), plus any missing PET-over-SPECT factors.

**Order**: P2P event first, then controlling clinical documents, then unresolved criteria IDs.

### margin_threshold_then_charge_sensitivity

Used for UM-finance therapy margin queue analysis.

- Rows are first evaluated against the revenue-to-cost ratio threshold.
- Rows below threshold are flagged and recommended for payer contract review.
- Rows above threshold are then checked for charge sensitivity; charge-sensitive rows are flagged for monitoring.
- Rows above threshold and not charge-sensitive require no action.

**Controlling records**: All queue row IDs listed in the task context.

**Exception records**: Rows that are below threshold (these are both controlling and exceptions, as they represent margin problems).

**Order**: Queue rows in the order specified by the task context's `queue_row_ids`.

## Basis Audit Construction

Every answer must include a `basis_audit` object with four required keys:

### source_precedence

One of the six enum values listed above. Choose the one that matches the task domain.

### controlling_record_ids

A list of environment record IDs that directly control the result. These are:
- Document IDs of evidence documents relied upon
- Claim line IDs
- Benchmark IDs
- Appeal IDs
- P2P event IDs
- Service margin month IDs
- Criteria IDs when no matching record ID exists

**Ordering rule**: Use the operational evidence order for the records that directly control the result.

### exception_record_ids

A list of record IDs that explain exclusions, denials, missing information, or route priority. These are:
- Stale document IDs excluded from evidence
- Undocumented drug trial IDs
- Missing packet item names (as strings)
- Criterion IDs for criteria that are not_met, unclear, or unresolved
- Stale benchmark IDs that were rejected
- Month IDs for below-threshold rows when they are the exception

**Ordering rule**: Use business gap/exception order — criteria or route gaps before stale or excluded records when both appear.

### precedence_record_order

A single ordered list combining controlling and exception records in source-precedence order, highest priority first.

**Ordering rule**: List the controlling and exception records in source-precedence order, highest priority first.

## Common Patterns from Train Answers

For `current_clinical_records_over_stale_export`:
- controlling: current document IDs in ascending document_id order
- exception: stale document IDs
- precedence_order: current docs then stale docs

For `payer_appeal_before_manufacturer_assistance`:
- controlling: appeal ID, documented trial IDs
- exception: undocumented trial IDs, missing packet items (appeal gaps before assistance gaps)
- precedence_order: appeal ID, documented trials, undocumented trials, missing items

For `effective_benchmark_by_plan_modifier_and_date`:
- controlling: claim line IDs, winning benchmark IDs (in cpt-code order)
- exception: rejected stale benchmark IDs
- precedence_order: winning benchmarks then rejected benchmarks

For `new_patient_specific_p2p_information`:
- controlling: P2P event ID, supporting clinical document IDs
- exception: unresolved criterion IDs, missing PET factor names (as enum strings)
- precedence_order: P2P event, clinical docs, unresolved criteria

For `margin_threshold_then_charge_sensitivity`:
- controlling: all queue row IDs from task_context
- exception: below-threshold row IDs
- precedence_order: rows in task_context order
