---
name: northstar-payer-ops
description: "Northstar Health Plan payer operations environment for utilization management, pharmacy appeals, payment integrity, peer-to-peer review, and therapy margin analysis. Use when the task involves Northstar prior authorization case review, coverage appeal and manufacturer assistance intake, cardiac imaging claim repricing, P2P authorization summaries, or UM-finance therapy margin queue analysis — any structured determination against the payer operations API and SQL backend."
license: MIT
compatibility: deepagents-code
---

# Northstar Payer Operations

## Environment Access

The task prompt provides the environment base URL. Substitute it for `<TASK_ENV_BASE_URL>` in all requests below.

**Authorization** — send this header with every SQL request:

```
Authorization: Bearer pa-review-token-014
```

**Key endpoints**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/portal` | Portal overview |
| GET | `/api/tables` | Full database schema |
| GET | `/api/cases` | All cases |
| GET | `/api/cases/{case_id}` | Single case |
| GET | `/api/policies` | All policies |
| GET | `/api/policies/{policy_id}` | Single policy |
| GET | `/api/documents/{document_id}` | Single document |
| GET | `/api/rate-schedules` | Rate schedules |
| GET | `/api/appeals` | All appeals |
| POST | `/sql/query` | SQL access |

## SQL Access

Send a POST with JSON body `{"query": "<SQL>"}` and the bearer header. The database is SQLite — use standard SQLite syntax.

Always read the schema first with `GET /api/tables` or consult [schema.md](references/schema.md). The key join anchor across most tables is `case_id`.

## Domain Identification

Read the task prompt and `task_context.json` to determine the domain:

| Signal | Domain | Source Precedence |
|--------|--------|-------------------|
| "UM nurse", prior authorization, physical therapy | **Prior Authorization** | `current_clinical_records_over_stale_export` |
| "pharmacy appeals", "manufacturer assistance", drug name | **Pharmacy Appeal + Assistance** | `payer_appeal_before_manufacturer_assistance` |
| "payment integrity", claim repricing, benchmark | **Payment Integrity** | `effective_benchmark_by_plan_modifier_and_date` |
| "peer-to-peer", P2P, completed discussion | **Peer-to-Peer** | `new_patient_specific_p2p_information` |
| "UM-finance", margin queue, revenue-to-cost | **Margin Queue** | `margin_threshold_then_charge_sensitivity` |

Each domain follows one of the workflows described in [workflows.md](references/workflows.md). Load that file once the domain is identified.

## General Pattern

1. Query the database for the target business ID (case, claim, appeal, or queue row).
2. Follow the joins outward to related tables (documents, criteria, benchmarks, drug trials, etc.).
3. Apply the domain's decision rules using the evidence.
4. Build the `basis_audit` object with `source_precedence`, `controlling_record_ids`, `exception_record_ids`, and `precedence_record_order`.
5. Return exactly the JSON shape required by the task's `answer_template.json`.

## Basis Audit

Every output includes a `basis_audit`. The `source_precedence` value is domain-specific (see table above). Construct the lists as follows:

- **controlling_record_ids**: The environment record IDs that directly control the result — relevant documents, criteria results, benchmarks, P2P events, or margin rows that drove the determination.
- **exception_record_ids**: Records that explain exclusions, denials, missing information, or route priority. Gap records (missing criteria, missing packet items) come before stale or excluded records.
- **precedence_record_order**: All controlling and exception records ordered by source precedence, highest priority first.
