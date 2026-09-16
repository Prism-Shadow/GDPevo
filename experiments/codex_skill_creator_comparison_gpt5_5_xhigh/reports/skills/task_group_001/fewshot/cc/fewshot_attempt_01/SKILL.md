---
name: harborcrm-reconciliation
description: HarborCRM API reconciliation for CRM handoff, event sponsorship and badge audits, trade-show exhibitor prospecting, and import-batch cleanup. Use this skill whenever a task asks Codex to query a HarborCRM task environment or API, fill an answer_template.json, produce JSON-only CRM-ready lead/sponsor/import output, normalize contacts, match CRM accounts or campaign members, classify trade-show exhibitors, deduplicate raw import contacts, or summarize CRM action counts.
---

# HarborCRM Reconciliation

Use this skill to solve HarborCRM tasks that require API data analysis and a JSON-only answer matching a provided `answer_template.json`.

## Required Inputs

Before computing anything:

1. Read the user prompt completely.
2. Read the provided `input/payloads/answer_template.json`.
3. Identify the API base URL supplied by the runner or task environment.
4. Read any local environment access file if one is present, and treat it plus the prompt as the boundary for network requests.

The template is authoritative for output keys, enum spellings, nullability, ordering, and whether extra fields are forbidden. Do not add commentary outside the final JSON.

## Data Gathering

Fetch all relevant GET endpoints named in the prompt. Also fetch shared CRM lists when available: accounts, contacts, opportunities, and campaign members. For entity-specific tasks, fetch the per-event, per-tradeshow, or per-import-batch detail endpoints before deriving totals.

Use [`scripts/fetch_harborcrm_snapshot.py`](scripts/fetch_harborcrm_snapshot.py) when a cached API snapshot would reduce mistakes:

```bash
python scripts/fetch_harborcrm_snapshot.py "$TASK_ENV_BASE_URL" \
  --common \
  --event-id "$EVENT_ID" \
  --show-id "$SHOW_ID" \
  --batch-id "$BATCH_ID" \
  --endpoint "/api/policies" \
  --out /tmp/harborcrm_snapshot.json
```

Only pass `--endpoint` paths that are allowed by the prompt or environment access file. The helper records 404s and continues, so inspect its `errors` section before assuming data is absent.

## Solving Workflow

Read [`references/harborcrm_rules.md`](references/harborcrm_rules.md) for the detailed rules before solving any nontrivial HarborCRM task.

Apply this high-level sequence:

1. Build lookup maps by account ID, account name, contact ID, normalized email, campaign member subject, event ID, show ID, and batch ID as applicable.
2. Normalize emails and phones before matching or deduplicating.
3. Choose the task family from the prompt and template:
   - Event handoff or post-event reconciliation.
   - Trade-show exhibitor prospecting.
   - Import-batch cleanup.
4. Derive rows from API records, not from example memory. If prompt rules conflict with general rules, follow the prompt and template.
5. Recompute every aggregate from the derived rows after sorting and exclusion decisions are final.
6. Validate the final object against the template shape and enum values.

## Output Checks

Before finalizing:

- Include exactly the top-level keys required by the template, unless the template explicitly allows more.
- Use `null` only where the template allows null; otherwise use an empty string, empty list, or integer zero as appropriate.
- Sort every list according to the prompt or template.
- Use integer USD amounts and integer counts.
- Recalculate totals from the output rows rather than copying intermediate notes.
- Return one JSON object only, with no Markdown fence and no explanatory prose.
