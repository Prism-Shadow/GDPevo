---
name: northstar-payer-review
description: Process Northstar Health Plan payer-operations review tasks (prior auth, appeals, payment integrity, P2P, margin queues) against the shared Northstar environment API, producing structured JSON determinations with full basis audit trails.
---

# Northstar Payer Operations Review

## Purpose

This skill handles structured review tasks across the Northstar Health Plan payer-operations domain. It covers five review types: utilization management (UM) determinations, pharmacy coverage appeals, payment integrity claim repricing, peer-to-peer (P2P) summaries, and therapy margin queue analysis. The skill produces a single JSON object conforming to the supplied answer template, including a full business basis audit trail.

## When to Use

Invoke this skill when a task requires:
- Reviewing a Northstar case, appeal, claim, P2P event, or margin queue against the shared payer-operations environment
- Producing a structured determination, intake disposition, correction packet, P2P summary, or margin queue report
- The task supplies `task_context.json` (target IDs, requester role, dates, domain) and `answer_template.json` (required output shape)

## Operating Rules

### 1. Environment Access

The shared payer-operations environment is at the configurable base URL provided in the task context (placeholder `<TASK_ENV_BASE_URL>`). Two access channels are available:

**SQL endpoint** — `POST /sql/query` with header `Authorization: Bearer pa-review-token-014`. Use for complex cross-entity queries that span multiple tables or require aggregation.

**REST business endpoints** — all use the same bearer token. Available paths:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check / root |
| GET | `/portal` | Portal landing |
| GET | `/api/tables` | List available data tables |
| GET | `/api/cases` | List all cases |
| GET | `/api/cases/{case_id}` | Single case detail |
| GET | `/api/policies` | List all policies |
| GET | `/api/policies/{policy_id}` | Single policy detail |
| GET | `/api/documents/{document_id}` | Single document |
| GET | `/api/rate-schedules` | List rate schedules |
| GET | `/api/appeals` | List appeals |

Prefer REST endpoints for direct record access by known ID. Use SQL for multi-table joins, filtering, or aggregation not supported by a single REST call.

**Hard constraint**: Do not inspect construction files, generated data files, SQLite files, manifests, setup scripts, or environment source files directly. All data must come through the API.

### 2. Information Gathering Sequence

Follow this sequence for every review task:

1. **Parse the task context** — Extract the target business ID(s), requester role, reporting date, service domain, and any local memo instructions from `task_context.json`.

2. **Load the answer template** — Read `answer_template.json` to understand the exact output shape, required enums, and field constraints before gathering data.

3. **Retrieve core records via REST** — Fetch the target entity (case, appeal, claim) and any directly referenced policies, documents, or rate schedules by ID.

4. **Expand with SQL as needed** — Use `POST /sql/query` when the REST endpoints don't expose the needed cross-entity view (e.g., joining claim lines to rate schedules, checking plan coverage criteria, aggregating margin data).

5. **Identify controlling vs. exception records** — As you gather records, classify each as either:
   - **Controlling** — directly drives the determination (e.g., the effective policy criterion, the applicable rate schedule, the current clinical record)
   - **Exception** — explains exclusions, denials, missing information, route priority, or gaps

### 3. Evidence Classification

For every document or record reviewed, determine whether it is:

- **Included (evidence)** — Current, relevant, and relied upon in the determination. List as `evidence_documents` (or equivalent field) in ascending document_id order.
- **Excluded** — Stale, superseded, irrelevant, or insufficient. List as `excluded_documents` (or equivalent field) in ascending document_id order. Be prepared to explain the exclusion reason in exception records.

**Staleness rule**: Current live records from the environment always take precedence over any stale exported data. When the same entity exists in both a current environment record and a stale export, use the current record and classify the stale one as excluded.

### 4. Criteria Evaluation

Map each applicable policy or clinical criterion to a result using this framework:

| Result | Meaning |
|--------|---------|
| `met` | Criterion is fully satisfied by the evidence |
| `not_met` | Criterion is clearly not satisfied |
| `unclear` | Evidence is ambiguous or insufficient to decide |
| `not_applicable` | Criterion does not apply to this case or request |
| `partial` | (Appeals/drug tasks only) Criterion is partially satisfied |

Use the exact criterion IDs required by the answer template. Track any criteria that remain unresolved after review in a separate `unresolved_criteria` list.

### 5. Source Precedence Rules

Every determination must declare a `source_precedence` rule from the canonical set of six. Choose the rule that matches the task type and evidence landscape:

| Rule | Apply When |
|------|-----------|
| `current_clinical_records_over_stale_export` | The task involves clinical evidence where the environment holds more current records than a legacy export |
| `payer_appeal_before_manufacturer_assistance` | The task involves both a coverage appeal and a manufacturer assistance program screen; process the payer appeal first |
| `effective_benchmark_by_plan_modifier_and_date` | The task involves repricing against rate schedules; select the schedule that matches both the plan modifier and the effective date |
| `new_patient_specific_p2p_information` | A peer-to-peer discussion has introduced new patient-specific information that may change the initial review |
| `margin_threshold_then_charge_sensitivity` | The task involves margin analysis; apply the revenue-to-cost threshold first, then evaluate charge sensitivity for rows below threshold |
| `appeal_deadline_then_clinical_then_payment_integrity` | The task involves an appeal where the deadline is the primary constraint, followed by clinical merit, then payment integrity considerations |

### 6. Record Ordering Conventions

When populating the `basis_audit.precedence_record_order` list, follow these ordering rules consistently:

- **Highest priority first** — The record with the greatest controlling weight appears at index 0
- **Controlling records before exception records** — Records that directly determine the result come before those that explain gaps or exclusions
- **Within exception records** — Criteria/route gaps appear before stale or excluded records when both types are present
- **Within same-type records** — Use ascending record ID order as the tiebreaker

### 7. Routing and Disposition

Map the final determination to the correct routing path based on the answer template's enum choices. General patterns:

| Outcome | Typical Route |
|---------|--------------|
| All criteria met, no issues | Direct approval / standard processing |
| Missing information that the requester can supply | Request more information / pend |
| Medical necessity question | Route to medical director review |
| Criteria not met and no further evidence expected | Issue denial |
| Appeal with new evidence | File appeal / expedited processing |
| P2P changed the review | Update authorization and issue corresponding letter |
| Margin below threshold, not charge sensitive | Payer contract review |
| Margin below threshold, charge sensitive | Monitor charge sensitive |

### 8. Basis Audit Trail

Every answer must include a complete `basis_audit` object with these four required keys:

- **`source_precedence`** — One of the six canonical source-precedence enum values (see Section 5)
- **`precedence_record_order`** — All controlling and exception records, ordered highest priority first (see Section 6)
- **`controlling_record_ids`** — The subset of records that directly control the result, in operational evidence order
- **`exception_record_ids`** — The subset of records that explain exclusions, denials, missing information, or route priority gaps, in business gap/exception order

### 9. Output Rules

- Return **exactly one JSON object** — no markdown fences, no prose, no comments outside the JSON
- Match the answer template shape exactly — all required top-level keys, all required nested keys, all enum values drawn from the specified choices
- **Currency**: Round to two decimal places (cents) using JSON numbers
- **Dates**: ISO 8601 calendar dates in `YYYY-MM-DD` format
- **Null modifiers**: Use `null` (not an empty string) when a claim line has no modifier
- **Line/row ordering**: Preserve the source ordering specified in the answer template (claim-line order, queue row ID order, alphabetical, etc.)
- **List fields**: Use alphabetical or ascending-ID order as specified by each field's ordering rule in the answer template
- **Empty lists**: Use `[]`, not `null`, when a list field has no entries but is required

### 10. Task-Type-Specific Notes

**UM Nurse Determination (prior authorization)**:
- Map clinical criteria using the PT-* criterion IDs
- Evidence documents and excluded documents must both be listed
- The authorization block requires approved CPT codes in ascending order

**Pharmacy Appeals Coordinator Disposition**:
- Classify prior medication failures into `documented_failures` and `undocumented_or_insufficient_failures`
- Required and missing packet items follow operational packet order (payer appeal items before assistance items)
- Evaluate both the appeal path and the assistance program screen independently

**Payment Integrity Claim Repricing**:
- Reject stale rate schedules explicitly in `stale_source_rejected`
- The `recovery_amount` at the claim level is the sum of line-level recovery amounts
- When the corrected allowed total exceeds the paid total, recovery represents an underpayment (positive amount)

**Peer-to-Peer Summary**:
- Record whether `new_information_changed_review` based on the P2P discussion
- PET-over-SPECT factors that remain unsupported go in `missing_pet_factors`
- Calculate the `internal_appeal_deadline` as 180 calendar days from the final adverse determination date; use `null` when not adverse

**Therapy Margin Queue**:
- `total_cost` = variable_cost + fixed_cost_allocated (as defined in the task context)
- `revenue_to_cost_ratio` = revenue / total_cost, to 4 decimal places
- `below_threshold` is true when the ratio is below the configured threshold (typically 1.2)
- `charge_sensitive` is a separate boolean flag from the source data
- `gap_to_120pct` is the dollar gap between actual revenue and 1.2 × total_cost for the top below-threshold issue
