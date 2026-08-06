# Northstar Health Plan Payer Operations Skill

## Purpose

Execute structured payer-operations tasks for Northstar Health Plan using the shared
payer-operations environment. Each task requires reading a task context, gathering
records from the environment, applying business rules, and returning a single JSON
object that conforms to a supplied answer template.

## When to Use

Invoke this skill when the task involves:
- A Northstar Health Plan business identifier (case, appeal, claim, queue, P2P event)
- A shared payer-operations environment accessed over HTTP
- A structured JSON output conforming to an `answer_template.json` schema
- A `task_context.json` payload with business parameters

## Input Files

Three input files are present for every task. Read all three before querying the
environment:

| File | Purpose |
|------|---------|
| `prompt.txt` | Natural-language task description, role, target, and deadline |
| `task_context.json` | Structured business parameters — target IDs, environment config, finance definitions, local memos |
| `answer_template.json` | Required output JSON schema with field definitions, enum choices, and ordering rules |

## Environment Access

The payer-operations environment is accessed exclusively over HTTP. Read
`environment_access.md` in the working directory (when present) for the base URL and
credentials. The task context may also carry an `environment` or `environment_access`
block with the same information.

### Endpoints

| Method | Path | Use |
|--------|------|-----|
| GET | `/` | Environment health / root |
| GET | `/portal` | Portal landing page |
| GET | `/api/tables` | List available database tables |
| GET | `/api/cases` | List case records |
| GET | `/api/cases/{case_id}` | Single case record |
| GET | `/api/policies` | List policy records |
| GET | `/api/policies/{policy_id}` | Single policy record |
| GET | `/api/documents/{document_id}` | Single clinical or administrative document |
| GET | `/api/rate-schedules` | List rate schedules |
| GET | `/api/appeals` | List appeal records |
| POST | `/sql/query` | Run a SQL query against the environment database |

### SQL Endpoint

```
POST {base_url}/sql/query
Authorization: Bearer {token}
Content-Type: application/json

{"query": "<SQL statement>"}
```

The token is supplied in `environment_access.md` as `sql_authorization_header` or in
the task context as `sql_bearer_token` / `authorization_header`. Use the SQL endpoint
for cross-entity queries and for retrieving records not exposed through a dedicated
REST endpoint.

### Rules

- **Never inspect local files** (SQLite databases, JSON fixtures, manifests, or
  setup scripts) — all data lives in the remote environment.
- **Use business endpoints first** for single-entity lookups (`/api/cases/{id}`,
  `/api/policies/{id}`, `/api/documents/{id}`); use SQL for joins, filtered lists,
  or cross-entity retrieval.
- **The `GET /api/tables` endpoint** returns the environment's table catalog — use
  it to discover table names and column schemas before writing SQL.

## Workflow

### Phase 1 — Orient

1. Read `prompt.txt` to understand the business question.
2. Read `task_context.json` to extract the target business ID, requester role,
   reporting date, and any domain-specific parameters (queue row IDs, cost
   definitions, thresholds, etc.).
3. Read `answer_template.json` to understand every required field, its type, its
   enum choices, and its ordering rules. Pay special attention to:
   - `required_top_level_keys` — every one must appear in the output.
   - `required_keys` inside nested objects.
   - Enum constraints and list ordering rules.
   - Numeric precision and date format requirements.

### Phase 2 — Gather Records

Query the environment for all records relevant to the target business ID. Typical
information needs include:

- **Case / claim / appeal record** — the primary entity.
- **Member and plan context** — who the member is, what plan they hold.
- **Requested service or therapy lines** — CPT codes, units, modifiers.
- **Policy or clinical criteria** — the applicable medical or pharmacy policy,
  including criterion IDs and their requirements.
- **Clinical documents** — evaluation notes, plans of care, imaging reports,
  specialist consults, trial/failure records.
- **Authorization records** — prior auth numbers, approved units, date ranges.
- **Rate schedules / benchmarks** — for payment integrity and repricing tasks.
- **P2P event records** — for peer-to-peer tasks.
- **Appeal records** — for coverage appeal tasks.
- **Margin / finance rows** — for queue-analysis tasks.

Use `GET /api/tables` to discover schema, then query with SQL where a dedicated
endpoint does not cover the need.

### Phase 3 — Apply Business Rules

Business rules are domain-specific. The sections below describe the rules for each
domain observed in training. Apply the rules that match the current task's service
domain.

#### Prior Authorization (Physical Therapy)

- Evaluate each criterion listed in the answer template's `criteria_results` required
  keys against the clinical evidence.
- Classify documents as **evidence** (directly support the determination) or
  **excluded** (stale, irrelevant, or superseded).
- Determine the authorization window (start/end dates) from the plan of care or
  policy.
- CPT codes and modifier come from the requested service line.
- The route follows from the recommendation: all criteria met → nurse_approval;
  criteria gaps → pend_for_information or escalate_to_md.

#### Pharmacy Coverage Appeal + Manufacturer Assistance

- Identify the drug from the case/appeal context.
- Classify prior medication trials into **documented failures** (evidence of trial
  and failure/intolerance exists) and **undocumented or insufficient failures**
  (mentioned but unsubstantiated).
- Evaluate drug-specific criteria (authorization, denial, rationale, failures)
  against the appeal and clinical records.
- Determine the appeal path (standard vs expedited) and compute the deadline from
  the appeal record's filed date plus the plan's appeal window.
- Build the packet: **required items** are the set the plan needs for the appeal
  and any assistance application; **missing items** are those absent from the
  environment records. Order appeal evidence gaps before assistance information gaps.
- Screen manufacturer assistance by checking the program's required fields against
  available member data.

#### Claim Repricing / Payment Integrity

- Retrieve the target claim and its claim lines (in claim-line order).
- Identify the applicable rate schedule by checking plan type, modifier, CPT code,
  and effective date — reject stale or legacy schedules.
- For each claim line, compute the correct allowed amount by applying the benchmark
  rate × units. Compare against the paid amount to determine the line disposition
  (`correct_upward`, `correct_downward`, `no_change`, `deny_line`).
- Sum paid totals, corrected totals, and recovery amounts across all lines.
- Currency values are in USD rounded to two decimal places.
- Use `null` (not empty string) for absent modifiers.

#### Peer-to-Peer (P2P) Final Summary

- Review the case, requested CPT, policy criteria, clinical evidence, and P2P event.
- Determine whether the P2P discussion brought **new patient-specific information**
  that materially changed the review.
- Classify the P2P outcome: `overturn_to_approval` (new information resolves prior
  concerns) or `uphold_intended_adverse_decision` (concerns remain unresolved).
- List any criteria that remain **unresolved** after the P2P.
- For PET MPI cases, identify which PET-over-SPECT factors (prior equivocal SPECT,
  BMI limitation, attenuation artifact) remain **unsupported/missing**.
- If the final determination is adverse, compute the **internal appeal deadline**
  as: final adverse determination date + 180 calendar days.
- Recommend an alternative modality when the requested service is denied.

#### Therapy Margin Queue

- Process only the queue row IDs listed in the task context.
- For each row, compute `total_cost` = variable_cost + fixed_cost_allocated.
- Compute `revenue_to_cost_ratio` = (total_cost + margin) / total_cost.
- Classify each row: `below_threshold` = true when revenue_to_cost_ratio < the
  threshold (default 1.2); `charge_sensitive` comes from the environment data.
- Recommend actions: rows below threshold → `payer_contract_review`; rows that
  are charge-sensitive but not below threshold → `monitor_charge_sensitive`;
  otherwise → `monitor_no_action`.
- Aggregate `below_threshold_segments` and `charge_sensitive_segments` from the
  classified rows, deduplicated and sorted alphabetically.
- The `top_issue` is the below-threshold row with the largest absolute gap; format
  as `{segment}_{cpt}`.
- `gap_to_120pct` = (total_cost × threshold) − (total_cost + margin) for the top
  issue, rounded to two decimal places. Use a positive value representing the
  shortfall.

### Phase 4 — Construct the Basis Audit

Every answer requires a `basis_audit` object with four keys. This is the structured
audit trail that explains *why* the result was reached.

#### source_precedence

Choose the single precedence rule that best describes the controlling business logic
for this task. The six available rules are:

| Rule | When to Use |
|------|-------------|
| `current_clinical_records_over_stale_export` | The determination relies on current environment clinical records while rejecting a stale or exported data source. Use when older documents or exports exist alongside fresher clinical data. |
| `payer_appeal_before_manufacturer_assistance` | The workflow processes payer-side appeal requirements before manufacturer assistance program screening. Use for pharmacy appeal + assistance tasks. |
| `effective_benchmark_by_plan_modifier_and_date` | The repricing uses the effective rate schedule selected by matching plan type, modifier, CPT code, and effective date — rejecting a stale schedule. Use for claim repricing / payment integrity tasks. |
| `new_patient_specific_p2p_information` | The P2P discussion is the decisive event — either it brought new patient-specific information that changed the review, or it confirmed the absence of such information. Use for P2P tasks. |
| `margin_threshold_then_charge_sensitivity` | Rows are evaluated first against the revenue-to-cost threshold; charge sensitivity is checked secondarily. Use for margin-queue tasks. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Priority ordering: appeal deadline urgency first, then clinical merit, then payment integrity concerns. Use for multi-factor appeal tasks. |

#### controlling_record_ids

The environment record IDs that **directly control** the result. These are the
records whose content drives the determination: the case or appeal record itself,
the clinical documents that satisfy criteria, the benchmark records that set rates,
the P2P event that resolves or confirms the outcome, and the queue rows that
determine margin classifications.

List them in the order defined by the answer template's `ordering_rule` for this
field — typically the operational evidence order.

#### exception_record_ids

Records that explain **exclusions, gaps, denials, or missing information**:
- Stale or superseded records that were considered but rejected.
- Criteria IDs that were not met or remain unresolved.
- Missing packet items or assistance fields (use the field ID, not a document ID).
- Records that document why a requirement could not be satisfied.

List them in the order defined by the answer template's `ordering_rule` — typically
criteria/route gaps before stale/excluded records when both appear.

#### precedence_record_order

The combined list of controlling and exception records ordered by source precedence,
**highest priority first**. This is the full audit trail showing the decision chain
in priority order.

### Phase 5 — Validate and Return

1. **Check required keys**: Every key in `answer_template.required_top_level_keys`
   must be present. Every nested `required_keys` must be satisfied.
2. **Check enum values**: Every enum field must use one of the allowed choices.
3. **Check ordering rules**: Lists must follow the specified ordering (ascending
   document ID, alphabetical, claim-line order, operational packet order, etc.).
4. **Check numeric precision**: Currency in USD rounded to two decimal places;
   ratios to four decimal places; integers for units.
5. **Check date format**: All dates in `YYYY-MM-DD` format.
6. **Check modifier handling**: Use `null` (JSON null, not the string "null") for
   absent modifiers.
7. **Return JSON only**: No markdown, no prose outside the JSON object. The output
   must parse as a single JSON object.

## Common Enumeration Tables

### Recommendation / Status / Route (Prior Auth)

| Recommendation | final_status | route | determination_letter | next_action |
|---|---|---|---|---|
| approve | approved | nurse_approval | approval | issue_approval |
| pend_for_information | pended | pending_information | information_request | request_more_information |
| escalate_to_md | md_review_required | medical_director_review | adverse_determination | route_md_review |
| deny | denied | peer_to_peer | adverse_determination | issue_denial |
| partial_approval | partially_approved | appeal_unit | partial_approval | resubmit_corrected_claim |

### Criteria Value Options

| Value | Meaning |
|-------|---------|
| `met` | The criterion is satisfied by the evidence. |
| `not_met` | The criterion is clearly not satisfied. |
| `partial` | Partially satisfied (drug failure criteria only). |
| `unclear` | The evidence is ambiguous or insufficient to decide. |
| `not_applicable` | The criterion does not apply to this case. |

### Basis Audit Source Precedence Rules (Full Reference)

1. **current_clinical_records_over_stale_export** — Prefer records retrieved live
   from the clinical environment over previously exported or batch-generated data
   that may be out of date.

2. **payer_appeal_before_manufacturer_assistance** — The payer's internal appeal
   process takes operational precedence over external manufacturer assistance
   programs. Resolve appeal requirements first, then screen assistance.

3. **effective_benchmark_by_plan_modifier_and_date** — Select the rate schedule
   that matches the plan type, line modifier, CPT code, and effective date
   quarter. Stale schedules or schedules with non-matching modifiers are rejected.

4. **new_patient_specific_p2p_information** — The peer-to-peer discussion is the
   controlling event. New patient-specific clinical information shared during P2P
   takes precedence over the pre-P2P record.

5. **margin_threshold_then_charge_sensitivity** — Evaluate each service row
   against the revenue-to-cost threshold first. Charge sensitivity is a secondary
   classification applied after the threshold check.

6. **appeal_deadline_then_clinical_then_payment_integrity** — Multi-factor
   priority: the appeal's statutory/contractual deadline is the dominant concern,
   followed by clinical merit review, followed by payment integrity checks.

## Cross-Cutting Rules

### Document Classification

When the answer template asks for evidence vs. excluded documents:
- **Evidence documents**: Clinical or administrative records whose content directly
  supports the determination — evaluation notes, plans of care, imaging reports,
  lab results, specialist consults, trial/failure documentation.
- **Excluded documents**: Records that are stale (superseded by newer versions),
  irrelevant to the current request, or belong to a different case/member.

### Stale Record Detection

A record is stale when:
- A newer version of the same record type exists in the environment (e.g., an
  updated evaluation supersedes the initial one).
- The record's date predates a more recent clinical event that would make it
  obsolete.
- For rate schedules: the schedule's effective date range does not cover the
  claim's date of service, or a newer quarterly version exists.

### Ordering Conventions

| Context | Order |
|---------|-------|
| Evidence documents | Ascending by document_id |
| Excluded documents | Ascending by document_id |
| Medication names | Alphabetical, lowercase |
| Claim lines | Claim-line order from the source claim |
| Criteria IDs | Ascending criterion ID order |
| Packet items (required) | Operational packet order: payer appeal items before assistance items |
| Packet items (missing) | Appeal evidence gaps before assistance information gaps |
| Assistance missing fields | Alphabetical by field ID |
| Below-threshold segments | Alphabetical by enum value |
| Charge-sensitive segments | Alphabetical by enum value |
| Queue rows | Same order as task_context row IDs |
| CPT codes in auth | Ascending CPT code |

### Error Handling

- If a required record is not found in the environment, note it as a gap (in
  exception_record_ids or missing_packet_items) rather than guessing.
- If the environment returns an error, retry once with the same request before
  treating it as unavailable.
- If a criterion cannot be evaluated due to missing evidence, mark it `unclear`
  rather than `not_met` — `unclear` means the evidence is insufficient, while
  `not_met` means the evidence clearly contradicts the requirement.

## Step-by-Step Execution Template

```
1. Read prompt.txt, task_context.json, answer_template.json
2. Read environment_access.md for base URL and credentials
3. GET {base_url}/api/tables to discover the schema
4. Query the primary entity (case/claim/appeal/queue)
5. Query related entities (member, plan, policy, documents, rate schedules)
6. Run SQL queries for cross-entity or filtered retrievals
7. Apply domain business rules (see Phase 3 sections above)
8. Classify documents as evidence or excluded
9. Select the source_precedence rule that best explains the logic
10. Build controlling_record_ids, exception_record_ids, precedence_record_order
11. Construct the full JSON answer following every constraint in answer_template.json
12. Validate: required keys present, enums correct, ordering rules followed,
    numeric precision met, dates in YYYY-MM-DD, JSON parseable
13. Return the JSON object — no markdown wrapping, no prose
```
