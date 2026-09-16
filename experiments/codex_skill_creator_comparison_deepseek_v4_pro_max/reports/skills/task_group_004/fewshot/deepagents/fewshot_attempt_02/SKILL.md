---
name: apexcloud-retention-ops
description: Complete reference for the ApexCloud Retention Operations API. Use when building renewal risk queues, QBR metrics packets, receivables reviews, churn model validations, or high-touch retention action boards from the ApexCloud task environment. Covers all public endpoints, controlled enum vocabularies, business calculation rules (ARR sourcing, clean ticket counts, overdue balance formulas, NPS handling, renewal windows), cross-entity linking between A/R customers and CRM accounts, churn model training/scoring with logistic regression, and five reusable task archetypes. Trigger on tasks mentioning ApexCloud, retention operations, renewal risk, QBR, QBR metrics, receivables, pipeline operations review, churn model, churn validation, churn candidates, retention board, retention action board, BORD sort, or the /api/ and /exports/ endpoints listed in the catalog.
compatibility: designed for deepagents-code
---

# ApexCloud Retention Operations

## Overview

This skill provides the complete API catalog, controlled vocabularies, business rules, and reusable task patterns for the ApexCloud Retention Operations API. Use it when a task requires building structured retention analytics from the ApexCloud environment on `http://task-env:9004`.

The API surfaces account profiles, billing snapshots, support tickets, NPS surveys, A/R aging, CRM opportunities, HR summaries, event performance data, churn model CSV exports, and a flat account-metric extract. Every response is JSON unless the endpoint is an `/exports/` CSV download.

## Quick Start

1. Confirm the API is reachable: `GET /api/health`
2. Identify the task archetype from the five patterns below
3. Read the corresponding section in [references/task_patterns.md](references/task_patterns.md) for the step-by-step workflow
4. Consult [references/endpoints.md](references/endpoints.md) for exact endpoint shapes and field meanings
5. Use [references/enums.md](references/enums.md) for every controlled label value — never invent or approximate enum strings
6. Apply the precision and calculation rules from [references/calculation_rules.md](references/calculation_rules.md)

## Core Rules (Always Apply)

- **ARR source**: Prefer `/api/billing/snapshots` filtered to the assessment `as_of` date. Fall back to `billing_arr_current` from `/api/accounts`. When snapshots are used, set `uses_billing_arr_source: true` and `arr_source_code: "REV-4"`.
- **Clean ticket count**: Fetch from `/api/accounts/{id}/tickets`, then exclude `is_spam=true` and `is_duplicate=true`. Code: `SUP-8`.
- **Overdue balance**: Use `/api/finance/ar-aging`. Overdue = `31_60 + 61_90 + 90_plus`. Do not include `1_30` or `current`.
- **Latest NPS**: From `/api/accounts/{id}/nps`, latest non-retracted score. Fall back to most recent non-null `nps_score` from `/api/accounts/{id}/metrics`.
- **Precision**: Currency to 2 decimals, percentages to 1 decimal, counts as integers, risk scores as integers, churn probabilities to 3 decimals.
- **A/R to CRM linking**: Match `customer_name` from A/R aging against account `legal_name` or entries in `account_aliases`.
- **Tenure risk direction**: Higher tenure correlates with lower churn risk, so `tenure_risk_direction` is `negative`.
- **JSON output only**: Never wrap the final answer in markdown fences or include explanatory text alongside the JSON. The response must be pure valid JSON.

## Task Archetypes

Detailed workflows live in [references/task_patterns.md](references/task_patterns.md). The five archetypes are:

1. **Renewal Risk Queue** — Rank a portfolio of accounts by composite risk (RS-6 scoring) and return a top-N queue with risk_level, primary_action, reason_codes, and portfolio_summary. Policy: RS-6, REV-4, SUP-8, ACT-5.
2. **QBR Metrics Packet** — Build a single-account quarterly business review with month-by-month metrics, highlights, metric_sources, review_plan, and agenda_topics.
3. **Receivables & Pipeline Review** — Cross-reference A/R aging with CRM accounts, summarize QTD pipeline, and add HR/event context. Policy: RCP-7, CM-5, PW-6, FS-4.
4. **Churn Model Validation & Outreach** — Load train/validation/candidate CSVs, train logistic regression, validate accuracy, score candidates, and rank top 5 by churn probability. Policy: MOD-7, PRB-4, DEP-5, OUT-2.
5. **High-Touch Retention Board** — Full action board with all accounts ranked (BORD-4), segment_summary, followup_calendar, and net_revenue_exposure (EXP-6). Policy: RS-6, REV-4, SUP-8, ACT-5, BORD-4, EXP-6, CAL-5.

## Reference Files

- [references/endpoints.md](references/endpoints.md) — Full endpoint catalog with field shapes, query parameters, and notes on data interpretation.
- [references/enums.md](references/enums.md) — Every controlled label: risk_level, primary_action, reason_codes, policy_codes, metric_sources, ticket_trend, review_owner, agenda_topics, outreach_action, segment, lifecycle_status, accuracy_band, and all model/pipeline/board codes.
- [references/calculation_rules.md](references/calculation_rules.md) — Precision rules, ARR sourcing, clean ticket logic, overdue formula, NPS handling, renewal window math, tenure thresholds, usage trend detection, expansion offset, cross-entity linking, churn model training/scoring procedure, and policy code selection summary.
- [references/task_patterns.md](references/task_patterns.md) — Reusable step-by-step workflows for all five task archetypes with data requirements, scoring procedures, output construction, and policy code assignments.

## Churn Model Dependencies

When the task involves churn model CSV exports, train a logistic regression model using scikit-learn:

```python
from sklearn.linear_model import LogisticRegression
import pandas as pd

train = pd.read_csv("train.csv")
valid = pd.read_csv("validation.csv")

X_train = train.drop(columns=["customer_id", "Churn"])
y_train = (train["Churn"] == "Yes").astype(int)
X_train = pd.get_dummies(X_train, drop_first=False)

model = LogisticRegression(solver="lbfgs", max_iter=1000)
model.fit(X_train, y_train)
```

When scoring candidates, apply the same encoding, use `model.predict_proba()`, select the probability for class 1 (churn), and rank descending.
