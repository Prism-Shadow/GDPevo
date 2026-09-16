---
name: harborcrm-reconciliation
description: Use this skill for HarborCRM API tasks that require a strict CRM-ready JSON answer from event, tradeshow, prospecting, import-batch, sponsor, badge, campaign-member, account, contact, opportunity, suppression, invoice, or policy data. It is especially useful when the prompt references HarborCRM, TASK_ENV_BASE_URL, answer_template.json, lead qualification, sponsor finance handoff, duplicate cleanup, platform coverage, or controlled enum/count/sorting requirements.
---

# HarborCRM Reconciliation

Use this skill when a task asks for a JSON-only HarborCRM handoff or audit built from API data and an `input/payloads/answer_template.json` file.

## Start Here

1. Read the task prompt and every payload file before querying the API.
2. Load `input/payloads/answer_template.json` and treat it as the contract for keys, enums, null-vs-empty-string behavior, ordering, and numeric precision.
3. Read the API base URL from the runner prompt or environment. Fetch only public endpoints listed by the prompt or allowed environment instructions.
4. If an endpoint listed in the prompt is unavailable, do not invent records. Use the available collection endpoints and any equivalent aggregate endpoint the environment exposes.
5. Build the answer as one JSON object only. Do not include prose, comments, Markdown fences, or fields not required by the template.

Use [references/harborcrm-playbook.md](references/harborcrm-playbook.md) for reusable decision rules. Use [scripts/harborcrm_utils.py](scripts/harborcrm_utils.py) for deterministic normalization, endpoint fetching, date arithmetic, platform inference, and top-level schema checks.

## Workflow

1. **Collect data**
   Fetch the primary object from the prompt: event, tradeshow, or import batch. Then fetch the related data needed by the template: exhibitors or meeting interest; raw contacts and suppression; accounts, contacts, opportunities, campaign members; sponsor/order/badge/invoice/package/policy resources when exposed.

2. **Normalize before matching**
   Lowercase and trim emails. Convert phones to digits only. Normalize company names for matching, but preserve display names from the winning source row or source object. Use account IDs when provided; otherwise match by exact normalized company name, email or website domain, then contact evidence.

3. **Classify records**
   Apply the prompt and template first, then the playbook. Separate qualified records from exclusions. Keep controlled enum values exactly as written in the template.

4. **Compute derived fields**
   Recalculate dates from source date plus follow-up offsets, revenue/open-balance totals from source amounts, opportunity totals from qualified records, duplicate/removal counts from raw rows, and platform/action counts from the final included records.

5. **Sort last**
   After all filtering and calculations, sort every list exactly as the template says. If no ordering is specified, sort stable, human-facing lists by company/account name and technical lists by ID.

6. **Validate**
   Parse the final JSON, check top-level keys against the template, verify all enum values, recount all summary totals from the final lists, and confirm no explanatory text surrounds the JSON.

## Helpful Commands

Fetch several JSON endpoints:

```bash
python skill/scripts/harborcrm_utils.py fetch "$TASK_ENV_BASE_URL" /api/crm/accounts /api/crm/contacts
```

Normalize or compute a due date:

```bash
python skill/scripts/harborcrm_utils.py normalize --email " Person@Example.COM " --phone "+1 (202) 555-0100" --date 2030-01-15 --days 7
```

Check top-level answer keys:

```bash
python skill/scripts/harborcrm_utils.py check answer.json input/payloads/answer_template.json
```

The helper is intentionally generic. Import its functions into a scratch script when the task requires more complex joins or counting.
