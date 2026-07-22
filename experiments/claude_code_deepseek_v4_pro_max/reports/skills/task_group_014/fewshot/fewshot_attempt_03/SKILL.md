# Northstar Payer Operations Skill

Complete structured prior authorization, appeal, payment integrity, and finance-margin tasks against the Northstar Health Plan shared payer operations environment. For every task, follow the workflow below; return JSON only (no markdown, prose, or commentary outside the JSON object).

---

## 1. Read the Inputs

Read all three task inputs before touching the environment:

| Input | Location | Purpose |
|-------|----------|---------|
| Prompt | `prompt.txt` | Business problem, target ID, role, reporting date, deliverables |
| Task context | `payloads/task_context.json` | Structured metadata: case/claim/queue IDs, dates, domain, review scope |
| Answer template | `payloads/answer_template.json` | Required JSON shape — top-level keys, field types, enums, ordering rules, optional fields flag |

From the prompt and task context, extract:
- **Target business ID** (case_id, claim_id, appeal_id, or queue)
- **Requester role** (UM nurse, pharmacy appeals coordinator, payment integrity analyst, P2P coordinator, UM-finance analyst)
- **Reporting date** or **reporting period**
- **Service domain** (physical_therapy, pharmacy, cardiac_imaging)
- **Work type** (determination, appeal disposition, claim repricing, P2P summary, margin queue)

---

## 2. Access the Environment

### Base URL and Credentials

Resolve `<TASK_ENV_BASE_URL>` from the task prompt or task context. The SQL endpoint uses bearer authentication:

```
POST {base_url}/sql/query
Authorization: Bearer pa-review-token-014
Content-Type: application/json
Body: {"query": "<SQL statement>"}
```

### Business REST Endpoints (GET only)

| Endpoint | Use |
|----------|-----|
| `GET /` | Environment root / health |
| `GET /portal` | Plan portal landing data |
| `GET /api/tables` | List available data tables |
| `GET /api/cases` | List all cases |
| `GET /api/cases/{case_id}` | Case detail, status, lines, member and plan context |
| `GET /api/policies` | List all policies |
| `GET /api/policies/{policy_id}` | Policy criteria, indications, coverage rules |
| `GET /api/documents/{document_id}` | Clinical documents, prior auth letters, denial notices |
| `GET /api/rate-schedules` | Rate/benchmark schedules for repricing |
| `GET /api/appeals` | Appeal records, routing, deadlines, outcomes |

### SQL Query Patterns

Use POST `/sql/query` for records not surfaced by the REST endpoints. Common query patterns observed across tasks:

- **Case lines / request items**: Query for service lines, CPT codes, units, modifiers attached to a case
- **Member / plan context**: Query for member eligibility, plan type, benefit year
- **Clinical evidence documents**: Query documents by case, type, date
- **Prior medication / drug trial records**: Query fill history, trial attempts, outcomes
- **Policy criteria details**: Query criteria codes, requirements, thresholds
- **Rate / benchmark data**: Query rates by CPT, modifier, effective date range
- **Claim lines and payments**: Query claim lines, paid amounts, authorization references
- **P2P events**: Query peer-to-peer discussion records, outcomes
- **Appeal records**: Query by case, appeal ID, filing date, status
- **Service margin rows**: Query by month, payer segment, CPT, cost and revenue fields

Always prefer the REST endpoints first; fall back to SQL only when the needed data is not available through REST.

---

## 3. Collect and Cross-Reference Evidence

For every task type, collect these categories of evidence and cross-reference them:

### 3a. Identify the Controlling Evidence Sources

| Task type | Primary sources |
|-----------|----------------|
| UM prior authorization | Case record, clinical documents (eval, POC), authorizations, policy criteria |
| Pharmacy appeal | Appeal record, case, drug trial evidence, denial notice, policy criteria |
| Payment integrity / repricing | Claim record, claim lines, rate/benchmark schedules (current vs. stale), authorization |
| Peer-to-peer | Case record, P2P event, clinical documents, policy criteria |
| Finance margin queue | Service margin rows by payer segment, CPT, cost, revenue |

### 3b. Evaluate Against Criteria or Requirements

- Map each applicable policy criterion ID to its result: `met`, `not_met`, `unclear`, `not_applicable` (or `partial` for drug criteria).
- For each criterion, cite the specific environment record(s) that support the result.
- Flag unresolved criteria explicitly — list their IDs.
- Identify stale, excluded, or missing records and document why they were excluded.

### 3c. Determine the Source Precedence Rule

Select exactly one from the six known precedence rules based on task type:

| Precedence rule | Applies when |
|-----------------|--------------|
| `current_clinical_records_over_stale_export` | UM clinical determination — current eval/POC documents override stale exports |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal — appeal evidence takes priority over manufacturer assistance screening |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity — current rate schedule by plan, modifier, and effective date overrides stale benchmarks |
| `new_patient_specific_p2p_information` | Peer-to-peer — new clinical information from the P2P discussion controls the final determination |
| `margin_threshold_then_charge_sensitivity` | Finance margin queue — classify below-threshold rows first, then flag charge-sensitive rows |
| `appeal_deadline_then_clinical_then_payment_integrity` | Cross-domain appeals — deadline urgency controls, then clinical merit, then payment integrity concerns |

---

## 4. Construct the Answer JSON

### 4a. Follow the Template Exactly

- Include every `required_top_level_field`.
- Match enum values precisely (case-sensitive).
- Order list items as specified by each field's ordering rule.
- Apply numeric precision rules: currency to 2 decimal places, ratios to 4 decimal places.
- Use `null` for absent modifiers (never empty string).
- Dates in `YYYY-MM-DD` format.
- CPT codes in ascending order.

### 4b. Build the basis_audit Object

Every answer must include:

```json
"basis_audit": {
  "source_precedence": "<one of the six rules>",
  "controlling_record_ids": ["<records that directly control the result>"],
  "exception_record_ids": ["<gaps, exclusions, stale records, missing information>"],
  "precedence_record_order": ["<controlling and exception records in priority order>"]
}
```

**controlling_record_ids** ordering rule: Use the operational evidence order — records that directly determine the outcome appear first.

**exception_record_ids** ordering rule: Criteria or route gaps before stale or excluded records when both appear.

**precedence_record_order** ordering rule: List the union of controlling and exception records in source-precedence order, highest priority first. A record may appear in both controlling_record_ids and exception_record_ids if it controls one part of the result but is also gapped for another.

### 4c. Validate Before Returning

- Does the JSON parse?
- Are all required top-level keys present?
- Do all enum values match the template's allowed choices?
- Are lists ordered per the template's ordering rules?
- Are currency values rounded to cents?
- Is `basis_audit` complete with all required keys?
- Are all record IDs legitimate environment record identifiers (not invented)?

---

## 5. Return the Answer

Return only the JSON object. No markdown fences, no prose, no commentary. The answer must be a single valid JSON object.
