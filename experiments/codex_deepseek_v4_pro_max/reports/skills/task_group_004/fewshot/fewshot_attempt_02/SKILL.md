 # ApexCloud Retention Operations Analyst

 Use this skill whenever a task requires building structured retention-analysis reports from the ApexCloud Retention Operations API. The skill covers risk queues, QBR metrics packets, receivables-and-pipeline reviews, churn-model validation, and high-touch retention action boards.

 ## Workflow

 ### 1. Parse the prompt for operational parameters

 Extract these values from the user prompt before touching the API:

 - **Base URL**: read the environment variable `TASK_ENV_BASE_URL` (or the `<TASK_ENV_BASE_URL>` placeholder). Consult `environment_access.md` if present in the workspace for the resolved URL and allowed endpoints.
 - **Accounts**: list every `account_id` the prompt names. If the prompt says "all regions" or "all accounts", expect to discover accounts dynamically via `/api/accounts`.
 - **Date range / quarter / months**: identify the start date, end date, assessment/as-of date, and/or month list. Convert quarter labels (e.g. `2026-Q2`) to the corresponding months before calling endpoints.
 - **Output schema**: always locate `input/payloads/answer_template.json` (or wherever the prompt points) and use its exact key names, nesting, and field order. Never reshape the template.
 - **Precision rules**: every task expects currency to 2 decimals, percentages to 1 decimal, and counts as integers. Some tasks add churn probabilities to 3 decimals — respect the per-task rules stated in the prompt.
 - **Rank / sort directives**: note explicit sorts (e.g. "top 5 by risk score descending", "by customer_name ascending").

 ### 2. Collect data from the API

 Available endpoints and typical uses are documented in `reference/api_endpoints.md`. Use query parameters exactly as the endpoint supports. Core patterns:

 - **Account profile & tenure** → `GET /api/accounts/{account_id}`.
 - **Monthly metrics** (revenue, usage) → `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`.
 - **Support tickets & SLA** → `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`.
 - **NPS surveys** → `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`.
 - **Billing / ARR** → `GET /api/accounts/{account_id}/billing` or `GET /api/billing/snapshots`.
 - **Overdue receivables** → `GET /api/accounts/{account_id}/ar-aging` or `GET /api/finance/ar-aging`.
 - **CRM pipeline / opportunities** → `GET /api/opportunities` with optional query filters.
 - **HR headcount / claims** → `GET /api/hr/summary`.
 - **Event metrics** → `GET /api/events/performance`.
 - **Churn exports** → `GET /exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`.
 - **Account metric extract** → `GET /exports/account_metric_extract.csv`.

 Fetch data for every required account and time window. Prefer parallel calls when the endpoints are independent.

 ### 3. Synthesize the analysis

 Map raw API responses to the output schema using the domain vocabulary in `reference/vocabulary.md`. The vocabulary file defines every allowed enum value for risk levels, primary actions, reason codes, trend labels, metric source labels, review owners, agenda topics, link statuses, accuracy bands, outreach actions, and policy-code families.

 Key synthesis rules:

 - **Risk scoring**: derive from a weighted combination of renewal timing, revenue exposure, NPS trajectory, SLA health, usage trend, overdue receivables, and tenure. Higher weights fall on revenue exposure and overdue balances when they co-occur with negative sentiment or SLA degradation.
 - **Ranking**: always rank highest-risk / highest-probability first. Break ties by ARR descending.
 - **Reason codes**: attach every code that genuinely applies based on the fetched data. Do not guess. If billing is clean, include `clean_billings`; if it is not, include the specific problem code.
 - **Primary action**: choose the single best action from the controlled vocabulary that matches the dominant risk driver for that account.
 - **Policy codes**: select a single code per family (do not output a pipe-delimited union) that reflects the actual methodology used in this run. The pipe-delimited labels in templates are *options*, not the final value.

 ### 4. Format the output

 - Strip any markdown fences or commentary. Return **only** a single JSON object.
 - Apply deterministic precision: round currency to 2 decimals, percentages to 1 decimal, counts as integers. Use Python's `round()` for consistency.
 - Fill every field in the template — use `null` only where the template explicitly allows it. For arrays, return an empty array `[]` when there is genuinely nothing to report.
 - Sort arrays as directed by the prompt. Default sort for risk boards is descending by risk score.
 - Use the exact key names from `answer_template.json`; do not invent or rename keys.

 ### 5. Validate before returning

 - Confirm every `account_id` / `customer_id` in the output matches one named in the prompt (or was legitimately discovered via `/api/accounts`).
 - Confirm all enum values are from the controlled vocabularies.
 - Confirm precision rules are followed on every numeric field.
 - Confirm the JSON is valid (no trailing commas, correct string escaping).

 ## Supporting reference files

 - `reference/api_endpoints.md` — full endpoint catalog with query parameters.
 - `reference/vocabulary.md` — every controlled enum and policy-code family.
 - `reference/precision_rules.md` — per-type rounding and formatting rules.
