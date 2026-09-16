 # M&A Deal Workbench API Reference

 ## Base URL

 The task environment provides the workbench base URL in the prompt via `<TASK_ENV_BASE_URL>`. All requests use that base.

 ## Read-Only SQL

 `POST /api/query`

 JSON body: `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH statement>"}`

 Use for cross-table checks that span multiple records. Only SELECT and WITH statements are permitted. Always use the documented token.

 ## Deal APIs

 | Endpoint | Description |
 |---|---|
 | `GET /workspace` | Deal workspace overview |
 | `GET /api/deals` | List all deals |
 | `GET /api/deals/<deal_id>` | Single deal summary (headline value, parties, status, structure, signing date) |
 | `GET /api/deals/<deal_id>/terms` | Current draft terms with term_id, clause_ref, category, values |
 | `GET /api/deals/<deal_id>/documents` | Deal document index |
 | `GET /api/deals/<deal_id>/benchmarks` | Market benchmarks by metric with sample_size, median, upper_quartile |
 | `GET /api/deals/<deal_id>/risk-estimates` | Risk estimates with source_estimate_id, type, low and high amounts |
 | `GET /api/deals/<deal_id>/notes` | Negotiation or deal-team notes |

 ## Target-Side Detail APIs

 | Endpoint | Description |
 |---|---|
 | `GET /api/deals/<deal_id>/cap-table` | Capitalization table: holders, security classes, fully_diluted_pct, as_converted_shares |
 | `GET /api/deals/<deal_id>/consents` | Third-party consent records with source_id, contract_name, counterparty, condition_type, amount_at_risk |
 | `GET /api/deals/<deal_id>/employees` | Employee records with employee_id, group, PTO accrual, WARN risk, service-credit gaps |
 | `GET /api/deals/<deal_id>/material-contracts` | Material contracts with contract_id, contract_name, annual_revenue, change-of-control provisions |
 | `GET /api/deals/<deal_id>/regulatory` | Regulatory records: HSR applicability, threshold basis, approval type, hell-or-high-water provisions |
 | `GET /api/deals/<deal_id>/diligence-findings` | Diligence findings with finding_id, category, amount, recommended treatment |

 ## Playbook and Policy APIs

 | Endpoint | Description |
 |---|---|
 | `GET /api/playbooks` | List available playbooks |
 | `GET /api/playbooks/<playbook_id>/rules` | Rules for a playbook: preferred position, fallback position, redlines, thresholds by category |
 | `GET /api/policies` | List available policies |
 | `GET /api/policies/<policy_id>/thresholds` | Policy thresholds: per-term limits, approved carveout groups, trigger requirements |

 ## Search

 `GET /api/search` – Search across deals, terms, and records.

 ## Data Retrieval Pattern

 1. Start with `/api/deals/<deal_id>` for the headline value and structure.
 2. Fetch `/api/deals/<deal_id>/terms` for the current draft terms.
 3. Fetch the relevant playbook rules or policy thresholds.
 4. Fetch supporting records (consents, employees, regulatory, risk-estimates, benchmarks, etc.) as needed by the task.
 5. Use `/api/query` for cross-table checks only when direct endpoints do not provide the needed join.

 ## Stable Identifiers

 Every record from the workbench carries a stable ID (term_id, consent source_id, employee_id, contract_id, finding_id, risk estimate_id). Always use these IDs verbatim in output. Never invent identifiers. When a term is missing from the draft, use an empty array for source_term_ids and document the gap from playbook/policy rules.
