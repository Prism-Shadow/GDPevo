# Northstar Payer Operations — Structured Determination Skill

## When to Use

Use this skill when tasked with producing a structured JSON determination, summary, or correction packet for a Northstar Health Plan business operation — including utilization management (UM) nurse review, pharmacy appeals intake, payment integrity claim repricing, peer-to-peer (P2P) authorization closure, or UM-finance margin queue analysis.

## Environment Access

All data lives in a shared read-only payer operations environment. Two access modes are available:

### REST Endpoints (no auth header needed)
| Endpoint | Use |
|---|---|
| `GET /api/tables` | Discover the full database schema (table names, columns, types) |
| `GET /api/cases` | List all cases |
| `GET /api/cases/{case_id}` | Fetch one case with all joined sub-records (documents, criteria, facts, appeals, authorizations, claims, request lines, drug trials, P2P events, assistance screens) |
| `GET /api/policies` | List all policies |
| `GET /api/policies/{policy_id}` | Fetch one policy with its criteria |
| `GET /api/documents/{document_id}` | Fetch one document with its clinical facts |
| `GET /api/rate-schedules` | List all payment benchmarks / rate schedules |
| `GET /api/appeals` | List all appeals |

### SQL Endpoint (bearer token required)
`POST /sql/query` with header `Authorization: Bearer pa-review-token-014` and body `{"sql": "<query>"}`. Useful for targeted queries: filter benchmarks by plan/domain/CPT, list facts by case, query service_margin rows by month_id, etc.

**Prefer REST for case-level exploration** — the `/api/cases/{case_id}` endpoint returns the case plus all joined sub-records in one call. Use SQL when you need to filter or aggregate across cases.

## Data Model

The environment is organized around these core entities:

- **cases** — The central work item. Links to member, provider, plan, policy, and contains the current stage/status.
- **members** — Patient demographics, plan enrollment, employer group.
- **plans** — Plan type (commercial, medicaid, medicare_advantage, workers_comp), network, effective dates.
- **policies** — Clinical/administrative policy with precedence and versioning.
- **policy_criteria** — Individual criterion definitions with approval_required flag and result_if_missing.
- **case_criteria** — Per-case criterion evaluation results linked to evidence.
- **documents** — Clinical/business documents with is_current flag (1 = current, 0 = stale/legacy).
- **document_facts** — Discrete facts extracted from documents, linked to criteria via supports_criteria.
- **request_lines** — Service/procedure lines on authorization cases.
- **authorizations** — Authorization records with status, approved units/dates/CPTs.
- **claims / claim_lines** — Paid claims with line-level amounts and modifiers.
- **payment_benchmarks** — Rate schedule entries keyed by payer + plan_type + service_domain + cpt_code + modifier + effective date range.
- **appeals** — Appeal records with path, deadline, expedited flag, owner.
- **drug_trials** — Medication trial history with documented flag and outcome.
- **assistance_screen** — Manufacturer assistance program eligibility.
- **p2p_events** — Peer-to-peer discussion records.
- **service_margin** — Monthly finance rows for margin analysis.

### Key Data Relationships

- `is_current = 1` on documents distinguishes active clinical evidence from stale exports.
- `supports_criteria` on document_facts maps facts to criterion IDs.
- `documented` flag on drug_trials distinguishes documented failures (1) from unsubstantiated mentions (0).
- `approval_required` on policy_criteria: 1 = required for approval, 0 = informational/process.
- `charge_sensitive` on service_margin: 1 = flagged for charge sensitivity review.
- Benchmark records are matched by: payer + plan_type + service_domain + cpt_code + modifier + effective date range covering the service date.

## Exploration Workflow

For any new task, follow this sequence:

1. **Read the answer template first.** Understand every required field, its enum choices, ordering rules, and precision requirements.

2. **Fetch the case via REST.** `GET /api/cases/{case_id}` gives you the case, member, plan, provider, documents, document facts, criteria results, request lines/claim lines, authorizations, appeals, drug trials, P2P events, and assistance screens — all in one response.

3. **Fetch the policy.** `GET /api/policies/{policy_id}` to see the full criterion definitions, approval requirements, and result_if_missing rules.

4. **Fetch individual documents as needed.** `GET /api/documents/{document_id}` for detailed clinical facts when the case-level summary isn't enough.

5. **Query benchmarks or margin data via SQL** when the task requires rate schedule lookups or financial calculations.

6. **Identify current vs. excluded records.** Documents with `is_current = 0` are excluded. Facts from excluded documents go into exception/gap lists, not controlling evidence. Stale benchmarks (expired effective_end before the service date) are rejected in favor of current ones.

## Answer Construction Rules

### Criteria Results

Map each required criterion ID from the answer template to its result. The result comes from `case_criteria` on the case. If a criterion appears in the template but not in the case's criteria array, check the policy — it may have `approval_required = 0` and not be evaluated for this case.

### Document Classification

- **evidence_documents**: List document IDs of current (`is_current = 1`) documents whose facts support the determination. Sort ascending by document_id.
- **excluded_documents**: List document IDs of non-current (`is_current = 0`) or otherwise inapplicable documents. Sort ascending by document_id.

### Recommendation / Status Mapping

The recommendation, final_status, route, determination_letter, and next_action form a consistent business-state vector. Derive them from the criteria pattern:

| Criteria Pattern | recommendation | final_status | route | determination_letter | next_action |
|---|---|---|---|---|---|
| All met | approve | approved | nurse_approval | approval | issue_approval |
| All met + P2P overturn | approve | approved | medical_director_review | approval | issue_approval |
| Any not_met (deny-if-missing) | deny | denied | medical_director_review | adverse_determination | issue_denial |
| Any not_met + P2P uphold | deny | denied | — | denial | — |
| Missing info, pend-if-missing | pend_for_information | pended | pending_information | information_request | request_more_information |
| Partial criteria, partial evidence | partial_approval | partially_approved | nurse_approval | partial_approval | issue_approval |

For P2P tasks, map `p2p_outcome` from the P2P event: `uphold_intended_adverse_decision` → denial path; `overturn_to_approval` → approval path.

### Authorization Block

When an authorization record exists on the case, use its values directly:
- `auth_number` from the auth record
- `approved_units`, `approved_start`, `approved_end` as-is
- `approved_cpt` as a sorted list (ascending CPT code) parsed from the comma-separated or single-value field
- `modifier` from `approved_modifier`

When no authorization exists (denied, pending), set the authorization block fields to their zero/null equivalents per the template.

### List Ordering Rules

- **evidence_documents / excluded_documents**: ascending by document_id.
- **documented_failures / undocumented_or_insufficient_failures**: alphabetical by medication name (lowercase).
- **approved_cpt**: ascending CPT code.
- **required_packet_items**: payer appeal items first, then assistance items. Within each group, use operational order (denial → authorization → rationale → evidence → income).
- **missing_packet_items**: appeal evidence gaps before assistance information gaps.
- **missing_fields (assistance)**: alphabetical by field id.
- **below_threshold_segments / charge_sensitive_segments**: alphabetical by enum value.
- **missing_pet_factors**: use the order shown in the template choices.
- **claim lines / rows**: use the source order from the environment (line_number for claims, task_context order for queues).
- **unresolved_criteria**: ascending criterion ID.

### Numeric Precision

- Currency (USD): round to 2 decimal places.
- Ratios (revenue_to_cost_ratio): 4 decimal places.
- Units: integer (no decimal places).
- Percentages and scores: use the unit specified in the document fact.

### Modifier Handling

- Use `null` (JSON null, not the string "null") when a claim line or request line has no modifier.
- Modifier values are case-sensitive: `"TC"`, `"GP"`, etc.

### Date Fields

- All dates in `YYYY-MM-DD` format (ISO 8601 calendar date).
- Appeal deadlines: calculate from the adverse determination date plus the plan's appeal window (e.g., 180 days for internal appeals).
- Periods: `YYYY-MM` format.

## Basis Audit Construction

Every answer requires a `basis_audit` block. This records the business reasoning chain.

### source_precedence

Choose the precedence rule that governs how evidence was weighted:

| Rule | When to Use |
|---|---|
| `current_clinical_records_over_stale_export` | UM review where current docs (is_current=1) take priority over legacy exports (is_current=0) |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal where payer coverage criteria are evaluated before manufacturer assistance eligibility |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity where the correct benchmark is chosen by matching plan_type + modifier + effective date range |
| `new_patient_specific_p2p_information` | P2P review where the P2P discussion may supply new clinical information that could change the original determination |
| `margin_threshold_then_charge_sensitivity` | Finance margin queue where rows are first evaluated against the revenue-to-cost threshold, then flagged for charge sensitivity |

### controlling_record_ids

List the environment record IDs that directly determine the outcome. These are:
- Fact IDs from current documents that support met criteria
- Benchmark IDs from the effective rate schedule
- Authorization record IDs
- Service margin month_ids

Use the operational evidence order: for clinical reviews, list facts in the order their criteria are evaluated. For financial reviews, list benchmarks in CPT order or queue row order.

### exception_record_ids

List record IDs that explain gaps, exclusions, or issues:
- Stale document fact IDs
- Stale/expired benchmark IDs
- Drug trial IDs for undocumented/insufficient failures
- P2P event IDs when the discussion didn't change the outcome
- Below-threshold margin rows (when they explain the gap)

Use business gap/exception order: criteria or route gaps before stale or excluded records when both appear.

### precedence_record_order

Concatenate controlling_record_ids followed by exception_record_ids, all in source-precedence order (highest priority first). This is the full evidence trail.

## Task-Type Specific Guidance

### UM Nurse Review (Physical Therapy)
- Focus on criteria: PT-ACTIVE, PT-DEFICIT, PT-DX, PT-POC, PT-UNITS.
- Requested units are the sum across all request lines.
- Evidence documents are those with `is_current = 1` that provide facts supporting the criteria.
- Excluded documents are those with `is_current = 0` (stale exports, legacy records).
- Source precedence: `current_clinical_records_over_stale_export`.

### Pharmacy Appeals Intake
- Focus on criteria: DRUG-AUTH, DRUG-DENIAL, DRUG-RATIONALE, DRUG-FAILURES.
- Classify medication failures: documented (`documented = 1`) vs. undocumented/insufficient (`documented = 0` or mentioned without fill record).
- Required packet items include both payer appeal items and manufacturer assistance items.
- Missing packet items list appeal gaps first, then assistance gaps.
- Assistance status derives from the assistance_screen: missing_fields → `eligible_missing_information`.
- Source precedence: `payer_appeal_before_manufacturer_assistance`.

### Payment Integrity Claim Repricing
- Match benchmarks by: payer + plan_type + service_domain + cpt_code + modifier + effective date range.
- The stale source is the benchmark with an effective_end before the service date.
- Correct allowed amount = benchmark allowed_amount × claim line units.
- Recovery = correct_allowed - paid (positive = underpayment/correct_upward, negative = overpayment/correct_downward).
- Line dispositions: `correct_upward` when correct > paid, `correct_downward` when correct < paid, `no_change` when equal.
- Source precedence: `effective_benchmark_by_plan_modifier_and_date`.

### P2P Authorization Closure
- Map p2p_outcome from the P2P event directly.
- new_information_changed_review: true only when the P2P provided new patient-specific facts that changed criteria results.
- missing_pet_factors: list ALL factors from the template that remain unsupported (check both the document facts and P2P new_information).
- internal_appeal_deadline: null when approved, otherwise adverse determination date + 180 calendar days.
- recommended_alternative: SPECT MPI when PET is denied; none when approved.
- Source precedence: `new_patient_specific_p2p_information`.

### UM-Finance Margin Queue
- total_cost = variable_cost + fixed_cost_allocated.
- margin = net_revenue - total_cost.
- revenue_to_cost_ratio = net_revenue / total_cost (4 decimal places).
- below_threshold = (revenue_to_cost_ratio < threshold).
- recommended_action: `payer_contract_review` when below_threshold and not charge_sensitive; `monitor_charge_sensitive` when charge_sensitive (even if above threshold); `monitor_no_action` otherwise.
- top_issue: format as `{segment}_{cpt}` for the row with the largest gap to threshold; `"none"` if no below-threshold rows.
- gap_to_120pct: (threshold × total_cost) - net_revenue for the top below-threshold issue.
- Source precedence: `margin_threshold_then_charge_sensitivity`.

## Common Pitfalls

1. **Missing the is_current flag**: Always check `is_current` on documents. A document that looks relevant may be a stale export that must be excluded.

2. **Undocumented vs. documented drug failures**: The `documented` flag on drug_trials (not just the presence of a trial row) determines classification. An undocumented trial goes into `undocumented_or_insufficient_failures`.

3. **Benchmark matching requires all dimensions**: payer + plan_type + service_domain + cpt_code + modifier + effective date range. Missing any dimension can match a distractor benchmark.

4. **Modifier null vs. empty string**: Always use JSON `null` for absent modifiers, never `""`.

5. **Recovery amount sign**: Use the underpayment amount (positive) when correct > paid. The field represents the absolute difference, not a signed adjustment.

6. **Packet item ordering**: Appeal evidence items come before assistance items in required lists. In missing lists, appeal gaps come before assistance gaps.

7. **basis_audit record types mix**: Controlling records can be fact IDs, benchmark IDs, authorization IDs, or month_ids depending on the task type. Exception records can be fact IDs, trial IDs, benchmark IDs, or P2P event IDs. Use the ID format that matches the entity being referenced.

8. **Criteria that appear in policy but not in case**: Some policy criteria have `approval_required = 0` and may not be evaluated on the case. Don't force them into criteria_results unless the template requires them.
