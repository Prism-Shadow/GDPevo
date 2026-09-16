# API Patterns

## Base rules

- Use the base URL from `environment_access.md`.
- Stay within the allowed endpoints only.
- Treat the task's answer template as the source of truth for the response shape and controlled vocabulary.
- Preserve JSON types exactly. Do not stringify numbers or booleans.

## Endpoint map

- Account-level analysis:
  - `/api/accounts/{account_id}`
  - `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`
  - `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - `/api/accounts/{account_id}/billing`
  - `/api/accounts/{account_id}/ar-aging`
- Portfolio analysis:
  - `/api/accounts`
  - `/api/finance/ar-aging`
  - `/api/opportunities`
  - `/api/hr/summary`
  - `/api/events/performance`
- Churn tasks:
  - `/exports/churn/train.csv`
  - `/exports/churn/validation.csv`
  - `/exports/churn/candidates.csv`

## Report-family checklists

### Renewal risk / retention board

- Restrict the cohort to the account IDs named in the prompt.
- Pull billing, support, NPS, usage, receivables, and expansion signals as needed.
- Convert those signals into rank, risk level, action, and reason codes.
- Check summary counts and ARR exposure against the item rows.

### QBR metrics packet

- Aggregate month-by-month revenue, tickets, SLA compliance, and NPS.
- Compute averages and peak months from the exact months requested.
- Choose source enums that match the data source actually used.

### Receivables / pipeline review

- Start with overdue A/R buckets, then link exact CRM accounts where possible.
- Sort overdue follow-ups by customer_name when requested.
- Use the same due date for every follow-up action when the prompt fixes it.

### Churn validation / outreach ranking

- Read train and validation CSVs before ranking candidates.
- Report dataset validation metrics before the ranking list.
- Rank only the requested candidates.
- Use probability precision requested in the prompt, usually 3 decimals.

## Final checks

- Item counts, summary totals, and top-N outputs must reconcile.
- Controlled labels must be copied exactly.
- Do not hardcode task-local values into the skill.
