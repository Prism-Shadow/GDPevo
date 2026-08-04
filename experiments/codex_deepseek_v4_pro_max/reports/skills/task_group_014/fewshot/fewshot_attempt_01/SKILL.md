---
name: northstar-payer-ops
description: Complete Northstar Health Plan payer operations tasks. Use when the task involves prior authorization review, pharmacy appeals, payment integrity claim repricing, peer-to-peer summaries, or therapy margin queues in the Northstar environment. The skill covers environment access, evidence gathering, criteria evaluation, and structured JSON answer construction.
---

# Northstar Payer Operations Skill

## When to Use

Activate this skill when the user asks you to complete a Northstar Health Plan payer operations work item. Typical task types include:

- UM nurse prior authorization determination summaries
- Pharmacy coverage appeal and manufacturer assistance intake dispositions
- Payment integrity claim repricing correction packets
- Peer-to-peer (P2P) final determination summaries
- UM-finance therapy margin queue summaries

## Input Structure

Every Northstar task is delivered as a directory containing:

| File | Purpose |
|------|---------|
| `prompt.txt` | Natural-language work order describing the task, target case/claim/queue, and expected output |
| `payloads/task_context.json` | Structured metadata: task ID, target business ID, requester role, reporting date, environment config, and domain-specific memos |
| `payloads/answer_template.json` | The required output JSON schema including field names, types, enum choices, ordering rules, and numeric precision constraints |

**Read all three files before making any environment calls.** The template defines the exact shape you must return. The context provides the target identifiers and business parameters. The prompt explains the operational goal.

## Environment Access

Northstar tasks target a shared payer-operations environment accessed over HTTP. The connection details appear in the task context under `environment` or `environment_access`.

### Base URL

The base URL is provided as `<TASK_ENV_BASE_URL>` in the prompt and context. Resolve this placeholder from the `environment_access.md` file in the workspace root, or from the environment variable `TASK_ENV_BASE_URL` if set.

### SQL Endpoint

| Property | Value |
|----------|-------|
| Method | `POST /sql/query` |
| Content-Type | `application/json` |
| Authorization | `Bearer pa-review-token-014` |
| Body | `{"sql": "<SELECT/WITH/PRAGMA table_info only>", "params": []}` |

**SQL constraints:**
- Only `SELECT`, `WITH`, and `PRAGMA table_info` statements are allowed
- No `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or `CREATE`
- Use parameterized queries with the `params` array when needed

### REST Business Endpoints

The environment exposes these GET endpoints:

| Endpoint | Use |
|----------|-----|
| `GET /` | Health check / root |
| `GET /portal` | Operational portal overview |
| `GET /api/tables` | List available data tables |
| `GET /api/cases` | List all cases |
| `GET /api/cases/{case_id}` | Fetch a specific case with member, plan, and request-line context |
| `GET /api/policies` | List all policies |
| `GET /api/policies/{policy_id}` | Fetch a specific policy with criteria text |
| `GET /api/documents/{document_id}` | Fetch a clinical or operational document |
| `GET /api/rate-schedules` | List available rate schedules |
| `GET /api/appeals` | List all appeals |

### Connection Pattern

```
1. Verify connectivity: curl -sS "{{BASE_URL}}/"
2. Explore schema: POST /sql/query with "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
3. Inspect tables: POST /sql/query with "PRAGMA table_info('table_name')"
4. Query data: POST /sql/query with SELECT statements
5. Supplement with REST endpoints for cases, policies, documents, etc.
```

## Workflow

### Phase 1: Orient

1. Read `prompt.txt` to understand the task type and target business object.
2. Read `payloads/task_context.json` to extract the target identifier, reporting date, and any domain-specific memos (e.g., `finance_memo`, `local_memo`, `work_item`).
3. Read `payloads/answer_template.json` to memorize every required field, enum choice, ordering rule, and precision constraint.

### Phase 2: Explore the Environment

1. **List all tables** via `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`.
2. **Inspect relevant table schemas** via `PRAGMA table_info('table_name')` for any table that sounds related to the task domain (cases, claims, appeals, documents, policies, rate schedules, service margins, etc.).
3. **Fetch the target record** using the business ID from the task context. Query the table(s) most likely to hold that record.
4. **Expand to related records**: once you find the target, trace foreign keys and relationships to gather all connected data (member info, plan info, request lines, clinical documents, policy criteria, rate schedules, appeal records, etc.).

### Phase 3: Gather Evidence

For each relevant entity discovered in Phase 2, collect the full record:

- **Cases**: member demographics, group/plan, service domain, request lines with CPT/modifier/units, diagnosis codes, authorization status
- **Policies**: criteria IDs, criteria text, coverage rules, medical-necessity requirements
- **Documents**: document type, date, clinical content, staleness indicators
- **Rate Schedules**: schedule name, version/effective date, CPT-to-allowable mappings, modifiers
- **Appeals**: appeal ID, path, deadline, expedited flag, related case, determination history
- **Claims**: claim lines with CPT/modifier/units/paid amounts, authorization reference
- **Service Margins**: payer segment, CPT, cost components, revenue, margin metrics

Use REST endpoints (`/api/cases/{case_id}`, `/api/policies/{policy_id}`, `/api/documents/{document_id}`, `/api/appeals`, `/api/rate-schedules`) as primary sources when available. Use SQL as the fallback or for cross-entity joins.

### Phase 4: Apply Business Rules

**Criteria Evaluation:**
- Map each criterion key from `answer_template.json` fields (e.g., `criteria_results` required keys) to the policy text and clinical evidence.
- For each criterion, determine: `met`, `not_met`, `partial`, `unclear`, or `not_applicable`.
- A criterion is `met` when clinical evidence explicitly satisfies the policy requirement.
- A criterion is `not_met` when evidence is absent or contradicts the requirement.
- Use `unclear` when the evidence is ambiguous or insufficient to decide.

**Document Classification:**
- **Evidence documents**: current, clinically relevant records that directly support the determination. Exclude stale, superseded, or out-of-scope records.
- **Excluded documents**: stale exports, expired records, documents from superseded time windows, or records not applicable to the current review period.

**Staleness Detection:**
- Compare document dates against the reporting date from task context.
- Flag documents with version indicators like "stale", "legacy", "old", or dates outside the current effective window.
- For rate schedules, prefer the most recent version that is effective as of the reporting date.

**Determination Logic (task-type specific):**

*UM Prior Authorization:*
- All criteria met + no exclusions → approve (route: `nurse_approval`)
- Missing information → pend (route: `pending_information`)
- Criteria not met or clinical gap → escalate to MD or deny
- Authorization details (units, dates, CPTs) come from the policy-allowed parameters applied to the request

*Pharmacy Appeals:*
- Classify medication trial failures as `documented_failures` (sufficient evidence of trial + failure) vs `undocumented_or_insufficient_failures` (missing records or insufficient trial)
- Appeal path depends on denial type and timeframe
- Appeal deadline: typically 60 calendar days from denial for standard internal, calculated from the denial notice date
- Manufacturer assistance eligibility depends on documented denial + income verification

*Payment Integrity Claim Repricing:*
- Identify the applicable benchmark (rate schedule) by matching CPT, modifier, plan type, and effective date
- Reject stale schedules: if multiple schedules exist for the same code, use the one effective as of the service/claim date
- Calculate `correct_allowed_amount` = benchmark rate × units
- `recovery_amount` = `correct_allowed_amount` - `paid_amount` (positive = underpayment to recover to provider; negative = overpayment)
- Disposition per line: `correct_upward` (underpaid), `correct_downward` (overpaid), or `match` (correct)

*P2P Summaries:*
- A P2P discussion outcome is either `overturn_to_approval` (MD changes decision) or `uphold_intended_adverse_decision` (MD maintains denial)
- `new_information_changed_review`: true only when the P2P introduced new patient-specific clinical information that materially altered the analysis
- Unresolved criteria are those that remain `not_met` or `unclear` after the P2P
- Internal appeal deadline: 180 calendar days from the final adverse determination date (when plan rules specify 180-day window)

*Therapy Margin Queue:*
- `below_threshold`: true when `revenue_to_cost_ratio < threshold_revenue_to_cost_ratio`
- `charge_sensitive`: true when `margin > 0` AND `revenue_to_cost_ratio > threshold` (the service is profitable but the ratio is high enough to warrant monitoring)
- `top_issue`: the below-threshold row with the largest absolute dollar gap, formatted as `{segment}_{cpt}`
- `gap_to_120pct`: `(total_cost × threshold) - (total_cost + margin)` for the top issue, i.e., the dollar amount needed to reach the threshold ratio

### Phase 5: Construct the Answer

**General Rules:**
- Return exactly one JSON object. No markdown, no prose outside the JSON.
- Follow every ordering rule specified in the template (ascending, alphabetical, operational order, claim-line order, etc.).
- Use the exact field names, enum values, and types from the template.
- Round numeric values to the precision specified (USD to 2 decimal places, ratios to 4 decimal places).
- Use `null` for absent modifiers or inapplicable fields where the template allows.

**Basis Audit Construction:**

Every Northstar answer includes a `basis_audit` object with four required keys:

| Key | Purpose |
|-----|---------|
| `source_precedence` | The precedence rule that governed this determination (choose from the template's `source_precedence` enum) |
| `controlling_record_ids` | Environment record IDs that directly control the result (the records whose data drove the determination) |
| `exception_record_ids` | Records that explain gaps, exclusions, denials, missing information, or route priority |
| `precedence_record_order` | All controlling + exception records ordered by source precedence priority, highest first |

**Choosing `source_precedence`:**

| Precedence Rule | When to Use |
|-----------------|-------------|
| `current_clinical_records_over_stale_export` | UM auth review where current clinical documents override stale/legacy exports |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeals where the payer appeal process takes priority over manufacturer copay assistance |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity where the effective rate schedule is selected by plan type, modifier, and effective date |
| `new_patient_specific_p2p_information` | P2P where the peer-to-peer discussion introduces new patient-specific information that may override the initial review |
| `margin_threshold_then_charge_sensitivity` | Finance queue where below-threshold issues are prioritized over charge-sensitivity flags |
| `appeal_deadline_then_clinical_then_payment_integrity` | Complex cases where appeal deadlines, clinical evidence, and payment integrity concerns stack |

**Ordering Rules for `precedence_record_order`:**
- Controlling records come before exception records (highest priority first)
- Within controlling records: use the operational evidence order (e.g., case → clinical documents → P2P event)
- Exception records follow business gap order: criteria/route gaps before stale/excluded records

**Ordering Rules for `controlling_record_ids`:**
- List records in the order they were relied upon to reach the determination
- Include case/claim/queue identifiers, document IDs, appeal IDs, policy IDs, benchmark IDs, etc.

**Ordering Rules for `exception_record_ids`:**
- Criteria or route gaps first (unresolved criteria, missing packet items)
- Then stale or excluded records (documents, schedules)
- Then missing information items (using their field names or identifiers)

## Common Pitfalls

1. **Skipping schema exploration**: always inspect table schemas with `PRAGMA table_info` before querying. Column names vary across task types.
2. **Ignoring stale records**: the environment may contain outdated documents or rate schedules. Always check dates and version indicators.
3. **Wrong source_precedence**: select the precedence rule that best describes the business logic governing the determination, not an arbitrary choice.
4. **Missing exception records**: include not just stale documents but also unresolved criteria IDs, missing packet items, and information gaps.
5. **Numeric precision**: follow the template's precision rules exactly. Ratios use 4 decimal places; currency uses 2.
6. **Ordering violations**: the template specifies ordering for lists. Follow it exactly (ascending IDs, alphabetical, operational order, etc.).
7. **Returning prose**: the output must be pure JSON. No markdown fences, no explanations, no comments.
8. **Misclassifying evidence vs excluded documents**: a document is "evidence" only if it is current and directly supports the determination. Stale, superseded, or tangential documents go in `excluded_documents`.
9. **Incorrect appeal deadline calculation**: verify the plan's internal appeal window (commonly 180 days from final adverse determination for P2P/PET, or 60 days from denial notice for pharmacy) before computing the date.
10. **Not reading the full template**: the `answer_template.json` contains critical ordering rules, precision specs, and enum choices embedded in field descriptions. Read every field definition.
