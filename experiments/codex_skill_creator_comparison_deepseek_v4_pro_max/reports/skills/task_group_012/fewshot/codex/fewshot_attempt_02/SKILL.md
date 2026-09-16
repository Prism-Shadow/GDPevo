---
name: peopleops-console
description: Navigate the PeopleOps Console task environment to resolve HR onboarding closeouts, case folder reviews, recruitment reconciliations, leave-source precedence disputes, and payroll accrual readiness checks. Use when Codex needs to verify employee records, inspect case folders and formal notices, reconcile recruitment outcomes, adjudicate leave policy precedence, or validate payroll assignments against a PeopleOps API. The skill applies across any employee ID, case ID, or recruitment opening within the environment.
---

# PeopleOps Console

## Overview

Work through PeopleOps HR tasks by gathering evidence from the task-environment
API, applying business rules around record precedence and draft exclusion, and
returning a JSON answer that matches the supplied answer template schema.

## Authentication

Every PeopleOps session uses the same credentials. Log in first:

```
ops.lead@peopleops.local
PeopleOps#2026
```

The task environment base URL is always provided as `<TASK_ENV_BASE_URL>` in
the prompt. Resolve it before making any API call.

## Core Workflow

1. **Read the prompt carefully** — identify the employee/case/opening ID, the
   business question, and the answer template schema.

2. **Read the answer template** (`input/payloads/answer_template.json`) — every
   field has an `allowed_values` list. All output labels must come from these
   enumerations, never from free text.

3. **Gather evidence** — query the API endpoints relevant to the task. See
   [references/api_endpoints.md](references/api_endpoints.md) for the full
   endpoint catalog. Always prefer authoritative submitted/approved records
   over drafts, profile summaries, or case summaries.

4. **Apply business rules** — see
   [references/business_rules.md](references/business_rules.md). The key rules
   are:
   - Draft records are never authoritative; exclude them
   - Submitted payroll assignments beat drafts
   - Approved leave assignments beat stale profile summaries
   - Notice quality is checked by inspecting notice packets (not messages or
     summaries)
   - Folder readiness requires all required files and tags
   - Recruitment outcomes are determined from interview feedback and offers,
     not case summaries

5. **Assemble the answer** — use only the allowed values from the answer
   template. Arrays contain IDs only (e.g., candidate IDs, assignment IDs,
   audit event IDs). Numeric fields use the exact values from API responses.

6. **Return JSON only** — no markdown fences, no explanatory text.

## Common Answer Fields

The answer template for each task defines its own schema with explicit
`allowed_values`. These families recur across tasks:

**Source and precedence** — fields that declare which record was authoritative:
`leave_source`, `payroll_source_status`, `evidence_source_order`,
`candidate_status_source`, `cost_source`, `notice_quality_source`,
`precedence_source`, `audit_scope`, `leave_precedence_source`.

**Exclusion** — fields listing draft, superseded, or irrelevant records:
`excluded_leave_ids`, `excluded_payroll_ids`, `excluded_audit_event_ids`,
`excluded_assignment_id`, `draft_exclusion_rule`.

**Control and gate** — fields that drive the final decision:
`closeout_action`, `final_control_result`, `approval_closeout_gate`,
`control_result`, `handoff_control_result`, `payroll_handoff_gate`.

**Quality and inspection** — fields that report on folder/notice condition:
`notice_quality`, `notice_defects`, `folder_ready`, `missing_files`,
`required_tag_present`, `folder_required_tag_action`.

**Follow-up and remediation** — fields that prescribe next steps:
`next_action`, `notice_followup_required`, `escalation_action`,
`records_remediation_owner`, `notice_remediation_action`,
`waitlisted_followup_action`, `rejected_followup_action`.

Always pick the value from the template's `allowed_values` that best matches the
evidence, not a value that "sounds close."

## Reference Files

- [api_endpoints.md](references/api_endpoints.md) — complete endpoint catalog
  with field descriptions
- [business_rules.md](references/business_rules.md) — record precedence, draft
  exclusion, notice quality, folder readiness, and recruitment reconciliation
  rules
