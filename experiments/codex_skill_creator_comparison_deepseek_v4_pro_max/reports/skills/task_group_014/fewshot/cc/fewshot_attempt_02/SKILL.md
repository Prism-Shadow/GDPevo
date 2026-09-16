---
name: northstar-payer-operations
description: Use when the task involves Northstar Health Plan payer operations — prior authorization, utilization management review, pharmacy appeals, payment integrity claim repricing, peer-to-peer clinical review, or UM-finance margin analysis. Always use this skill when the user references Northstar, a payer-operations environment, an authorization case, an appeal, a claim repricing, a P2P review, or a therapy margin queue, even when the domain terminology is partial or the task is framed as a JSON-structured determination, correction packet, or queue summary.
---

# Northstar Payer Operations

Solve Northstar Health Plan payer-operations tasks by querying the shared
HTTP + SQL environment and returning a single JSON object that conforms to
the provided answer template.

## First steps — always do these

1. **Read the three task input files**:
   - `input/prompt.txt` — the business request in prose.
   - `input/payloads/task_context.json` — the target business id, requester
     role, reporting date, and any domain-specific hints under `local_memo`
     or a similar key.
   - `input/payloads/answer_template.json` — the exact required JSON shape.
     Treat this as a binding contract: every required key must be present,
     enum values must be drawn from the listed choices, ordering rules
     must be followed, and numeric/date precision must match the spec.

2. **Read `environment_access.md`** at the workspace root. It supplies:
   - `TASK_ENV_BASE_URL` (e.g. `http://...`)
   - The SQL endpoint path and the `Authorization: Bearer ...` value.
   - The list of allowed business REST endpoints.

## Environment access pattern

Every Northstar task uses the same environment architecture:

- **Base URL** — `{TASK_ENV_BASE_URL}` from `environment_access.md`.
- **SQL endpoint** — `POST /sql/query` at the base URL.
  - Header: `Authorization: Bearer {token}`.
  - Body: JSON with a `{"query": "SELECT ..."}` field.
- **Business REST endpoints** (all `GET`):
  - `/portal` — entry point, may surface navigation hints.
  - `/api/tables` — lists available SQL tables and column names.
  - `/api/cases` — lists cases; `/api/cases/{case_id}` returns a specific case.
  - `/api/policies` — lists policies; `/api/policies/{policy_id}` returns one.
  - `/api/documents/{document_id}` — returns a clinical or administrative document.
  - `/api/rate-schedules` — lists rate/benchmark schedules.
  - `/api/appeals` — lists appeals; use `/api/appeals` to find an appeal by case or by id.

Always use the environment — do not create or inspect local files, SQLite
databases, or generated data outside the environment endpoints.

## Data discovery workflow

1. **List the available tables** with `GET /api/tables`. Note the table
   names and column schemas.
2. **Fetch the portal** with `GET /portal` and skim for hints about which
   tables or entities are relevant for the current business domain.
3. **Retrieve the target record** using the REST endpoint that matches the
   task's business object (case, appeal, or claim — the task context will
   tell you). For cases, also check whether an authorization record exists
   on the case or a linked record.
4. **Pull supporting records** — documents, policies, rate schedules,
   appeals — using their REST endpoints. Query SQL when you need cross-table
   joins or filtered subsets that the REST endpoints do not return directly.
5. **Cross-reference everything** before writing the answer. A criterion
   result must be backed by the policy text and the clinical evidence.
   A correction dollar must come from the correct benchmark row.

## Basis audit — required in every answer

Every Northstar answer template includes a `basis_audit` object with the
same four keys:

| Key | Purpose |
|-----|---------|
| `source_precedence` | The precedence rule that governs this task. Pick from the six standard rules below. |
| `controlling_record_ids` | Environment record IDs that directly control the outcome (evidence docs, benchmark rows, appeal records, P2P event, margin rows). Order by operational evidence flow. |
| `exception_record_ids` | Records that explain gaps, denials, exclusions, stale sources, missing information, or route issues. Order gaps/exceptions before stale/excluded records when both appear. |
| `precedence_record_order` | The controlling and exception records combined, sorted in source-precedence order (highest priority first). |

### The six standard precedence rules

Choose the rule that matches the task's domain and fact pattern:

1. **`current_clinical_records_over_stale_export`**
   — Current clinical documents and evaluation records take precedence over
   stale/out-of-date exports. Stale records are excluded from evidence.

2. **`payer_appeal_before_manufacturer_assistance`**
   — Process the payer appeal and its clinical evidence first. The
   manufacturer assistance screening follows and depends on the appeal
   disposition. Appeal gaps and packet items come before assistance gaps.

3. **`effective_benchmark_by_plan_modifier_and_date`**
   — Select the rate benchmark that matches the plan modifier and effective
   date. Reject stale or superseded benchmarks as exception records.

4. **`new_patient_specific_p2p_information`**
   — New patient-specific information from the peer-to-peer discussion takes
   precedence over pre-P2P clinical records and the original intended
   determination.

5. **`margin_threshold_then_charge_sensitivity`**
   — Apply the revenue-to-cost threshold first to identify below-threshold
   rows. For above-threshold rows, then check whether they are flagged as
   charge-sensitive.

6. **`appeal_deadline_then_clinical_then_payment_integrity`**
   — Priority order: appeal deadline compliance, then clinical evidence
   strength, then payment integrity or financial factors.

### How to assign records in the audit

- **controlling_record_ids**: include the records whose content *directly
  produces* the outcome. For an approval, the evaluation doc, the plan of
  care, and the criteria that were met. For a repricing, the claim lines and
  the benchmark rows that set the corrected amounts. For a margin analysis,
  the queue row IDs for all rows evaluated.

- **exception_record_ids**: include stale sources that were rejected,
  criteria that were not met, packet items that are missing, rows that fall
  below the margin threshold, and any records that explain *why* the result
  is not a simple approval. Use the business gap/exception order: criteria
  or route gaps before stale or excluded records when both appear.

- **precedence_record_order**: start with the highest-priority controlling
  record, then list the remaining controlling records, then list the
  exception records. The total list is the union of controlling and
  exception records in source-precedence order.

## Domain-specific patterns

### UM nurse review (physical therapy, occupational therapy, speech therapy)

1. Retrieve the case and its authorization record.
2. Retrieve all documents attached to the case.
3. Retrieve the applicable policy so you know which criteria govern the
   review (e.g. PT-ACTIVE, PT-DEFICIT, PT-DX, PT-POC, PT-UNITS).
4. Classify each document as clinical evidence (current eval, plan of care)
   or excluded (stale export, outdated assessment, unrelated record).
5. Evaluate each criterion against the evidence — met, not_met, unclear, or
   not_applicable.
6. Map the criteria results to a `recommendation`, `final_status`, `route`,
   `determination_letter`, and `next_action` using the template's enum sets.
7. Build the `authorization` object from the authorization record, filling
   `auth_number`, `approved_units`, date range, approved CPT codes (sorted
   ascending), and modifier.

Document classification rule: a document is *evidence* when it is current
and directly supports the medical-necessity determination. A document is
*excluded* when it is stale, superseded, or does not bear on the current
request.

### Pharmacy coverage appeals and manufacturer assistance

1. Retrieve the case (`/api/cases/{case_id}`) and appeal (via
   `/api/appeals` or SQL).
2. Determine the drug, appeal path (standard_internal / expedited_internal /
   external_review / not_eligible), and whether the appeal is expedited.
3. Calculate the appeal deadline: typically 30 calendar days from the
   denial date for a standard internal appeal, or 60 days for external
   review, unless the task context specifies otherwise.
4. Retrieve medication trial/failure records (via SQL or document endpoints)
   and classify them:
   - **documented_failures**: medications with adequate trial evidence
     (documented fill records, prescriber notes, or clinical evidence of
     failure/intolerance). List lowercase, sorted alphabetically.
   - **undocumented_or_insufficient_failures**: medications mentioned but
     lacking adequate documentation. List lowercase, sorted alphabetically.
5. Evaluate drug coverage criteria (DRUG-AUTH, DRUG-DENIAL, DRUG-RATIONALE,
   DRUG-FAILURES) against the appeal evidence.
6. Build the `required_packet_items` and `missing_packet_items` lists:
   - **required** = everything needed for a complete appeal/assistance
     submission, in operational order (payer appeal items first, then
     assistance items).
   - **missing** = items not present in the record, ordered as appeal
     evidence gaps before assistance information gaps.
7. Screen for manufacturer assistance: identify the program name (matching
   the drug), check eligibility, and list any missing fields in
   alphabetical order.

### Payment integrity claim repricing

1. Retrieve the claim lines (via SQL — claims and claim lines are typically
   in relational tables, not REST endpoints).
2. Retrieve available rate schedules (`/api/rate-schedules`) and identify:
   - The **effective benchmark** that matches the plan, modifier, and
     current date.
   - Any **stale source** that should be rejected.
3. For each claim line, look up the corrected allowed amount from the
   effective benchmark, multiply by units, and round to two decimal places.
4. Compute per-line `recovery_amount` = `correct_allowed_amount` -
   `paid_amount`. A positive recovery means the provider was underpaid; a
   negative recovery means overpayment. The template may use "recovery" to
   mean the underpayment amount — follow the template's definition.
5. Compute totals: `paid_total`, `correct_allowed_total`, and
   `recovery_amount` (sum of line recoveries, matching the template's sign
   convention).
6. Set `resubmission_route` and `priority` based on the dollar magnitude and
   business context.
7. Lines must appear in claim-line order from the source claim. Use `null`
   for absent modifiers — never an empty string.

### Peer-to-peer clinical review

1. Retrieve the case and find the P2P event record (via SQL or case-linked
   records).
2. Retrieve the authorization line CPT code, policy criteria, clinical
   evidence documents, and the P2P outcome.
3. Evaluate each applicable criterion (e.g. PET-IND, PET-FACTOR) against the
   evidence, including any new information from the P2P.
4. Identify **unresolved criteria**: criteria that remain `not_met` or
   `unclear` after the P2P. List in ascending criterion ID order. Use an
   empty list only when everything is resolved.
5. Determine whether `new_information_changed_review` — true only when the
   P2P supplied new patient-specific facts that materially altered the
   determination.
6. For cardiac PET MPI tasks, identify which PET-over-SPECT factors remain
   unsupported. List in the template's prescribed order.
7. If the final determination is adverse, set the `internal_appeal_deadline`
   to **180 calendar days** from the final adverse determination date,
   unless the task context specifies a different window.
8. Recommend the alternative modality when appropriate (e.g. SPECT MPI when
   PET MPI is denied).

### UM-finance margin analysis

1. Retrieve the margin rows by the queue row IDs listed in the task
   context's `finance_memo`. Use SQL to pull the columns you need from the
   service-margin table.
2. Compute `total_cost` = `variable_cost` + `fixed_cost_allocated` (unless
   the task context gives a different definition).
3. Compute `margin` = `revenue` - `total_cost`.
4. Compute `revenue_to_cost_ratio` = `revenue` / `total_cost`. Round to the
   precision specified in the template (typically 4 decimal places).
5. Classify each row:
   - `below_threshold` = true when `revenue_to_cost_ratio` < threshold.
   - `charge_sensitive` = true when the row has a charge-sensitivity flag
     in the environment data.
6. Assign `recommended_action`:
   - `payer_contract_review` for below-threshold rows.
   - `monitor_charge_sensitive` for above-threshold rows flagged as
     charge-sensitive.
   - `monitor_no_action` for above-threshold rows not flagged.
7. Populate `below_threshold_segments` and `charge_sensitive_segments` with
   the payer-segment values of rows that fall into each category, sorted
   alphabetically by enum value.
8. Compute `gap_to_120pct` for the top below-threshold issue: the dollar
   difference between 120% of total cost and actual revenue (i.e. `1.2 *
   total_cost - revenue`). Round to the template's precision.

## Answer construction rules

### Conformance to the template

- Read `answer_template.json` before touching any environment endpoint.
  Know what you are building before you collect the data.
- Every `required_top_level_keys` entry must appear in your output.
- Enum fields must use one of the listed `choices` — no freeform strings.
- List fields must follow the ordering rule in the template (ascending,
  alphabetical, claim-line order, operational order, etc.).
- Numeric values must match the precision in the template. Dollars are
  rounded to the specified decimal places. Ratios use the specified
  precision (typically 4 places).
- Dates must use `YYYY-MM-DD` format.
- When the template allows `null` for a value, use JSON `null`, not an empty
  string and not the string `"null"`.
- The `additional_fields_allowed` flag (or equivalent) tells you whether
  extra keys beyond the template are permitted. When it is `false`, stick
  strictly to the template's keys.

### Ordering rules

When the template says "ascending" or "alphabetical", sort by the natural
order of the id or value. When it says "claim-line order", preserve the
order from the source data. When it says "operational evidence order",
follow the domain-specific rule described in the template or task context.

### Return format

Return a **single JSON object**. Do not wrap it in markdown fences, do not
add prose before or after, do not include a `json` language tag — unless the
prompt explicitly asks for a different format (check `prompt.txt`).

## Common pitfalls

- **Confusing the REST and SQL layers**: REST endpoints (`/api/cases`,
  `/api/documents`, etc.) return pre-joined domain objects. Use them first.
  Reach for SQL only when you need cross-table joins, filtered lists, or
  tables not exposed via REST.
- **Including stale records in evidence**: check dates and versions. A
  "Legacy" or "Stale" label in the environment means the record should be
  excluded or treated as an exception.
- **Miscomputing recovery_amount**: the template definition varies. In some
  tasks recovery = overpayment (paid - corrected); in others it represents
  the underpayment correction. Read the template definition.
- **Forgetting the basis_audit**: every answer template requires it. If you
  skip it, the answer is incomplete.
- **Not ordering lists correctly**: the template's ordering rules are part
  of the contract. An otherwise correct answer with wrong ordering may fail.
- **Using empty strings for absent modifiers**: always use `null` in JSON.
