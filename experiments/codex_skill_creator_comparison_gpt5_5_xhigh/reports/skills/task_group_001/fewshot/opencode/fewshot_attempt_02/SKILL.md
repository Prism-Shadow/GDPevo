---
name: harborcrm-handoff
description: Use for HarborCRM API tasks that require producing strict JSON handoffs from event, trade-show, import-batch, CRM, finance, sponsor, badge, exhibitor, meeting-interest, suppression, or campaign-member data. Apply this skill whenever a prompt mentions HarborCRM, CRM import preparation, sponsor finance handoff, event badge reconciliation, qualified lead/prospect lists, or trade-show exhibitor qualification, especially when an answer_template.json must be filled from a supplied API base URL.
---

# HarborCRM Handoff

Use this skill to turn HarborCRM API records into the exact JSON object requested by the task prompt and `input/payloads/answer_template.json`.

## First Pass

1. Read the user prompt and `input/payloads/answer_template.json` completely.
2. Identify the task family:
   - Event handoff: event details, sponsors/orders, badges, finance invoices, opportunities, campaign members.
   - Trade-show prospecting: exhibitors, meeting interest, CRM overlap, platform qualification.
   - Import batch cleanup: raw contacts, suppression, CRM account/contact matching, duplicate removal.
3. Resolve the API base URL supplied by the runner. Do not hard-code training URLs or IDs.
4. Fetch every endpoint named by the prompt for the requested event, show, or batch ID. Also fetch shared CRM tables when existing account, contact, opportunity, or campaign-member decisions are required.
5. Read [references/rules.md](references/rules.md) for the detailed reusable rules before making classification or counting decisions.
6. Use [scripts/harborcrm_helpers.py](scripts/harborcrm_helpers.py) for deterministic fetching, email/phone normalization, and exhibitor pre-classification when useful.

## API Handling

Prefer structured API reads over inference from names alone. Use endpoint paths exactly as the prompt gives them, preserving query strings:

```bash
python <skill-root>/scripts/harborcrm_helpers.py fetch "$TASK_ENV_BASE_URL" \
  /api/crm/accounts \
  /api/crm/contacts
```

If the prompt uses a placeholder such as `<TASK_ENV_BASE_URL>`, replace it with the runner-provided base URL. Strip one trailing slash from the base URL before joining paths.

If an endpoint is unavailable, do not invent records. Continue with the available prompt-named endpoints and record decisions only when supported by fetched data.

## Output Discipline

- Return one JSON object only, with no prose outside it.
- Follow the template's required keys, field names, enum values, nullability, and ordering rules exactly.
- Do not add convenience fields that are not declared by the template.
- Keep currency and count fields as integers.
- Use `null` only where the template allows it; otherwise use the requested empty string, zero, or enum.
- Sort every list by the template rule. If no rule is stated, use the most stable identifier in the schema, then company/account name.
- Recompute all totals and counts from the records included in the final output.

## Reconciliation Principles

- Normalize email as lowercase trimmed text.
- Normalize phone as digits only.
- Prefer explicit IDs from API records. When an ID is absent, match CRM accounts by exact normalized company name, obvious canonical company-name variants, or email/domain evidence. Treat disqualified CRM accounts as exclusions, not import/update targets.
- Preserve source-row facts in import-cleaning outputs unless the template asks for CRM canonical values.
- For conflicting records, make the reason visible through the template's controlled exclusion/action enum rather than dropping the record silently.

## Final Check

Before answering, verify:

- Every required top-level key from the template exists.
- Every enum value appears exactly as allowed.
- Every included record has evidence in the fetched API data.
- Excluded, duplicate, suppressed, and no-action records are counted consistently with the final arrays.
- The final JSON parses with `python -m json.tool`.
