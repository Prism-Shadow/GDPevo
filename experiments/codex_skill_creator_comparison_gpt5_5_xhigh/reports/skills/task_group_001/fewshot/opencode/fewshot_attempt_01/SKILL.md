---
name: harborcrm-reconciliation
description: Prepare JSON-only HarborCRM handoffs, lead-qualified prospecting summaries, and import-batch reconciliations from event, show, or batch API data. Use this whenever a prompt mentions HarborCRM, a specific event/show/batch ID, sponsor statuses, lead handoff, sponsor finance, qualified leads, badges, exhibitors, campaign members, imported contacts, duplicate cleanup, suppression, policies, or an `answer_template.json` that must be matched exactly.
---

# HarborCRM Reconciliation

Use this skill for structured HarborCRM tasks where the goal is to turn scoped API data into one exact JSON object. The common pattern is the same across event handoffs, trade-show prospecting, and import cleanup: read the template first, pull only the prompt-specified data, apply the policy rules, normalize records, and emit JSON only.

## Core workflow

1. Read the prompt and `input/payloads/answer_template.json` before anything else.
2. Identify the task family:
   - event handoff / sponsor reconciliation
   - trade-show prospecting / exhibitor qualification
   - import-batch cleanup / dedupe / suppression
3. Use the runner-supplied HarborCRM base URL and only the public endpoints named in the prompt.
4. Pull the scoped records for the event, show, or batch, plus the supporting CRM and policy data the prompt calls for.
5. Normalize identifiers, contact fields, dates, counts, and money values.
6. Apply the prompt's business rules and the policy data. Do not guess beyond what the source data supports.
7. Build the final object to match the template exactly.
8. Sanity-check ordering, enum values, null handling, and totals before you answer.

## Output rules

- Return one JSON object only.
- Do not add prose, markdown, fences, or extra keys.
- Match the template's field names exactly.
- Preserve the template's required ordering for lists and nested lists.
- Use the template's controlled values exactly as written. Do not invent synonyms.
- Keep currency as integer USD unless the template says otherwise.
- Use `null` where the template expects `null`, not empty strings.
- Treat every run as task-specific. Never reuse prior example values or hardcode training data.

## Normalization rules

- Lowercase and trim email addresses.
- Strip phone numbers to digits only.
- Keep missing optional strings as empty strings only when the template allows them.
- Keep IDs, company names, and contact names exactly as sourced unless the prompt asks you to normalize them.
- Use deterministic sorting whenever the template specifies an order. If the template does not specify one, choose a stable ascending order by the primary label or ID and keep it consistent.

## Classification rules

- Use the prompt and policy data as the authority for qualification and exclusion.
- Prefer explicit CRM overlap checks over name matching.
- Mark existing CRM entities for update when the prompt says to preserve them.
- Mark new entities for creation when no CRM match exists and the record is qualified.
- Mark excluded records with the controlled reason set required by the template.
- Keep near misses visible when the template asks for them instead of hiding them.

## Event handoff pattern

Use this pattern when the prompt is about event sponsor reconciliation or sales handoff.

- Read event-level data, sponsor orders, badges, sponsor packages, invoices, CRM accounts, CRM contacts, opportunities, campaign members, and policies as needed by the prompt.
- Separate active sponsor records from qualified non-sponsor leads.
- Exclude sponsor attendees, inactive or canceled sponsor records, non-business badges, and already-disqualified CRM accounts when the prompt calls for those filters.
- Summarize sponsor revenue by status and keep open balances separate when required.
- Use the event's lead opportunity amount or the prompt's stated value for each qualified non-sponsor account.
- Report follow-up due dates and task counts only for the handoff items the prompt asks for.
- Include CRM action counts for the account, contact, and campaign-member work implied by the handoff.

## Trade-show prospecting pattern

Use this pattern when the prompt is about exhibitor qualification or campaign prospecting.

- Read trade-show exhibitors, meeting-interest data, CRM accounts, CRM contacts, and policies.
- Qualify only exhibitors that match the campaign policy.
- Preserve platform coverage exactly as the template allows.
- Sort qualified leads and exclusions exactly as the template says.
- Set create/update/no-import actions from CRM overlap and prompt rules.
- Rank leads using the prompt's stated priority logic, such as demo request, interest score, platform breadth, or company name.
- Size opportunities only by the prompt's stated tier rules.

## Import-batch cleanup pattern

Use this pattern when the prompt is about cleaning an import batch or preparing a batch campaign import.

- Read the batch's raw contacts, suppression list, CRM accounts, CRM contacts, and policies.
- Resolve duplicates before counting surviving contacts.
- Keep the winning row's source data on the cleaned record.
- Separate duplicate, suppressed, and unusable rows in the removal summary when the template asks for them.
- Normalize the surviving contacts so they can be imported cleanly.
- Report import-action totals and campaign-member counts from the surviving cleaned set only.

## Final check

Before you answer, ask:

- Did I use only the scoped data and prompt-listed endpoints?
- Did I follow the template exactly?
- Did I exclude every record the prompt or policy says to exclude?
- Did I keep all counts, totals, and money values internally consistent?
- Did I return JSON only?
