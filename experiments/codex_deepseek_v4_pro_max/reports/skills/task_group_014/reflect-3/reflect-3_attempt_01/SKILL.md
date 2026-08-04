 # Northstar Payer Operations Skill

 Parse a Northstar Health Plan operational task, query the shared payer-operations environment, and return a structured JSON answer conforming to the task's `answer_template.json`.

 ## When to Use

 Use this skill for Northstar payer-operations tasks involving utilization management, pharmacy appeals, payment integrity, peer-to-peer summaries, or therapy-margin queue analysis. The task prompt always names the Northstar business entity and references `<TASK_ENV_BASE_URL>`.

 ## Environment Setup

 The environment base URL is specified in the task prompt and/or `environment_access.md`. The SQL endpoint is `POST /sql/query` with a JSON body `{"sql": "<query>", "params": []}`. All requests require the header `Authorization: Bearer pa-review-token-014` and `Content-Type: application/json`.

 Business REST endpoints are also available for browsing records:
 - `GET /api/tables` — schema overview
 - `GET /api/cases`, `GET /api/cases/{case_id}`
 - `GET /api/policies`, `GET /api/policies/{policy_id}`
 - `GET /api/documents/{document_id}`
 - `GET /api/rate-schedules`
 - `GET /api/appeals`

 Do not inspect environment source files, SQLite database files, manifests, or setup scripts directly. Use only the HTTP endpoints.

 ## Workflow

 ### 1. Discover Schema

 Query all table names:
 ```sql
 SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
 ```

 Inspect column details for each relevant table:
 ```sql
 PRAGMA table_info(<table_name>)
 ```

 The standard schema includes these tables (verify with the live environment):

 | Table | Purpose |
 |---|---|
 | `cases` | Authorization / appeal / claim cases |
 | `members` | Member demographics and plan enrollment |
 | `plans` | Health plan product details |
 | `providers` | Rendering / prescribing providers |
 | `request_lines` | Requested CPT/HCPCS lines with units and modifiers |
 | `authorizations` | Authorization decisions linked to cases |
 | `documents` | Clinical, administrative, and evidence documents |
 | `document_facts` | Key-value facts extracted from documents, linked to criteria |
 | `policies` | Medical / drug / payment policy headers |
 | `policy_criteria` | Individual criteria definitions within a policy |
 | `case_criteria` | Criteria results per case |
 | `claims` | Paid claim headers |
 | `claim_lines` | Individual claim-line detail |
 | `payment_benchmarks` | Rate-schedule benchmarks by payer, plan, CPT, modifier, and effective date |
 | `appeals` | Appeal records linked to cases |
 | `drug_trials` | Medication trial/failure history |
 | `assistance_screen` | Manufacturer assistance-program screening results |
 | `p2p_events` | Peer-to-peer discussion records |
 | `service_margin` | Monthly therapy-margin data |

 ### 2. Identify the Task Type

 Read the task `prompt.txt` and `task_context.json`. Determine the business domain:

 - **UM nurse determination** — case-driven; look for `prior_authorization`, `nurse_review`, criteria results, clinical documents, and authorization records.
 - **Pharmacy appeals** — appeal-driven; look for `APPEAL-`, `coverage_exception`, drug trials, appeals table, and assistance screen.
 - **Payment integrity / claim repricing** — claim-driven; look for `CLAIM-`, payment benchmarks with effective dates, stale schedules.
 - **Peer-to-peer summary** — P2P-driven; look for `P2P-`, `peer_to_peer`, p2p_events, criteria with PET/imaging factors.
 - **Therapy margin queue** — finance-driven; look for `QUEUE-`, `service_margin`, revenue/cost ratios.

 ### 3. Gather All Relevant Records

 Starting from the target business ID (case_id, claim_id, appeal_id, or queue row IDs), join outward following foreign keys. Typical query chains:

 - case → member → plan
 - case → provider
 - case → request_lines
 - case → documents (filter `is_current` for active evidence)
 - case → document_facts
 - case → case_criteria → policy_criteria
 - case → authorizations
 - case → appeals → drug_trials → assistance_screen
 - claim → claim_lines
 - claim → payment_benchmarks (match on plan_type, cpt_code, modifier, effective dates)

 ### 4. Apply Business Rules

 #### Evidence and Document Handling

 - Current documents (`is_current = 1`) are evidence documents. Non-current / stale documents (`is_current = 0`) are excluded.
 - The source-precedence rule for clinical reviews is **current clinical records over stale exports**.

 #### Criteria Evaluation

 - Map each `criterion_id` from `case_criteria` to its result value (`met`, `not_met`, `partial`, `unclear`, `not_applicable`).
 - A criterion with result `not_met` or `partial` that remains unsatisfied after review is **unresolved** and should appear in `unresolved_criteria`.
 - When policy criteria require specific evidence (e.g., formulary failure fill records, PET-over-SPECT factors), identify gaps with the most specific enum value available.

 #### Authorization

 - When all required criteria are met and the authorization status is favorable, the recommendation is `approve` with route `nurse_approval`.
 - Approved CPT codes are listed in ascending order. Approved units are the sum of requested units.
 - Use `null` for absent modifiers; never use an empty string.

 #### Appeals and Assistance

 - Documented medication failures: trials with `documented = 1`, ordered alphabetically by medication name.
 - Undocumented / insufficient failures: trials with `documented = 0`, ordered alphabetically.
 - Required packet items: list payer appeal items before manufacturer assistance items, using the operational packet order.
 - Missing packet items: list appeal evidence gaps before assistance information gaps, using the most specific enum value available.
 - Assistance status derives from the `assistance_screen` record. When denial is on file and only income proof is missing, the status is `eligible_missing_information`.
 - The source-precedence rule is **payer appeal before manufacturer assistance**.

 #### Payment Integrity and Benchmarking

 - Match claim lines to `payment_benchmarks` on payer, plan_type, service_domain, cpt_code, and modifier, where the service date falls within `effective_start` to `effective_end`.
 - Reject stale rate sources whose effective period ended before the service date.
 - `correct_allowed_amount` per line = benchmark `allowed_amount` × `units`.
 - `recovery_amount` per line = `correct_allowed_amount` − `paid_amount`.
 - Total recovery = sum of line recoveries. Use the underpayment amount when the corrected total exceeds the paid total.
 - Line disposition: `correct_upward` when recovery > 0, `correct_downward` when recovery < 0, `no_change` when zero.
 - The source-precedence rule is **effective benchmark by plan, modifier, and date**.

 #### Peer-to-Peer Summaries

 - `p2p_outcome` maps directly from the `p2p_events.outcome` field.
 - `final_status` maps from the authorization status or the P2P `final_status`.
 - `new_information_changed_review` is `true` only when the P2P supplied new patient-specific information that materially changed the clinical determination.
 - Missing PET-over-SPECT factors: include all three (`prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`) when none are documented.
 - Recommended alternative when PET is denied for cardiac imaging: `SPECT MPI`.
 - Internal appeal deadline: calculate from the final adverse determination date using the plan's internal appeal window.
 - The source-precedence rule is **new patient-specific P2P information**.

 #### Therapy Margin Queue

 - `total_cost` = `variable_cost` + `fixed_cost_allocated`.
 - `margin` = `net_revenue` − `total_cost`.
 - `revenue_to_cost_ratio` = `net_revenue` / `total_cost` (rounded to 4 decimal places).
 - `below_threshold` is `true` when the ratio is below the threshold.
 - `charge_sensitive` comes directly from the data column.
 - Recommended action: `payer_contract_review` for below-threshold rows, `monitor_charge_sensitive` for above-threshold charge-sensitive rows, `monitor_no_action` otherwise.
 - `below_threshold_segments` and `charge_sensitive_segments`: list distinct payer segments, each ordered alphabetically.
 - `top_issue`: the below-threshold row with the largest dollar gap to the threshold, formatted as `{segment}_{cpt}`. Use `none` when no rows are below threshold.
 - `gap_to_120pct`: `(total_cost × threshold) − net_revenue` for the top issue, rounded to 2 decimal places.
 - The source-precedence rule is **margin threshold then charge sensitivity**.

 ### 5. Build the Answer

 - Load the `answer_template.json` from the task's payload directory for the exact required shape.
 - Every top-level key and nested required key from the template must be present.
 - Use only the enum values listed in the template for each field.
 - Follow all ordering rules stated in the template (alphabetical, ascending, operational order, queue-row order).
 - Dates: `YYYY-MM-DD`. Currency: dollars rounded to 2 decimal places. Ratios: 4 decimal places.
 - Use `null` for absent modifiers; never use an empty string.

 ### 6. Basis Audit Trail

 Every answer includes a `basis_audit` object with:
 - `source_precedence`: the precedence rule for the task domain (choose from the six enum values listed in the template).
 - `precedence_record_order`: all controlling and exception records in priority order, highest first.
 - `controlling_record_ids`: environment record IDs that directly control the result.
 - `exception_record_ids`: gap/exception records explaining exclusions, denials, missing information, or route priority. Order business gaps before stale/excluded records when both appear.

 ### 7. Validate and Submit

 - Confirm all required fields are present with correct types and enum values.
 - Verify numeric precision matches the template (2 decimal places for currency, 4 for ratios, integers for units).
 - Verify date formats are `YYYY-MM-DD`.
 - Ensure lists follow the required ordering rules.

 ## Key Principles

 1. **Schema first.** Always explore the live schema with `PRAGMA table_info` before querying data.
 2. **Match on exact identifiers.** Use case_id, claim_id, appeal_id, or queue row IDs exactly as provided.
 3. **Prefer specific enum values.** When a gap can be described by a more specific enum, use it rather than a generic category.
 4. **Current over stale.** In clinical and payment contexts, current records control. Stale exports, expired benchmarks, and non-current documents are exceptions.
 5. **Precision matters.** Round currency to 2 decimals, ratios to 4 decimals. Use `null` for absent modifiers, never empty strings.
 6. **Ordering is semantic.** Follow the template's ordering rules exactly — they encode operational and business priority.
 7. **Unresolved after adverse review.** A criterion that is `not_met` or `partial` after a completed review is unresolved when the determination is adverse and the gap remains, and should appear in `unresolved_criteria`.
