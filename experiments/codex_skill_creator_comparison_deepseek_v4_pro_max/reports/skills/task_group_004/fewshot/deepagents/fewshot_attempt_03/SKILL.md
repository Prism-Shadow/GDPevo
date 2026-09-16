---
name: apexcloud-retention
description: "Operational analysis and reporting with the ApexCloud Retention Operations REST API. Use when a task requires: (1) renewal risk queue ranking accounts by churn risk with risk scores, actions, and reason codes, (2) QBR metrics packet with monthly revenue, support tickets, SLA, and NPS, (3) A/R receivables and pipeline operations review with overdue followups linked to CRM accounts, (4) churn model validation and outreach ranking by predicted churn probability, (5) high-touch retention operations board reconciling billing, support, NPS, receivables, usage, and expansion across accounts, or (6) any task querying multiple ApexCloud endpoints to produce structured JSON with controlled vocabularies and deterministic precision."
license: MIT
compatibility: designed for deepagents-code
---
# ApexCloud Retention Operations

## Overview

The ApexCloud Retention Operations API provides customer success data across accounts, billing, support tickets, NPS surveys, A/R aging, CRM pipeline, HR context, events, and churn model exports. Every analysis task follows the same core pattern: fetch from multiple endpoints, reconcile across sources, compute aggregates, and return deterministic JSON with controlled vocabularies.

## Quick Start

Every task provides a base URL. Substitute `<TASK_ENV_BASE_URL>` with the actual URL before making any calls.

```bash
# Verify the service is running
curl -s <TASK_ENV_BASE_URL>/api/health
```

## Core Capabilities

The skill supports five analysis types. Each maps to a structured JSON output with controlled vocabularies and deterministic precision. See the workflow reference for step-by-step procedures.

### 1. Renewal Risk Queue

Rank a specified set of accounts by renewal risk. Gather account profiles, billing snapshots, account-month metrics, support tickets, NPS responses, and A/R aging. Compute a risk score from renewal timing, revenue exposure, sentiment, SLA health, usage trends, overdue receivables, tenure, and lifecycle context. Return the top 5 ranked accounts.

**Output shape:** `risk_accounts` array (rank, account_id, risk_score, risk_level, primary_action, current_arr, latest_nps, clean_ticket_count, overdue_balance, reason_codes), `portfolio_summary` object, `model_checks` object, `policy_codes` object.

### 2. QBR Metrics Packet

Build a monthly metrics breakdown for a single account across three months. Pull recognized revenue, clean ticket counts, SLA compliance, and NPS scores per month, then compute highlights (averages, peaks, trends).

**Output shape:** `qbr_metrics` array (per month), `highlights` object, `metric_sources` object, `review_plan` object, `agenda_topics` array.

### 3. Receivables and Pipeline Operations Review

Reconcile overdue A/R aging entries with CRM accounts by customer name/alias matching, summarize Q3 pipeline (won/lost/open, win rate, top product line), and attach HR and event operations context.

**Output shape:** `financial_summary` object, `pipeline_summary` object, `overdue_followups` array sorted by customer_name ascending, `ops_context` object, `policy_codes` object.

### 4. Churn Model Validation and Outreach Ranking

Validate churn model exports (train, validation, candidate CSVs) by extracting row counts, feature counts, and accuracy. Rank specified candidate accounts by predicted churn probability and assign outreach actions.

**Output shape:** `model_validation` object, `risk_ranking` array (top 5), `cohort_checks` object, `model_policy_codes` object.

### 5. High-Touch Retention Operations Board

Reconcile account profiles, billing snapshots, support health, NPS, A/R, product usage, and expansion opportunities across specified accounts. Produce a full action board ranked by risk, with follow-up due dates per action type.

**Output shape:** `action_board` array, `segment_summary` object, `followup_calendar` object, `policy_codes` object.

## Output Conventions

Every response is valid JSON only, with no surrounding text or markdown.

**Precision rules:**
- Currency values: 2 decimal places
- Percentage values: 1 decimal place
- Risk scores and counts: integers
- Churn probabilities: 3 decimal places

**Controlled vocabularies:** All enum values for risk levels, actions, reason codes, metric sources, agenda topics, policy codes, and every other enumerated field are documented in [references/controlled_vocabularies.md](references/controlled_vocabularies.md). Use only values listed there.

**Policy codes:** Each task includes a `policy_codes` block. Select the code that best fits the data-driven evidence; do not guess or hardcode. The reference explains the mapping logic.

## Data Reconciliation Rules

- **ARR source:** Use `billing_arr_current` from the account endpoint or the most recent `billing_arr` from billing snapshots. The `current_arr` output field comes from this source, not from CRM ARR. See output conventions reference for the `uses_billing_arr_source` flag.
- **Clean ticket count:** Count tickets where `is_duplicate=false AND is_spam=false`. Ignore duplicate/spam tickets.
- **NPS scores:** Use the latest non-null `score` from the NPS endpoint within the specified date range. Monthly `nps_score` in metrics may come from the aggregate endpoint, but the `latest_nps` for risk ranking comes from the most recent individual response.
- **SLA compliance:** Use the `sla_compliance` field from account metrics. For tickets-based SLA, count met vs total for `first_response_sla_met` or `resolution_sla_met`.
- **Overdue balance:** Sum `31_60 + 61_90 + 90_plus` from the A/R aging entry for the as-of date. Do not include `current` or `1_30`.
- **Tenure:** `contract_tenure_months` from the account endpoint. Lower tenure correlates with higher churn risk.
- **Customer name matching:** When linking A/R customers to CRM accounts, match `customer_name` from A/R aging against `account_aliases` and `legal_name` from the accounts endpoint. If a match is found, populate `account_id` and set `link_status` to `"linked"`. Otherwise `"unlinked"` with `account_id: null`.
- **Expansion pipeline:** Sum `amount` from opportunities where `state="open"` and `close_date` falls within the analysis period, for the account in question.

## References

- [API Endpoints](references/api_endpoints.md) — Complete endpoint catalog with response shapes and query parameters.
- [Controlled Vocabularies](references/controlled_vocabularies.md) — Every allowed enum value, policy code, and selection rule.
- [Output Conventions](references/output_conventions.md) — Precision, rounding, null handling, and per-field source attribution.
- [Workflows](references/workflows.md) — Step-by-step procedures for each of the five analysis types, including data fetching order, reconciliation steps, and computation logic.
