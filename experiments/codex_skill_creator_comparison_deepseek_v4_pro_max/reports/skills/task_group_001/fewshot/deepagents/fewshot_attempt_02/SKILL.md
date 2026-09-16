---
name: harbor-crm-handoff
description: "HarborCRM multi-entity data reconciliation and CRM handoff preparation. Use when preparing post-event or post-tradeshow CRM handoff records from HarborCRM API data. Handles five operational workflows: (1) post-event sponsor/lead reconciliation with controlled-status sponsor reporting, qualified non-sponsor lead handoff, badge-level exclusion, and CRM action counts, (2) tradeshow OEM/platform-based prospecting with qualified exhibitor lists, priority tiering, near-miss exclusion, and aggregate counts, (3) import-batch contact cleaning with deduplication, suppression, and CRM action classification, (4) post-event badge/opportunity/sponsor reconciliation including campaign-member actions and badge-only contact normalization, and (5) tradeshow lead ranking with demo-scored priority tiers, CRM overlap detection, and platform-coverage summaries. Use for any HarborCRM data reconciliation, cleaning, qualification, and structured JSON handoff task."
compatibility: designed for deepagents-code
---

# HarborCRM Handoff

## Overview

HarborCRM exposes a shared REST API at the base URL supplied by the runner (conventionally `<TASK_ENV_BASE_URL>`). This skill provides reusable rules and reference schemas for reconciling events, tradeshows, import batches, policies, and CRM records into structured JSON handoff payloads.

This skill does **not** contain task-specific answers. It describes the reusable patterns, field semantics, controlled vocabularies, ordering rules, qualification logic, normalization rules, and follow-up-date calculations that recur across all five HarborCRM handoff workflows.

## When to Use Which Reference

Every HarborCRM handoff task shares the same API surface and core CRM reconciliation concepts. The task prompt and answer template determine which workflow and output shape to follow.

- [API Catalog](references/api_catalog.md) — complete endpoint reference with expected response shapes for events, tradeshows, import batches, invoices, CRM records, and policies.
- [Business Rules](references/business_rules.md) — qualification logic, controlled vocabularies, sorting rules, contact normalization, follow-up date calculation, priority tiering, and CRM-action classification rules.

## Core Workflow

### 1. Gather API Data

Identify the target entity from the task prompt: an `event_id`, `show_id`, or `batch_id`. Fetch all referenced endpoints using the base URL supplied by the runner. See [API Catalog](references/api_catalog.md) for the full endpoint list and response shapes.

### 2. Load Policies and CRM Baselines

Always fetch `GET /api/policies` and the CRM baselines (`GET /api/crm/accounts`, `GET /api/crm/contacts`, `GET /api/crm/opportunities`, and optionally `GET /api/crm/campaign_members`) before making qualification decisions. Account status, `disqualified_reason`, contact `opted_out`, and domain overlap drive exclusion logic.

### 3. Apply Business Rules

Use [Business Rules](references/business_rules.md) for:

- Controlled vocabularies (status enums, platform enums, exclusion reasons, CRM actions)
- Sponsor status classification from orders and invoices
- Non-sponsor lead qualification (exclude sponsors, inactive/canceled records, non-business badges, disqualified CRM accounts)
- Badge classification and CRM action derivation
- Contact normalization (email lowercase and trimmed, phone digits-only)
- Duplicate resolution rules for import batches
- Follow-up date calculation from event metadata (`end_date` + `followup_days_after_end` or `sponsor_followup_days_after_end`)
- Sorting rules per output section
- Priority tier assignment from demo requests and interest scores

### 4. Build the Output JSON

Follow the exact shape declared in `input/payloads/answer_template.json`. Never add undeclared fields. Use only the types, enums, and ordering rules the template specifies. Return one JSON object with no explanatory prose outside it.

## Resources

- **references/api_catalog.md**: Complete endpoint reference with response shapes.
- **references/business_rules.md**: Qualification logic, enums, sorting, normalization, and CRM action rules.
