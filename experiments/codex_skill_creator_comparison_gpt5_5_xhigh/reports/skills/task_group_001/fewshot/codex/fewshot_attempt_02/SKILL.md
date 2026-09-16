---
name: harborcrm-audit
description: Audit HarborCRM event handoffs, trade-show prospecting lists, and import batches. Use when a prompt asks to reconcile sponsor finance, badge scans, campaign members, exhibitors, duplicates, suppression, contact hygiene, or other HarborCRM API records and return structured JSON.
---

# HarborCRM Audit

## Overview

Use this skill to turn HarborCRM API data into a template-matched JSON handoff. Read the prompt, the answer template, and `/api/policies` before classifying any record.

## Workflow

1. Identify the task family.
   - Event handoff and sponsor reconciliation
   - Trade-show prospecting and exhibitor qualification
   - Import batch cleanup and suppression handling
2. Query only the endpoints named in the prompt, plus `/api/policies`.
3. Build canonical records in memory first, then emit one JSON object only.
4. Match the template exactly. Do not add extra keys or prose.

## Shared Rules

- Treat `/api/policies` as authoritative for allowed enums and qualification notes.
- Normalize emails to lowercase trimmed strings.
- Normalize phones to digits only.
- Trim names, company names, and other display strings.
- Use only enum values declared by the template or policy data.
- Use integer USD values unless the template says otherwise.
- Use `YYYY-MM-DD` for dates when requested.
- Sort every list exactly as the template or prompt specifies.
- Keep aggregate counts consistent with the item lists they summarize.

## Task Families

### Event Hand-off

Use [references/harborcrm_workflows.md](references/harborcrm_workflows.md#event-handoff) for sponsor status reconciliation, qualified lead extraction, follow-up counts, and campaign-member action mapping.

### Trade-Show Prospecting

Use [references/harborcrm_workflows.md](references/harborcrm_workflows.md#trade-show-prospecting) for exhibitor qualification, platform coverage, near-miss reasons, CRM overlap, and ranking logic.

### Import Cleanup

Use [references/harborcrm_workflows.md](references/harborcrm_workflows.md#import-batch-cleanup) for deduping raw contacts, applying suppression, choosing canonical rows, and counting surviving imports.
