# Northstar Payer Operations — Structured Determination Skill

## Purpose

Produce a structured JSON determination for a Northstar Health Plan payer-operations task by querying the shared read-only environment. Every task follows the same flow: read the input dossier, navigate the environment to collect evidence, apply the correct source-precedence rule for the work type, and return one JSON object matching the supplied answer template.

## When to Use

Invoke this skill when the task:
- Mentions Northstar Health Plan, the shared payer operations environment, or `<TASK_ENV_BASE_URL>`.
- Involves utilization management (UM), prior authorization, appeals, payment integrity / claim repricing, peer-to-peer (P2P) closure, or finance-queue margin analysis.
- Supplies a `prompt.txt`, a `task_context.json` payload, and an `answer_template.json` schema.
- Requires an environment query via REST endpoints or `POST /sql/query`, and a structured JSON-only response.

## Environment

All tasks use the same read-only payer-operations environment.

### Base URL

```
<TASK_ENV_BASE_URL>
```

Resolve `<TASK_ENV_BASE_URL>` from `task_context.json` → `environment.base_url`, or from `environment_access.md` → `base_url`. The canonical training value is `http://task-env:9014/`.

### SQL Endpoint

```
POST /sql/query
```

**Headers:**
- `Authorization: Bearer pa-review-token-014`
- `Content-Type: application/json`

**Body:** `{"sql": "<query>"}`

The endpoint accepts standard SQL (SQLite dialect). All tables are read-only.

### Available REST Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Portal home page (HTML) |
| `GET /portal` | Same portal page |
| `GET /api/tables` | Full table catalog with column definitions |
| `GET /api/cases` | All cases (paginated) |
| `GET /api/cases/{case_id}` | Denormalized case with embedded criteria, authorizations, documents, claims, appeals, drug trials, assistance screen, request lines, members, and providers |
| `GET /api/policies` | All policies with criteria |
| `GET /api/policies/{policy_id}` | Single policy detail |
| `GET /api/documents/{document_id}` | Single document detail |
| `GET /api/rate-schedules` | All rate-schedule benchmarks |
| `GET /api/appeals` | All appeals |

**Prefer `/api/cases/{case_id}` for the target case.** It returns an enriched, denormalized view with embedded authorizations, criteria, documents, claims, request lines, drug trials, and member/provider data — often reducing the need for multiple SQL queries.

### Database Schema

Major tables (queryable via SQL):

| Table | Key columns | Purpose |
|---|---|---|
| `cases` | case_id, member_id, policy_id, request_type, service_domain, current_stage, current_status | Case master |
| `members` | member_id, patient_name, dob, plan_id, plan_type | Member demographics |
| `providers` | provider_id, provider_name, specialty, npi | Provider directory |
| `plans` | plan_id, payer_name, plan_type, state, network | Plan contracts |
| `policies` | policy_id, policy_name, version, precedence | Clinical / payment policies |
| `policy_criteria` | criterion_id, policy_id, criterion_key, approval_required, result_if_missing | Policy criteria definitions |
| `case_criteria` | case_id, criterion_id, result, evidence_fact_ids, gap_description | Criteria results per case |
| `authorizations` | auth_id, case_id, auth_number, status, approved_units, approved_cpt | Authorization records |
| `request_lines` | line_id, case_id, cpt_code, modifier, requested_units, diagnosis_codes | Requested service lines |
| `documents` | document_id, case_id, document_type, is_current, source_system | Clinical / admin documents |
| `document_facts` | fact_id, document_id, case_id, fact_key, fact_value, supports_criteria | Extracted document facts |
| `drug_trials` | trial_id, case_id, medication, outcome, documented | Medication trial history |
| `appeals` | appeal_id, case_id, denial_date, appeal_path, expedited_attestation, outcome | Appeal records |
| `claims` | claim_id, case_id, payer, auth_number, paid_total | Claim master |
| `claim_lines` | claim_line_id, claim_id, cpt_code, modifier, units, paid_amount | Claim line detail |
| `payment_benchmarks` | benchmark_id, payer, plan_type, cpt_code, modifier, allowed_amount, source_name, source_version | Rate benchmarks |
| `p2p_events` | p2p_id, case_id, provider_argument, new_information, outcome, final_status | Peer-to-peer events |
| `assistance_screen` | case_id, program_name, income_percent_fpl, assistance_status, missing_fields | Manufacturer assistance |
| `service_margin` | month_id, period, payer_segment, cpt_code, net_revenue, variable_cost, fixed_cost_allocated, charge_sensitive | Finance margin data |

## Input Dossier

Every task provides three files inside `input/`:

### 1. `prompt.txt`

The natural-language task description. It names:
- The business role (UM nurse, pharmacy appeals coordinator, payment integrity analyst, P2P coordinator, UM-finance analyst).
- The target identifier (case, appeal, claim, or queue ID).
- The expected output reference (`input/payloads/answer_template.json`).
- Any special rules (e.g., "do not inspect construction files directly").

### 2. `payloads/task_context.json`

Structured metadata. Key fields:

| Field | Meaning |
|---|---|
| `task_id` | Task identifier |
| `target_business_id` / `business_id` / `target.claim_id` | The primary lookup key |
| `target_appeal_id` | Appeal ID when present |
| `requester_role` | Who is asking |
| `reporting_date` / `request_date` | As-of date for the determination |
| `environment` | Base URL, SQL endpoint, bearer token |
| `local_memo` / `finance_memo` | Business rules, definitions, threshold values, row-IDs |
| `work_item` / `work_type` | Describes the work type |

**Always read `task_context.json` first** — it tells you the target ID(s), the as-of date, and any business rules (thresholds, definitions, row-IDs, deadlines) that the answer template alone does not convey.

### 3. `payloads/answer_template.json`

The required output schema. It specifies:
- `required_top_level_fields` — every key that must appear.
- Per-field types, enum choices, ordering rules, and precision.
- `basis_audit` — always required with `source_precedence`, `precedence_record_order`, `controlling_record_ids`, `exception_record_ids`.

**Never add fields not listed unless `additional_fields_allowed` is explicitly true.** The template's `required_top_level_fields` is authoritative.

## Workflow

### Step 1 — Orient

1. Read `prompt.txt` to understand the business ask.
2. Read `payloads/task_context.json` to extract the target ID, as-of date, requester role, and any finance/clinical business rules.
3. Read `payloads/answer_template.json` to internalize the output shape, enums, ordering rules, and precision requirements.

### Step 2 — Collect Evidence

Gather all relevant data from the environment:

1. **Start with the denormalized case endpoint:** `GET /api/cases/{target_id}`. This often returns the case, member, provider, criteria results, authorization records, documents, claims, appeals, drug trials, and assistance screen in one call.
2. **Fill gaps with SQL.** Use `POST /sql/query` when you need:
   - Cross-table joins (e.g., claim lines joined to benchmarks).
   - Filtered lookups (e.g., rate schedules matching a specific CPT/modifier/plan/date).
   - Aggregate queries (e.g., margin calculations).
   - Tables not embedded in the case response (e.g., `service_margin`, `payment_benchmarks`).
3. **Resolve references.** When a case references a `policy_id`, confirm the policy and its criteria via `/api/policies/{policy_id}` or SQL on `policy_criteria`.
4. **Check document currency.** Every document has an `is_current` flag (0 = stale, 1 = current). Stale documents must not control the determination.
5. **Check effective dates.** Rate benchmarks, policies, and plans have `effective_start`/`effective_end` ranges. Only records effective on the as-of date apply.

### Step 3 — Apply Source Precedence

Every determination uses exactly one source-precedence rule. Choose based on **work type**:

| Work type | Source precedence rule | Meaning |
|---|---|---|
| UM nurse prior-authorization review | `current_clinical_records_over_stale_export` | Current clinical documents (is_current=1) control; stale exports are excluded. |
| Pharmacy / drug coverage appeal | `payer_appeal_before_manufacturer_assistance` | Appeal evidence (denial, authorization, prescriber letter, formulary failure records) is primary; manufacturer assistance screening is secondary. |
| Payment integrity / claim repricing | `effective_benchmark_by_plan_modifier_and_date` | Use the benchmark whose effective date range covers the service date, matching plan type, CPT, and modifier. Reject stale schedules. |
| Peer-to-peer closure | `new_patient_specific_p2p_information` | The P2P event's new patient-specific information takes precedence over the pre-P2P review. |
| Finance margin / queue analysis | `margin_threshold_then_charge_sensitivity` | Revenue-to-cost ratio against the threshold is the primary signal; charge-sensitivity flag is the secondary signal. |

### Step 4 — Distinguish Controlling vs. Exception Records

For every `basis_audit`:

- **Controlling records** are the environment records (document IDs, auth IDs, benchmark IDs, P2P IDs, policy IDs, criteria IDs, margin row IDs) that **directly determine** the result.
- **Exception records** are records that explain **exclusions, gaps, denials, missing information, or route priority** — stale documents, missing criteria, incomplete packets, distractor records.

**Ordering rule for `precedence_record_order`:** controlling records first, then exception records, reflecting the source-precedence priority (highest-priority record first).

**Ordering rule for `exception_record_ids`:** criteria/route gaps before stale or excluded records when both appear.

### Step 5 — Apply Precision and Formatting Rules

1. **Currency:** All dollar amounts as JSON numbers rounded to 2 decimal places.
2. **Dates:** ISO 8601 `YYYY-MM-DD` format. Use `null` only when the template explicitly allows it (e.g., "Use null only when no internal appeal deadline applies").
3. **Modifiers on claim lines:** Use `null` (not empty string) when no modifier is present.
4. **Lists:** Follow the ordering rule stated in the answer template for each list field (ascending ID, alphabetical, claim-line order, operational packet order, etc.).
5. **Enums:** Use exactly the string values listed in each field's `choices` array. Do not invent or approximate.
6. **Units:** `approved_units` and claim-line `units` are integers.

### Step 6 — Return JSON Only

- Return exactly one JSON object.
- No markdown fences, no prose, no comments outside the JSON.
- Every key in `required_top_level_fields` must be present.
- No keys beyond those listed, unless `additional_fields_allowed` or `additional_properties` is explicitly true.

## Data-Quality Rules

- **is_current flag:** Documents with `is_current = 0` are stale. They appear in `excluded_documents` / `exception_record_ids`, never in controlling evidence.
- **Effective date windows:** A benchmark, policy, or plan whose `effective_end` is before the service/as-of date, or whose `effective_start` is after it, does not apply.
- **Distractor records:** The environment may contain records with similar but non-matching identifiers (e.g., `CASE-D-*` prefix, unrelated CPTs, different service domains). Query by exact target ID. If a record with a different ID surfaces, verify relevance before using it.
- **SQL parameterization:** Always use the exact target ID, date, and business keys from `task_context.json`. Never hardcode values from the training examples.
- **Null handling:** `null` in JSON means absent. Use it only where the answer template explicitly permits it (modifiers, appeal deadline when not applicable). Do not use empty strings or `"none"` unless those are listed enum choices.

## Common Patterns by Work Type

### Prior Authorization (UM Nurse Review)

- Look up the case at `/api/cases/{case_id}`.
- Evaluate each criterion listed in `case_criteria` against the policy's required criteria.
- Current clinical documents (eval, plan of care) are controlling; stale exports are excluded.
- The authorization record (`authorizations` array) holds the recommended units, dates, CPTs.
- `criteria_results` map each relevant `criterion_id` to `met`/`not_met`/`unclear`/`not_applicable`.

### Pharmacy Appeal Disposition

- Look up the case and appeal records.
- Check `drug_trials` for documented vs. undocumented medication failures.
- Evaluate `case_criteria` against the drug policy (`POL-DRUG-EXC-*`).
- Check `assistance_screen` for manufacturer program eligibility.
- Required appeal packet items are listed in the drug policy; compare against documents on file.
- Missing items go in `missing_packet_items`.
- Source precedence: payer appeal evidence before manufacturer assistance.

### Payment Integrity / Claim Repricing

- Look up the claim and its claim lines.
- Query `payment_benchmarks` for the effective schedule matching the claim's payer, plan type, CPT, and modifier on the service date.
- Reject stale benchmarks (expired effective ranges, or `Legacy Imaging Export` source).
- Calculate `correct_allowed_amount` = benchmark's `allowed_amount` × units.
- `recovery_amount` = `paid_amount` − `correct_allowed_amount` (negative = underpayment).
- Line disposition: `correct_upward`, `correct_downward`, `no_change`, `deny_line`.

### Peer-to-Peer Closure

- Look up the case and the `p2p_events` record.
- The P2P `outcome` determines `p2p_outcome` (`overturn_to_approval` or `uphold_intended_adverse_decision`).
- `new_information_changed_review` is `true` only if the P2P record has `new_information` that materially altered the criteria evaluation.
- Unresolved criteria are those that remain `unclear` after the P2P.
- PET MPI: `missing_pet_factors` lists PET-over-SPECT factors (prior equivocal SPECT, BMI limitation, attenuation artifact) that remain unsupported.
- Internal appeal deadline (when adverse): `final_adverse_determination_date + 180 days`, per the plan's 180-day internal appeal window.

### Finance Margin Queue

- Query `service_margin` rows by the exact `month_id` values from `task_context.json` → `finance_memo.queue_row_ids`.
- `total_cost` = `variable_cost + fixed_cost_allocated` (or the definition given in `task_context.json`).
- `margin` = `net_revenue − total_cost`.
- `revenue_to_cost_ratio` = `net_revenue / total_cost`.
- `below_threshold` is `true` when `revenue_to_cost_ratio < threshold` (from task_context).
- `charge_sensitive` is `true` when the `charge_sensitive` column equals 1.
- Segregate below-threshold segments from charge-sensitive segments.
- `gap_to_120pct`: dollar gap = `(threshold × total_cost) − net_revenue` for the top below-threshold issue.

## Error Recovery

- If an endpoint returns `{"error": "not_found"}`, the target ID may need an alternate lookup path — try SQL or a different endpoint.
- If the SQL endpoint returns `{"error": "invalid_sql", "message": "sql must be a non-empty string"}`, the `sql` key (not `query`) is expected in the POST body.
- If a case endpoint returns unexpected fields, re-check the table catalog at `/api/tables` for the current schema.
- If distractor records appear, tighten the query with exact ID matching.

## Output Checklist

Before returning the JSON:

1. Every `required_top_level_field` is present.
2. Every enum value matches an allowed choice.
3. All currency values are rounded to 2 decimal places.
4. All dates are `YYYY-MM-DD`.
5. `null` is used only for explicitly nullable fields (modifiers, non-applicable deadlines).
6. Lists follow the stated ordering rule.
7. `basis_audit.source_precedence` matches the work type.
8. `basis_audit.precedence_record_order` lists controlling then exception records in priority order.
9. `basis_audit.controlling_record_ids` contains only records that directly determine the result.
10. `basis_audit.exception_record_ids` contains only gap/stale/excluded records.
11. No markdown, prose, or comments surround the JSON.
