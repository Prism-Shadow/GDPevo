## Northstar Health Plan Payer Operations

This skill handles structured decision-support tasks for Northstar Health Plan. Every task provides a prompt, a task-context payload, and an answer template. You must query a shared payer-operations environment (SQL + REST), gather evidence, and return exactly one JSON object conforming to the template.

### Input files (per-task)

In every task workspace you will find:

- `input/prompt.txt` — natural-language request from the business team.
- `input/payloads/task_context.json` — the target business ID, requester role, reporting date, environment credentials, and domain-specific notes.
- `input/payloads/answer_template.json` — the required JSON shape, field enumerations, ordering rules, and precision constraints.

Root-level environment guidance lives in `/work/environment_access.md` (or the equivalent path in the task workspace). Use it to discover the base URL, SQL endpoint, and bearer token.

### Environment access

Every Northstar task uses the same shared payer-operations environment.

**Base URL**: Read from `environment_access.md` (or `task_context.json.environment.base_url`) — typically `http://task-env:9014/`.

**SQL endpoint**: `POST /sql/query`
- Header: `Authorization: Bearer pa-review-token-014`
- Content-Type: `application/json`
- Body: `{"sql": "<SELECT | WITH | PRAGMA table_info>", "params": [...]}`

**REST endpoints** (all GET, suffix on base URL):
- `/` — environment index
- `/portal` — payer portal overview
- `/api/tables` — list all available tables
- `/api/cases` — list cases
- `/api/cases/{case_id}` — single case detail
- `/api/policies` — list policies
- `/api/policies/{policy_id}` — single policy detail
- `/api/documents/{document_id}` — single clinical or administrative document
- `/api/rate-schedules` — list rate schedules and benchmarks
- `/api/appeals` — list appeals

### General workflow

Follow this order for every task. Do not skip steps.

**Step 1 — Read the inputs**
Read `input/prompt.txt`, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`. Identify:
- The target business ID (`target_business_id`, `case_id`, `claim_id`, `appeal_id`, `business_id`, or `queue_row_ids`)
- The service domain and work type
- Every required top-level field, its type, enum choices, ordering rules, and precision constraints

**Step 2 — Explore the data environment**
Use SQL first to understand what is available:
- `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name` — list all tables
- `PRAGMA table_info({table})` — inspect column names and types for each relevant table

Then retrieve the specific records named by the target business ID. You may combine SQL queries with REST endpoints. For example:
- A case may be fetched via `GET /api/cases/{case_id}` and also joined through SQL on `cases`, `documents`, `claim_lines`, `rate_schedules`, `appeals`, `policies`, `service_margin`, etc.

**Step 3 — Gather evidence systematically**
Query every data source relevant to the template fields. Common evidence categories:
- **Case/claim records** — case metadata, status, request lines, authorization numbers
- **Clinical documents** — evaluations, plans of care, diagnostic reports, peer-to-peer notes
- **Policy criteria** — applicable clinical policy and its criterion IDs, thresholds, and rules
- **Rate schedules / benchmarks** — current and stale versions, plan-modifier-date-specific rates
- **Appeal records** — appeal path, deadlines, packet requirements, prior determinations
- **Drug trials / formulary** — documented and undocumented medication failures
- **Assistance programs** — eligibility, missing fields, status
- **Service margin rows** — cost, revenue, margin, ratios, charge-sensitivity flags

**Step 4 — Classify and evaluate**
Map each template field to the evidence you gathered. Apply the business rules implied by the template:
- Criteria keys map to policy criteria; mark each as `met`, `not_met`, `unclear`, or `not_applicable` based on evidence in documents and policy records.
- For document lists (`evidence_documents`, `excluded_documents`): include documents that contributed to the determination in evidence; exclude stale or superseded documents.
- For enumeration fields (`recommendation`, `final_status`, `route`, `next_action`, etc.): choose the value that follows from the criteria results and the overall evidence picture.
- For currency fields: round to two decimal places.
- For ratios: round to four decimal places.
- For dates: use `YYYY-MM-DD` format. Calculate deadlines using the plan rules documented in the task (e.g. "180-day internal appeal window from the final adverse determination date").
- For lists: follow the ordering rule stated in the template (ascending ID, alphabetical, claim-line order, queue-row-id order, operational packet order, gap order).
- Use `null` for absent modifiers; never use an empty string.

**Step 5 — Build the basis_audit**
Every answer must include a `basis_audit` object with these exactly-four keys:

| Key | Description |
|---|---|
| `source_precedence` | Pick the single enum value that best describes the evidence-priority rule governing this task. Available values: `current_clinical_records_over_stale_export`, `payer_appeal_before_manufacturer_assistance`, `effective_benchmark_by_plan_modifier_and_date`, `new_patient_specific_p2p_information`, `margin_threshold_then_charge_sensitivity`, `appeal_deadline_then_clinical_then_payment_integrity`. |
| `controlling_record_ids` | List the environment record IDs that directly control the result (documents, case records, P2P events, benchmark records, margin rows, appeal records). Order by operational evidence order. |
| `exception_record_ids` | List records that explain exclusions, denials, missing information, or route priority. Put criteria/route gaps before stale/excluded records when both appear. |
| `precedence_record_order` | List all controlling and exception records together in source-precedence order, highest priority first. |

**Step 6 — Assemble and validate**
Build the JSON object with every required top-level key. Before finalizing, verify:
- All required fields are present.
- All enum values match the allowed choices in the template.
- All list items follow the stated ordering rules.
- All numeric values use the stated precision.
- All dates are valid ISO 8601 calendar dates or `null` where allowed.
- `modifier` fields use `null` (not empty string) when absent.
- No prose, markdown, or commentary outside the JSON object.

### Domain-specific guidance

**Prior authorization / UM nurse review (physical therapy, cardiac imaging, etc.)**
- Look up the case, the member, the plan, the requested CPT codes, and the active policy criteria.
- Compare clinical documents against each criterion. Mark criteria as `met` when the document evidence satisfies the policy requirement; `not_met` when it does not; `unclear` when the record is insufficient.
- Exclude stale documents (e.g., an older export that has been superseded by a current evaluation).
- The `authorization` object should reflect approved units, date range, CPT codes, and modifiers from the case and plan records.

**Pharmacy appeals and manufacturer assistance**
- Retrieve the appeal record, the drug, the denial, the prescriber rationale, and drug trial/failure records.
- Separate documented step-therapy failures from undocumented or insufficient failures using the trial records in the environment.
- For manufacturer assistance, check the assistance program records for eligibility, status, and missing fields.
- Required packet items combine payer appeal requirements and manufacturer assistance requirements; missing items are those not yet in the file.

**Payment integrity / claim repricing**
- Identify the current effective benchmark (rate schedule) by matching the plan, CPT codes, modifiers, and the effective date.
- Reject stale rate sources that are superseded by a current schedule.
- Compute correct allowed amounts per line by applying the current benchmark rate × units; then derive recovery amounts (paid minus correct allowed, or correct minus paid for underpayments).

**Peer-to-peer (P2P) final summary**
- Review the P2P event outcome, the clinical documents, and the policy criteria.
- Mark criteria that were not satisfied despite the P2P discussion as unresolved.
- If the P2P supplied new patient-specific information that changed the review, set `new_information_changed_review` to true; otherwise false.
- List PET-over-SPECT factors that remain unsupported.
- For adverse determinations, compute the internal appeal deadline using the plan's stated internal appeal window from the determination date.

**Margin / finance queue**
- Pull the service_margin rows identified by `queue_row_ids` in the task context.
- Compute `total_cost` as `variable_cost + fixed_cost_allocated` (or as defined in the finance memo).
- Compute `margin` as `revenue - total_cost`.
- Compute `revenue_to_cost_ratio` as `revenue / total_cost`, rounded to four decimal places.
- A row is `below_threshold` when its ratio is strictly less than the stated threshold.
- A row is `charge_sensitive` per the environment flag on the row.
- The `top_issue` is the below-threshold row with the largest dollar gap to the threshold; if none, use `"none"`.
- `gap_to_120pct` is `(threshold_ratio × total_cost) - revenue` for the top below-threshold issue.
- `below_threshold_segments` and `charge_sensitive_segments` aggregate payer segments from the rows, sorted alphabetically.

### Output rules

- Return **only** a single JSON object. No markdown fences, no prose, no commentary.
- Match every required key from the answer template exactly.
- Use the enumerations, ordering rules, precision rules, and null-handling rules stated in the template.
- Include `basis_audit` with all four required keys on every answer.
