---
name: harbor-crm
description: HarborCRM event-to-CRM reconciliation, trade-show prospecting, and import-batch preparation. Use when a task requires cross-referencing HarborCRM API endpoints (events, trade shows, CRM, finance, imports, policies) to produce a structured JSON handoff, prospect list, or cleaned import batch with controlled enums, sorting rules, and CRM-action classifications.
---

# HarborCRM Reconciliation & Prospecting

## Overview

HarborCRM is a shared CRM/marketing workspace backed by a REST API at a base
URL supplied by the runner as `<TASK_ENV_BASE_URL>`. Tasks require reading
multiple endpoints, applying policy-driven business rules, and producing a
strictly-typed JSON output that matches a supplied answer template.

## Task Family Decision Tree

Every HarborCRM task falls into one of these three families. Identify the
family from the prompt, then read the matching reference guide.

| Trigger | Family | Reference |
|---------|--------|-----------|
| Prompt gives an `event_id`, mentions sponsor reconciliation, badge scans, or post-event handoff | **Post-Event Handoff** | [task_patterns.md](references/task_patterns.md) |
| Prompt gives a `show_id`, mentions exhibitors, trade show, meeting interest, or prospecting | **Trade-Show Prospecting** | [task_patterns.md](references/task_patterns.md) |
| Prompt gives an `import_batch` id, mentions raw contacts, suppression, or CRM import prep | **Import Batch Preparation** | [task_patterns.md](references/task_patterns.md) |

## Core Workflow

1. **Read the answer template first.** The template in `input/payloads/answer_template.json` defines every required key, allowed enum value, sort order, numeric type, and date format. Produce exactly those keys — no extras, no omissions.
2. **Read the policies endpoint.** Call `GET /api/policies` early. Policies contain business rules (qualification criteria, exclusion lists, opportunity amounts, follow-up windows, dedup keys) that drive every decision.
3. **Pull all relevant endpoints in parallel.** No endpoint is stateful with another; fetch them concurrently.
4. **Join entities across endpoints.** Match sponsors to invoices by `invoice_id`. Match badges/contacts/accounts by `account_id` and normalized email. Match exhibitors to CRM accounts by `company_name` or domain.
5. **Classify with controlled enums only.** Never invent statuses, reasons, or actions. Use only the allowed values declared in the answer template. See [business_rules.md](references/business_rules.md) for enum catalogs.
6. **Sort output lists as specified.** Every output list has a declared sort order. Enforce it exactly.
7. **Validate numeric precision.** Counts are integers. Currency is integer USD. Dates are `YYYY-MM-DD`.

## References

- [api_endpoints.md](references/api_endpoints.md) — Complete endpoint catalog with parameters, relationships, and response shapes
- [business_rules.md](references/business_rules.md) — Policy-driven rules, controlled enums, normalization conventions
- [task_patterns.md](references/task_patterns.md) — Detailed workflows for each task family with step-by-step data flow
