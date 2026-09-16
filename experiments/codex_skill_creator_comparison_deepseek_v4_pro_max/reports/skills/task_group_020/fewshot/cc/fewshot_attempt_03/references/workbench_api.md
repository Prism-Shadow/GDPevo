# Workbench API Reference

The M&A deal workbench serves structured deal records through REST
endpoints.  The base URL is always `<TASK_ENV_BASE_URL>`.

## Request conventions

All GET endpoints return JSON.  Use `curl -s` or equivalent without
extra headers unless the prompt specifies a token.

### Read-only SQL

`POST /api/query` accepts `{"token": "deal-workbench-readonly", "sql":
"<query>"}`.  Use it for cross-table checks that single endpoints
cannot resolve.  The query must be a single `SELECT` or `WITH`
statement.  Do not use SQL when a dedicated endpoint already provides
the needed data.

## Endpoint catalogue

### Deal

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals` | List of all deals |
| `GET /api/deals/<deal_id>` | Deal header: parties, headline price, signing/target-close dates, status, structure (APA/SPA) |

### Terms

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/terms` | Current draft terms with term IDs, clause references, numeric values, and textual provisions |

### Playbooks

| Endpoint | Returns |
|----------|---------|
| `GET /api/playbooks` | List of available playbooks |
| `GET /api/playbooks/<playbook_id>/rules` | Preferred, fallback, and prohibited positions for each term category the playbook covers |

### Policies (committee)

| Endpoint | Returns |
|----------|---------|
| `GET /api/policies` | List of policies |
| `GET /api/policies/<policy_id>/thresholds` | Approval thresholds in the same unit as the draft terms they govern |

### Risk estimates

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/risk-estimates` | Low/high quantified exposure estimates per risk category with source IDs |

### Benchmarks

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/benchmarks` | Market data: sample sizes, medians, quartiles for comparables |

### Consents

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/consents` | Required third-party consents with IDs, counterparty names, condition types, amounts at risk, and contract references |

### Material contracts

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/material-contracts` | Material contracts with IDs, names, counterparties, annual revenue, and consent condition types |

### Regulatory

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/regulatory` | HSR applicability, filing thresholds, approval status, required effort standards |

### Cap table (SPA only)

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/cap-table` | Holder groups, security classes, fully-diluted percentages, as-converted shares |

### Employees

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/employees` | Employee IDs, groups (field/operations/corporate), PTO liabilities, service-credit eligibility, WARN risk status |

### Diligence findings

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/diligence-findings` | Findings with IDs, dollar amounts, categories (working capital, privacy, IP, environmental) |

### Documents

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/documents` | Document references including the draft agreement; may contain governing-law and other structural defaults |

### Notes

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>/notes` | Negotiation notes with position updates, open items, and counsel observations |

### Search

| Endpoint | Returns |
|----------|---------|
| `GET /api/search` | Cross-deal search; rarely needed for single-deal tasks |

### Workspace

| Endpoint | Returns |
|----------|---------|
| `GET /workspace` | Top-level workspace summary |

## Fetch strategy by task type

### Issue register (seller APA review)

Start with `/api/deals/<deal_id>`, `/api/deals/<deal_id>/terms`,
`/api/playbooks/<playbook_id>/rules`.  Then fetch employees, consents,
regulatory, benchmarks, risk-estimates, and notes.  Use `/api/query`
only for cross-table reconciliation.

### Closing and economics package (buyer SPA review)

Start with `/api/deals/<deal_id>`, `/api/deals/<deal_id>/terms`,
`/api/deals/<deal_id>/cap-table`, `/api/playbooks/<playbook_id>/rules`.
Then fetch consents, material-contracts, regulatory, employees,
diligence-findings.  Holders come from the cap table, not from terms.

### Escalation memo (committee policy review)

Start with `/api/deals/<deal_id>`, `/api/deals/<deal_id>/terms`,
`/api/policies/<policy_id>/thresholds`.  Then fetch risk-estimates and
benchmarks.  Only include terms that violate the policy thresholds;
exclude in-policy terms even if they appear in the draft.  Include the
excluded in-policy terms list in the aggregate summary.

### Transition review (carveout APA)

Start with `/api/deals/<deal_id>`, `/api/deals/<deal_id>/terms`,
`/api/playbooks/<playbook_id>/rules`.  Then fetch employees, consents,
regulatory, risk-estimates, documents, and material-contracts.
Transition-specific issues include TSA scope/fees, IP-domain
transition, Section 1060 allocation, transfer tax, employee
continuity, outside-date extension, and governing law/forum.

### Deviation matrix (buyer SPA review)

Start with `/api/deals/<deal_id>`, `/api/deals/<deal_id>/terms`,
`/api/playbooks/<playbook_id>/rules`.  Then fetch consents,
material-contracts, regulatory, risk-estimates, diligence-findings,
and notes.  Cover indemnity cap/basket, survival/knowledge,
materiality scrape, escrow/holdback, consent closing conditions, HSR,
and material contracts.
