# HarborCRM Pattern Guide

## Contents

- Shared rules
- Event and sponsor handoffs
- Badge and campaign-member reconciliation
- Trade-show prospecting
- Import batch cleanup
- Normalization
- Validation

## Shared Rules

- Treat the prompt as the source of business logic and the template as the source of schema.
- Use `/api/policies` whenever the prompt references controlled reasons, suppression, qualification, or timing.
- Never invent fields, rename enums, or output records that the template does not ask for.
- Recompute every summary from the final included rows.
- Sort each list exactly as the template says.

## Event and Sponsor Handoffs

- Classify sponsor records into the status buckets named by the template. The staged tasks use values such as `paid_deferred`, `open_invoice`, and `proposal_only`, with `not_sponsor` appearing in badge-level templates.
- Sum sponsor revenue by status from the sponsor package amount or equivalent status amount. If the template asks for open balance, sum that separately for open-invoice sponsors only.
- Qualified non-sponsor leads are business attendees that are not sponsor-attached, not already disqualified in CRM, and not otherwise excluded by policy.
- Excluded records belong in the exclusion list with the exact controlled reason from the template.
- For lead handoffs, use the event's lead opportunity amount once per qualified account or contact.
- Follow-up dates come from event or policy metadata. Use the exact source date; do not invent offsets.
- CRM action counts must match the final account, contact, and campaign-member actions implied by the included records.

## Badge and Campaign-Member Reconciliation

- When the template includes badge decisions, classify each badge as sponsor-attendee, qualified non-sponsor lead, or excluded as required.
- Sponsor-attendee rows stay out of the qualified lead set even when they still need a CRM contact or campaign-member action.
- Qualified badge leads should drive the account, contact, and campaign-member actions that the template allows.
- When the template includes a campaign-member action list, derive each action from the existing CRM membership state and the badge or contact record state.
- Badge-only contact facts should use the surviving lead row's normalized contact data.

## Trade-Show Prospecting

- Qualified exhibitors must match the campaign's platform and product-fit rules from the prompt or policy.
- If the prompt gives ranking keys, apply them in order and break remaining ties by company name ascending.
- If the prompt gives a priority-tier table, use it exactly for opportunity sizing.
- Platform lists use the template's enum order.
- Platform coverage counts count each platform occurrence across the qualified set, not unique companies.
- Existing CRM overlap counts and IDs include only qualified records that already match CRM accounts.
- Excluded exhibitors use the template's controlled reason enum.

## Import Batch Cleanup

- Build duplicate groups from the canonical duplicate key in the prompt or policy, usually normalized email and sometimes phone.
- Keep the winning row for each duplicate group by the task's precedence rule. If no precedence is stated, prefer the most recent `captured_at` among non-suppressed rows with the most complete usable data.
- Remove suppressed rows and missing-contact rows separately from duplicates.
- Clean contacts are the surviving unique rows only.
- Count import actions from the cleaned set, not from removed rows.

## Normalization

- Email: lowercase and trim whitespace.
- Phone: digits only.
- Preserve empty strings when the template allows them; do not synthesize placeholders.
- Keep dates in `YYYY-MM-DD` unless the template explicitly asks for timestamps.

## Validation

- Verify every sorted list against the required ordering.
- Verify every enum value against the template verbatim.
- Recompute counts, totals, and overlaps after all exclusions and deduplication.
- Return one JSON object only.
