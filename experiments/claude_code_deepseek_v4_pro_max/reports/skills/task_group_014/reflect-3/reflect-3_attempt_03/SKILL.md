# Northstar Payer Operations Skill

## Overview

This skill covers Northstar Health Plan payer operations tasks: utilization management determinations, pharmacy coverage appeals, payment integrity corrections, peer-to-peer summaries, and financial queue analysis. Every task uses a shared read-only operations environment and requires a structured JSON answer conforming to a provided template.

## Task Input Structure

Each task provides three inputs:
- **prompt.txt** — Natural-language description of the work item, requester role, reporting date, and what to return.
- **task_context.json** — Machine-readable context: target business IDs, environment access details, and role-specific memos.
- **answer_template.json** — The exact JSON shape to return, including required fields, enum choices, ordering rules, and numeric precision.

## Environment Access Pattern

The environment exposes:
- **REST endpoints** (`GET /api/cases`, `/api/policies`, `/api/appeals`, `/api/rate-schedules`, `/api/documents/{id}`, etc.) — return nested business objects with related records.
- **A SQL endpoint** (`POST /sql/query`) — accepts `{"sql": "SELECT ..."}` for filtered queries across tables.
- **A base portal** (`GET /` or `GET /portal`) — lists available entry points.

Prefer REST endpoints for single-business-object lookups (e.g., `GET /api/cases/{case_id}` returns the case with its documents, facts, criteria, authorizations, claims, appeals, drug trials, P2P events, and request lines nested inline). Use SQL for cross-entity searches or filtering (e.g., `SELECT * FROM service_margin WHERE month_id IN (...)`).

## Data Model Reference

Key entities and their relationships:

| Table/Endpoint | Purpose | Key Columns |
|---|---|---|
| `cases` | Authorization, appeal, claim-review, and queue work items | case_id, member_id, policy_id, service_domain, current_stage, current_status |
| `members` | Patient demographics and plan enrollment | member_id, plan_id, plan_type, member_status |
| `providers` | Rendering and requesting providers | provider_id, specialty, npi, organization |
| `policies` | Medical and payment policy definitions | policy_id, version, effective_start, effective_end, precedence |
| `policy_criteria` | Individual criteria within a policy | criterion_id, criterion_key, approval_required, result_if_missing |
| `case_criteria` | Criteria results for a specific case | case_id, criterion_id, result, evidence_fact_ids, gap_description |
| `documents` | Clinical, administrative, and payment documents | document_id, case_id, document_type, is_current, source_system |
| `document_facts` | Extracted facts from documents | fact_id, document_id, fact_key, fact_value, supports_criteria |
| `request_lines` | Requested service/procedure lines | line_id, case_id, cpt_code, modifier, requested_units |
| `authorizations` | Authorization decisions | auth_id, case_id, auth_number, status, approved_units, approved_cpt |
| `claims` | Paid or queued claims | claim_id, case_id, paid_total, claim_status, auth_number |
| `claim_lines` | Individual claim service lines | claim_line_id, claim_id, cpt_code, modifier, units, paid_amount |
| `payment_benchmarks` | Rate schedules for repricing | benchmark_id, cpt_code, modifier, allowed_amount, source_name, source_version, effective dates |
| `appeals` | Coverage and payment appeals | appeal_id, case_id, appeal_path, appeal_deadline, expedited_attestation |
| `drug_trials` | Medication trial history | trial_id, case_id, medication, outcome, documented |
| `assistance_screen` | Manufacturer assistance program status | case_id, program_name, assistance_status, missing_fields |
| `p2p_events` | Peer-to-peer discussion records | p2p_id, case_id, outcome, new_information, final_status |
| `service_margin` | Monthly therapy margin data | month_id, payer_segment, cpt_code, net_revenue, variable_cost, fixed_cost_allocated, charge_sensitive |
| `plans` | Health plan details | plan_id, payer_name, plan_type, state, network |

## General Workflow

### Step 1 — Read All Three Inputs
Read prompt.txt for the narrative task description, task_context.json for target IDs and role details, and answer_template.json for the exact output shape. The template defines required keys, enum choices, ordering rules, and numeric precision — these are constraints, not suggestions.

### Step 2 — Query the Environment
Use the REST endpoint for the target business object first (e.g., `/api/cases/{case_id}`). This returns the case plus nested related records. Supplement with SQL queries when you need filtered results across entities. Query related policies via `/api/policies/{policy_id}` to get the policy-level criteria definitions and precedence. Query rate schedules via `/api/rate-schedules` for payment benchmark data.

### Step 3 — Map Evidence to Criteria
For each criterion in the case or policy, identify:
- **Result**: met, not_met, partial, unclear, or not_applicable — taken directly from case_criteria.
- **Supporting evidence**: The document_facts whose `supports_criteria` field references the criterion ID.
- **Gaps**: Any criterion with a non-empty `gap_description` or a `partial`/`not_met` result.

### Step 4 — Classify Records
Separate records into:
- **Evidence / controlling**: Records that directly determine the outcome — current documents whose facts support met criteria, effective benchmarks used for repricing, P2P events that determined the final status.
- **Excluded / exception**: Stale documents (is_current=0), expired benchmarks, undocumented drug trials, missing packet items, criteria gaps.

### Step 5 — Follow the Template Exactly
- Use **only** values from the enum choices listed in the template.
- Respect **ordering rules** stated in the template (ascending CPT codes, alphabetical medication names, operational packet order, claim-line order, alphabetical segment order).
- Apply **numeric precision** as specified (dollars to cents, ratios to 4 decimal places).
- Use **null** only where explicitly permitted (e.g., absent modifiers, no applicable deadline).

### Step 6 — Construct the Basis Audit
Every answer requires a `basis_audit` object. This is a business audit trail, not boilerplate.

**source_precedence** — Select exactly one from the six available rules based on the domain:

| Rule | When to Use |
|---|---|
| `current_clinical_records_over_stale_export` | Current clinical documents override older exports; stale records are excluded |
| `payer_appeal_before_manufacturer_assistance` | Payer appeal packet items take priority over manufacturer assistance program items |
| `effective_benchmark_by_plan_modifier_and_date` | Payment benchmarks are selected by plan type, modifier, and effective-date range |
| `new_patient_specific_p2p_information` | A peer-to-peer discussion produced the final determination |
| `margin_threshold_then_charge_sensitivity` | Financial queue rows are ranked by revenue-to-cost threshold compliance first, then charge sensitivity |
| `appeal_deadline_then_clinical_then_payment_integrity` | Multi-factor: appeal deadlines take highest priority, then clinical factors, then payment integrity items |

**controlling_record_ids** — Environment record IDs (fact IDs, document IDs, benchmark IDs, trial IDs, P2P event IDs, service-margin month IDs) that directly control the result. Include records for both met and not-met criteria when both are part of the determination.

**exception_record_ids** — Records that explain exclusions, denials, missing information, or route priority. Use business gap/exception order: criteria or route gaps before stale or excluded records when both appear. A record that documents a gap belongs here, not in controlling.

**precedence_record_order** — The union of controlling and exception records, ordered by source-precedence priority (highest priority first). Controlling records come before exception records within the same precedence tier.

### Record ID Selection Guidelines

When choosing which environment IDs to include in the basis audit:
- Use **fact IDs** (`FACT-DOC-...`) for criteria-level evidence — each fact links a document to a specific criterion via `supports_criteria`.
- Use **document IDs** (`DOC-TR-...`) when referring to whole documents (evidence_documents, excluded_documents lists).
- Use **benchmark IDs** (`BM-...`) for payment benchmark records that control repricing amounts.
- Use **trial IDs** (`TRIAL-...`) for drug trial records.
- Use **month IDs** (`SM-...`) for service_margin queue rows.
- Use **P2P event IDs** (`P2P-...-E1`) for peer-to-peer events.
- A record can appear in **either** controlling or exception, never both.
- When a criterion result is `not_met` and the fact documents the absence (e.g., "not documented"), that fact is an **exception** record because it explains the gap, not a controlling record that establishes compliance.

## Domain-Specific Patterns

### UM Nurse Determinations
- Criteria results come directly from the case's `criteria` array.
- The authorization record (if present) provides the recommended auth details.
- Exclude documents with `is_current: 0` (stale exports).
- Evidence documents are those with `is_current: 1` that support the criteria.
- The determination letter and next action flow from the criteria outcome: all met → approval, any not_met → denial, partial/unclear → pend or escalate.

### Pharmacy Coverage Appeals
- Drug trials with `documented: 1` are documented failures; those with `documented: 0` are undocumented or insufficient.
- Medication names in lists must be lowercase and alphabetical.
- Required packet items follow operational order: payer appeal items before manufacturer assistance items.
- Missing packet items follow case-specific gap order: appeal evidence gaps before assistance information gaps.
- The assistance program status from the environment maps to the template's status enum.
- Missing fields in the assistance object are listed alphabetically by field ID.

### Payment Integrity Corrections
- Identify the current benchmark by matching payer, plan_type, CPT, modifier, and effective-date range.
- Identify the stale source by finding the benchmark that matches what was actually paid.
- Compute per-line: `correct_allowed_amount = benchmark.allowed_amount × units`.
- Compute per-line recovery: `correct_allowed_amount - paid_amount`.
- Line dispositions: positive recovery → `correct_upward`, negative → `correct_downward`, zero → `no_change`.
- The claim-level recovery is the sum of line recoveries; total correct is the sum of line correct amounts.

### Peer-to-Peer Summaries
- The P2P event outcome determines the p2p_outcome field.
- `new_information_changed_review` is true only when the P2P supplied new patient-specific information that materially changed the original review.
- Unresolved criteria are those where the factor was never provided and remains an open gap — even if the result is `not_met` (final), the criterion itself is unresolved in the business sense when it represents a missing factor that could be supplied later.
- Missing PET factors are listed in the order shown in the template choices, including all factors that remain unsupported.
- When the final determination is adverse, calculate the internal appeal deadline using the stated window (e.g., 180 days) from the final adverse determination date.

### Financial Queue Analysis
- `total_cost = variable_cost + fixed_cost_allocated` (as defined in the task context).
- `margin = net_revenue - total_cost`.
- `revenue_to_cost_ratio = net_revenue / total_cost` (to 4 decimal places).
- `below_threshold = revenue_to_cost_ratio < threshold` (threshold from task context).
- `charge_sensitive` comes directly from the environment row.
- Recommended actions: below_threshold → `payer_contract_review`; charge_sensitive (not below) → `monitor_charge_sensitive`; neither → `monitor_no_action`.
- Segment lists are alphabetical by enum value.
- The top issue is formed as `{segment}_{cpt}` for the highest-priority below-threshold row.
- `gap_to_120pct = (threshold × total_cost) - net_revenue` for the top below-threshold issue.

## Output Rules

- Return **exactly one JSON object** — no markdown, no prose, no comments outside the JSON.
- All required top-level keys from the template must be present.
- No additional top-level keys beyond those in the template (unless `additional_properties` is explicitly allowed).
- Enum values must match the template's choices exactly (case-sensitive).
- List ordering must follow the template's stated ordering rules.
- Currency values are JSON numbers (not strings), rounded to the specified precision.
- Dates are ISO 8601 calendar dates (`YYYY-MM-DD`).
- Boolean values are JSON `true`/`false`, not strings.
- Use `null` for absent modifiers and for deadlines that do not apply.
