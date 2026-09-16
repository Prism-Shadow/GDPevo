---
name: harborcrm-prepare
description: Prepare HarborCRM event handoff, trade-show prospecting, and import-cleanup JSON outputs from task API data and a provided template. Use when a prompt names HarborCRM records, asks for sponsor status reconciliation, exhibitor qualification, contact import cleanup, normalization, exclusion counts, due dates, or any other strict JSON handoff from the HarborCRM task environment.
---

# HarborCRM Workflows

## Overview
Use this skill for HarborCRM tasks that must return one JSON object only.

The template is the schema authority. The prompt supplies the task-specific rules. The API data supplies the records.

## Workflow
1. Read the prompt and the answer template first.
2. Fetch the runner-supplied HarborCRM base URL and only the endpoints named by the prompt or required by the template.
3. Load `GET /api/policies` early so controlled enums and qualification rules stay consistent.
4. Build the output in the exact shape the template expects. Do not add fields or reuse example values.
5. Normalize contact facts before comparing records:
   - emails: trim and lowercase
   - phones: strip all non-digits
   - names and company names: preserve display text unless the prompt says otherwise
6. Classify with the narrowest status set allowed by the template.
7. Use CRM state to decide `create_*`, `update_existing`, `no_import`, or `suppress`.
8. Sort every list exactly as requested. If the prompt is silent, use the template order rules.
9. Count only surviving records for totals and action counts.
10. Return JSON only.

## Task Families
- Event handoff: reconcile sponsor status, event leads, follow-up dates, and CRM work.
- Trade-show prospecting: qualify exhibitors, assign platform coverage, and summarize overlaps and exclusions.
- Import cleanup: dedupe rows, apply suppression, normalize contacts, and count import actions.

## Reference
See [references/harborcrm.md](references/harborcrm.md) for the stable HarborCRM rules, status handling, and tie-break guidance.
