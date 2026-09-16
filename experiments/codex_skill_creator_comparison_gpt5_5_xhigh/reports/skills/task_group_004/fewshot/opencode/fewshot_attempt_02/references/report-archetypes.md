# Report Archetypes

Use this as a quick map when the prompt names one of the recurring ApexCloud deliverables.

## Renewal risk queue / retention board

Inputs usually include account profile data, account metrics, support tickets, NPS, billing snapshots, A/R aging, and sometimes opportunities.

Typical output shape:
- ranked account list
- portfolio or segment summary
- model or policy checks

Typical reasoning:
- combine exposure, sentiment, support health, billing pressure, tenure, renewal timing, and lifecycle context
- rank the most urgent accounts first unless the prompt says otherwise

## QBR metrics packet

Inputs usually include one account's profile plus monthly metrics, tickets, and NPS.

Typical output shape:
- month-by-month series
- highlight block with averages, peaks, and trend labels
- metric source mapping
- review plan and agenda topics

Typical reasoning:
- keep the month series chronological
- compute summary values from the same month range used in the series
- choose source enums that match the endpoint family named in the prompt

## Receivables and pipeline operations review

Inputs usually include A/R aging, accounts, opportunities, HR summary, and event performance.

Typical output shape:
- financial summary
- pipeline summary
- overdue follow-up list
- ops context
- policy codes

Typical reasoning:
- start from the overdue aging buckets
- link customers to CRM accounts when a match exists
- sort overdue follow-ups by customer name unless the prompt says otherwise

## Churn validation and outreach ranking

Inputs usually include churn train, validation, and candidates CSVs.

Typical output shape:
- validation metrics
- ranked candidate list
- cohort checks
- policy codes

Typical reasoning:
- validate the dataset first
- then rank only the requested candidates by predicted churn probability
- keep probability precision exactly as requested

## Common precision and sort rules

- Ranked lists: highest risk or probability first unless instructed otherwise.
- Months: chronological.
- Currency: 2 decimals.
- Percentages: 1 decimal.
- Counts: integers.
- Probabilities: the precision requested by the prompt.

## Common pitfalls

- Do not confuse revenue with ARR.
- Do not invent a source system that is not named in the prompt or template.
- Do not broaden scope beyond the listed IDs.
- Do not leave union-style placeholders such as `a|b|c` in the final answer.
