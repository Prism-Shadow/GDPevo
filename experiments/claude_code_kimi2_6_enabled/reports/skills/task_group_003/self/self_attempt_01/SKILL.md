# Task Group 003 — CRM Support Console Skill

## Overview
Tasks in this group require interacting with a shared CRM Support Console API to process tickets, cases, complaints, queues, and mobile-data worklists. The correct response is always a JSON object conforming exactly to the task’s `answer_template.json`.

---

## 1. API Access

- **Base URL**: Read from `<TASK_ENV_BASE_URL>` environment variable.
- **Health Check**: `GET /health` returns `{"ok": true, "service": "task_group_003_support_console"}`.
- **Server Header**: `SupportConsole/1.0 Python/3.11.2`.

### Primary Endpoints (from `environment_access.md`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/tickets` | `GET` | Retrieve ticket data |
| `/api/v1/customers` | `GET` | Retrieve customer data |
| `/api/v1/kb/articles` | `GET` | Retrieve knowledge-base articles |
| `/api/v1/workflows/prioritize` | `POST` | Queue/case prioritization |
| `/api/v1/audit/logs` | `GET` | Audit log data |
| `/api/v1/compliance/policies` | `GET` | Compliance policies |
| `/api/v1/sla/check` | `POST` | SLA compliance status |

**Caution**: Endpoints may return `404` when no task-specific data is loaded. During an actual solve attempt, query the endpoints relevant to the task type first.

---

## 2. Task Taxonomy & Expected Outputs

Each task has a distinct `answer_template.json`. Read it first before calling any API.

### 2.1 Ticket Batch Resolution (`ticket_batch.csv`)
**Input**: CSV with columns `ticket_id`, `customer_id`, `issue_type`, `description`.
**Output Template**:
```json
{
  "tickets": [
    {
      "ticket_id": "string",
      "resolution_code": "string",
      "priority": "string",
      "assigned_team": "string"
    }
  ]
}
```
**Key APIs**: `GET /api/v1/tickets`, `GET /api/v1/customers`, `GET /api/v1/kb/articles`

### 2.2 Case Queue Processing (`case_queue.json`)
**Input**: JSON with `queue_id` and a `cases` array (`case_id`, `issue_type`, `severity`).
**Output Template**:
```json
{
  "cases": [
    {
      "case_id": "string",
      "next_action": "string",
      "priority": "string",
      "sla_deadline": "string"
    }
  ]
}
```
**Key APIs**: `POST /api/v1/workflows/prioritize`, `POST /api/v1/sla/check`

### 2.3 Client Complaint Response (`client_complaint_email.txt` + `response_requirements.json`)
**Input**: Free-text email + JSON severity matrix and template map.
**Output Template**:
```json
{
  "complaint_id": "string",
  "complaint_type": "string",
  "severity": "string",
  "response_template_id": "string",
  "required_actions": ["string"]
}
```
**Key APIs**: `GET /api/v1/audit/logs`, `GET /api/v1/compliance/policies`

### 2.4 Queue Snapshot Escalation (`queue_snapshot.csv`)
**Input**: CSV with columns `ticket_id`, `status`, `age_hours`, `sla_breach_risk`.
**Output Template**:
```json
{
  "escalations": [
    {
      "ticket_id": "string",
      "escalation_path": "string",
      "sla_status": "string",
      "recommended_action": "string"
    }
  ]
}
```
**Key APIs**: `POST /api/v1/sla/check`, `POST /api/v1/workflows/prioritize`

### 2.5 Mobile Data Recovery (`mobile_data_worklist.json`)
**Input**: JSON with `cases` array and optional `customer_preferences` per `case_id`.
**Output Template**:
```json
{
  "resolutions": [
    {
      "case_id": "string",
      "primary_operation": "string",
      "follow_up_operation": "string",
      "charge_or_update": "string"
    }
  ]
}
```
**Key APIs**: Likely `GET /api/v1/customers` for plan/account details; use `GET /api/v1/kb/articles` for carrier/recovery procedures.

---

## 3. Reusable Workflow (SOP)

1. **Read `answer_template.json` first** to learn the exact output schema and root key name (e.g., `tickets`, `cases`, `escalations`, `resolutions`).
2. **Read all payload files** to inventory every input record. Track the ID field used (`ticket_id`, `case_id`, etc.).
3. **Call the relevant API endpoints** for the task type:
   - Ticket resolution → `/api/v1/tickets`, `/api/v1/customers`, `/api/v1/kb/articles`
   - Case/queue/SLA → `/api/v1/workflows/prioritize`, `/api/v1/sla/check`
   - Complaint/compliance → `/api/v1/audit/logs`, `/api/v1/compliance/policies`
4. **Map API responses to template fields**. Use the KB articles or compliance policies to pick canonical codes/paths rather than inventing values.
5. **Preserve cardinality**: Every input record must produce exactly one output object with the same ID.
6. **Emit ONLY JSON** in the final answer — no markdown code fences, no explanatory text.

---

## 4. Output Conventions

- **JSON only**: The grader expects raw JSON, not wrapped in ```json blocks.
- **Field names**: Must match `answer_template.json` exactly (case-sensitive).
- **Date/Times**: Use ISO 8601 strings for SLA deadlines when required (e.g., `2024-06-15T14:00:00Z`).
- **Arrays**: Maintain the same order as the input payload unless the prompt or API explicitly specifies a different sort.
- **Null/Empty**: If a field is optional in the template and no data applies, prefer `""` or `null` as shown in the template example; do not omit the key.

---

## 5. Sorting & Rounding Rules

- **No explicit sorting directive**: Keep the same order as the input payload (CSV row order or JSON array order).
- **Numeric charges/GB values**: Preserve exact values from the API or customer preferences; round only if the prompt or API response explicitly specifies a precision.
- **Priority/Severity canonical values**: Infer from the API or payload severity matrix. Common levels in this group are `low`, `medium`, `high`, `critical`.

---

## 6. Pitfalls

- **Missing records**: It is easy to accidentally drop the last row of a CSV or a case in a JSON array. Always count input records and verify the output array length matches.
- **Wrong root key**: Some templates use `"tickets"`, others `"cases"`, `"escalations"`, or `"resolutions"`. Do not assume.
- **Inventing resolution codes**: Resolution codes, escalation paths, and response template IDs must come from the API or the provided `response_requirements.json` / KB articles.
- **SLA deadlines**: Do not compute SLA deadlines manually from clock time unless the API is unavailable. Prefer the result from `POST /api/v1/sla/check`.
- **Customer preferences**: In mobile-data tasks, the `customer_preferences` object may override default operations (e.g., `accepted_refuel_gb`, `does_not_want_plan_change`). Read it per `case_id`.
- **Trailing commas**: Ensure valid JSON — no trailing commas after the last element in arrays or objects.
