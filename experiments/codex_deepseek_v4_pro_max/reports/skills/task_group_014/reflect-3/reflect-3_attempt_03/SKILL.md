 # Northstar Payer Operations Skill

## Purpose

Solve structured payer-operations tasks (utilization management, appeals, payment integrity, peer-to-peer, and margin analysis) against the Northstar Health Plan shared environment. Every task requires querying a read-only environment through business endpoints and SQL, then returning a JSON answer that exactly conforms to a supplied answer template.

## Environment

The task provides a base URL (`<TASK_ENV_BASE_URL>`) to a shared payer-operations environment. Two access methods are available:

### Business REST Endpoints (GET)

- `GET /` — portal
- `GET /portal`
- `GET /api/tables`
- `GET /api/cases`
- `GET /api/cases/{case_id}`
- `GET /api/policies`
- `GET /api/policies/{policy_id}`
- `GET /api/documents/{document_id}`
- `GET /api/rate-schedules`
- `GET /api/appeals`

### SQL Endpoint

```
POST /sql/query
Content-Type: application/json
Authorization: Bearer pa-review-token-014
```

Body: `{"sql": "<SELECT | WITH | PRAGMA table_info only>", "params": []}`

Allowed SQL: `SELECT`, `WITH`, and `PRAGMA table_info(...)`. No INSERT, UPDATE, DELETE, DDL, or schema writes.

Row limit: 500 rows per query. Use targeted WHERE clauses.

## Workflow

### Step 1 — Read the Task Inputs

Every task has three files:

- `prompt.txt` — natural-language task description identifying the target business object and role
- `payloads/task_context.json` — structured context: task_id, target IDs, reporting date, environment details, local memos
- `payloads/answer_template.json` — the exact JSON shape to return, with required fields, enums, and precision rules

Read all three before querying anything. The answer template is authoritative for output shape.

### Step 2 — Explore the Schema

Start by listing all tables:

```
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name
```

Then inspect the columns of every table that could be relevant to the task domain using:

```
PRAGMA table_info('table_name')
```

Common tables across domains:

| Table | Domain |
|---|---|
| cases | All domains — central case record |
| members | Member demographics and plan |
| plans | Plan details |
| providers | Provider info |
| request_lines | Authorization/service request lines |
| documents | Clinical and administrative documents |
| document_facts | Structured facts extracted from documents |
| policies | Policy metadata and versions |
| policy_criteria | Criteria definitions per policy |
| case_criteria | Criteria evaluation results per case |
| authorizations | Authorization records |
| claims | Claim headers |
| claim_lines | Individual claim lines |
| payment_benchmarks | Rate benchmarks for repricing |
| appeals | Appeal records |
| drug_trials | Medication trial history |
| assistance_screen | Manufacturer assistance program screens |
| p2p_events | Peer-to-peer discussion records |
| service_margin | Service margin analytics rows |

### Step 3 — Gather Task Data

Use the target business ID from `task_context.json` (e.g., `case_id`, `claim_id`, `appeal_id`) to filter queries. Query every table that can contribute controlling evidence to the determination.

For case-driven tasks, gather:
- The case row itself
- The member and plan
- Request lines
- All documents (both current and non-current)
- Document facts
- Policy criteria definitions
- Case criteria results
- Authorization records
- Any domain-specific records (appeals, drug trials, P2P events, claims, benchmarks, assistance screens)

### Step 4 — Evaluate Evidence

Each task domain has specific evaluation rules. Apply these consistently:

**Current vs. Stale Records:** Documents with `is_current = 0` are stale and must not control the result. Use `source_precedence: "current_clinical_records_over_stale_export"` when stale records exist. List current documents in `evidence_documents` and stale ones in `excluded_documents`.

**Criteria Evaluation:** Map each criterion from `policy_criteria` to its result in `case_criteria`. Results are one of: `met`, `not_met`, `partial`, `unclear`, `not_applicable`. A `not_met` criterion that hasn't been resolved by a P2P or appeal is still "unresolved" — include its ID in any `unresolved_criteria` list.

**Benchmark Repricing:** When a claim was priced against a stale schedule, find the current effective schedule using the service date, plan type, CPT code, and modifier. Reject the stale source explicitly in `stale_source_rejected`. Compute line-level and total corrections using the current benchmark's allowed amounts.

**P2P Events:** The P2P outcome (`uphold_intended_adverse_decision` or `overturn_to_approval`) combined with `new_information` determines whether the review changed. If no new patient-specific information was supplied, `new_information_changed_review` is `false`.

**Appeal Deadlines:** When an internal appeal deadline is needed, calculate it from the final adverse determination date using the plan's stated appeal window (e.g., 180 days). Use ISO 8601 `YYYY-MM-DD`.

**Margin Analysis:** For service_margin rows, `total_cost = variable_cost + fixed_cost_allocated`. `margin = net_revenue - total_cost`. `revenue_to_cost_ratio = net_revenue / total_cost`. Compare against the threshold ratio; rows below the threshold need contract review. Rows flagged `charge_sensitive = 1` need charge-sensitivity monitoring regardless of threshold status.

### Step 5 — Build the Basis Audit Trail

Every answer requires a `basis_audit` object with four keys:

| Key | Purpose |
|---|---|
| `source_precedence` | The precedence rule that governed the determination (see choices below) |
| `controlling_record_ids` | Environment record IDs that directly control the result, in operational evidence order |
| `exception_record_ids` | Records explaining gaps, exclusions, denials, or missing information. Order: criteria/route gaps before stale/excluded records |
| `precedence_record_order` | All controlling and exception records in source-precedence order, highest priority first |

**Source precedence choices:**

- `current_clinical_records_over_stale_export` — when current documents override a stale export
- `payer_appeal_before_manufacturer_assistance` — when appeal processing precedes assistance screening
- `effective_benchmark_by_plan_modifier_and_date` — when the effective rate schedule is chosen by plan type, modifier, and date
- `new_patient_specific_p2p_information` — when a P2P discussion outcome controls the result
- `margin_threshold_then_charge_sensitivity` — when margin analysis separates below-threshold issues from charge-sensitive monitoring
- `appeal_deadline_then_clinical_then_payment_integrity` — when appeal timeline, then clinical evidence, then payment facts control

### Step 6 — Assemble the Answer

Build a JSON object that matches `answer_template.json` exactly:

1. Include every `required_top_level_key`.
2. Use only the specified enum values — no invented values.
3. String fields must use exact case and format.
4. Numeric values must follow stated precision (e.g., two decimal places for USD, four decimal places for ratios).
5. Lists must follow stated ordering rules (alphabetical, claim-line order, operational packet order, etc.).
6. Use `null` for absent modifiers and `[]` for empty lists when appropriate.
7. Dates must be ISO 8601 `YYYY-MM-DD`.
8. Do not include extra top-level keys beyond those listed as required.
9. Return JSON only — no markdown, no prose, no comments.

## Domain-Specific Patterns

### UM Nurse Determination (Prior Authorization)

- Evaluate each policy criterion against case criteria results.
- Current documents with `is_current = 1` are evidence; documents with `is_current = 0` are excluded.
- Recommendation maps to: all criteria met → `approve`; any missing → `pend_for_information`; any not_met with result_if_missing=deny → `deny`.
- Final status, route, and determination letter must be consistent with the recommendation.

### Pharmacy Appeals

- Required packet items include payer appeal items (denial notice, member authorization, prescriber rationale, formulary failure evidence) before assistance items (household income proof).
- Missing packet items: appeal evidence gaps before assistance information gaps.
- Documented failures: drug trials with `documented = 1` and meaningful outcomes. Undocumented/insufficient: trials with `documented = 0` or insufficient evidence.
- Assistance status: `eligible_ready` when all fields present; `eligible_missing_information` when fields are missing.

### Payment Integrity (Claim Repricing)

- Find all benchmarks for the claim's service domain, plan type, CPT, and modifier.
- Select the benchmark effective on the service date. A benchmark whose effective_end is before the service date is stale.
- Recompute each line's allowed amount using the current benchmark's allowed_amount × units.
- Recovery is positive for underpayments (correct > paid) and negative for overpayments.

### Peer-to-Peer Summaries

- Requested CPT comes from the request line.
- P2P outcome and final status come from the p2p_event record.
- Unresolved criteria are criterion IDs that remain `not_met` after the P2P — even though they've been evaluated, they represent unresolved gaps.
- Missing PET-over-SPECT factors:
  - `prior_equivocal_spect`
  - `bmi_limitation`
  - `attenuation_artifact`
  Include every factor from the policy that is unsupported by documentation.
- If the final determination is adverse and an internal appeal window applies, compute the deadline from the determination date plus the window days.

### Margin Queue Analysis

- For each queue row, compute: total_cost, margin, revenue_to_cost_ratio.
- `below_threshold` is `true` when revenue_to_cost_ratio < threshold.
- `charge_sensitive` matches the row's charge_sensitive flag.
- Recommended action:
  - `below_threshold && !charge_sensitive` → `payer_contract_review`
  - `!below_threshold && charge_sensitive` → `monitor_charge_sensitive`
  - `!below_threshold && !charge_sensitive` → `monitor_no_action`
- `below_threshold_segments` and `charge_sensitive_segments` list the payer segments alphabetically.
- `top_issue` is the `{segment}_{cpt}` of the row with the lowest revenue_to_cost_ratio among below-threshold rows.
- `gap_to_120pct` is `threshold × total_cost − net_revenue` for the top below-threshold issue, as a positive dollar amount.

## Common Pitfalls

- **Unresolved vs. Resolved Criteria:** A criterion that evaluated to `not_met` is still "resolved" in the sense that a determination was made, but it may appear in `unresolved_criteria` lists when the template uses that term to mean "criteria gaps that remain after review."
- **Stale Document Handling:** Always check `is_current` on documents. A stale document may appear in the case file but must never control the result.
- **Modifier Matching in Benchmarks:** Benchmarks with a modifier only apply to claim lines with that exact modifier. A null-modifier benchmark applies to null-modifier lines.
- **List Ordering:** Every list in the answer template has a stated ordering rule. Alphabetical means case-insensitive alphabetical; operational order means the business-logic order described in the template.
- **Numeric Precision:** Ratios use 4 decimal places (round half-up). Currency uses 2 decimal places. Do not exceed the stated precision.
- **Basis Audit IDs:** Use actual environment record IDs (document IDs, auth IDs, appeal IDs, benchmark IDs, month IDs, etc.) — not fabricated or inferred names.
