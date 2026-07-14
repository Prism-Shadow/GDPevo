# AsterOps Data-Quality Audit Skill

Use this skill for AsterOps audit tasks that ask for a single JSON answer from a remote workbench plus a local `input/payloads/answer_template.json`.

## Workflow

1. Read only the task prompt, the answer template, and any allowed environment access file in the current attempt directory.
2. Use the workbench catalog first to identify public API endpoints, filters, reference tables, and CSV downloads.
3. Pull scoped API records with the exact business filter from the prompt: batch, campaign, wave, region/period, scope/period, or similar.
4. Use CSV downloads only when the prompt or template asks for snapshot, lineage, or source reconciliation. Treat current API records as authoritative for operational totals unless the template says otherwise.
5. Build the answer directly from the template. Keep required keys, enum labels, nested object shapes, and zero-valued required fields.
6. Return JSON only for task answers.

Do not read local environment source, evaluator files, test materials, notes, or files outside the solver attempt directory.

## General Output Conventions

- Sort ID lists lexicographically ascending unless the template states a different order.
- Sort object arrays by the template key, usually `person_key`, `purchase_id`, `event_id`, `charge_id`, `transaction_key`, or `vehicle_id`.
- Include all required enum buckets with `0` even when absent.
- Use empty lists for no IDs and empty strings for unavailable normalized contact fields.
- Preserve exact controlled enum spellings from the template and reference APIs.
- For money, report USD to two decimals. For currency conversion, convert each included line with the reference rate, round that line to cents, then aggregate.
- For gallon totals, aggregate included effective records and round to two decimals.
- Use integer counts with no decimal places.

## Effective Records

- `posted` records are effective unless replaced or invalid.
- `amended` records are retained as the effective replacement; their `amends_*` target is superseded.
- `void` records are excluded from totals and listed separately when requested.
- Superseded records are excluded from totals even if a stale CSV snapshot still shows them as posted.
- Invalid value records are excluded from financial or operational totals, but still count in invalid issue summaries.
- Background-looking IDs still count when they satisfy the task scope. Do not restrict analysis to the hand-authored sample IDs.

## CRM Contact Audits

- Normalize emails by trimming and lowercasing.
- Normalize phones by stripping all non-digits. Preserve country code digits when present.
- A source row is suppressed when `contact_status` is `do_not_contact` or `consent_status` is `revoked`.
- Suppressed-only people can still appear in canonical person accounting with `contact_status: "suppressed"`.
- When selecting active duplicate lineage, remove suppressed source rows before reporting lineage source IDs for a retained corrected person.
- Prefer active steward corrections when present. Otherwise use source precedence, with `crm_verified` outranking `event_import` for canonical contact selection.
- Unknown consent is not by itself a hard block when the contact is active and reachable.
- A canonical person with no normalized email and no normalized phone is `dropped_unreachable`.
- Quality counts are source-row based: duplicate source rows are rows beyond the first in each duplicate `person_key` group; normalization counts include only nonblank fields that changed.

## CRM Campaign Audiences

- Reconcile campaign members to canonical CRM contacts by `person_key`.
- Hard block bounced or unsubscribed campaign members, revoked consent, do-not-contact rows, and suppression notes.
- Duplicate campaign members are not automatically hard blocked. Keep the noncanonical duplicate member IDs in manual review and retain the best actionable member when the canonical contact is reachable.
- For duplicate campaign members, prefer higher engagement/actionability, then score, while keeping the duplicate person key in the audit.
- Segment normalization is case/space tolerant: enterprise renewal, strategic renewal, SMB churn risk, partner, ops lead, otherwise unknown.
- Domain counts use the retained canonical email domain after trim/lowercase.

## Fuel Purchase Audits

- Resolve fuel aliases by case-insensitive substring matching against product description, choosing the highest-priority alias.
- Track priority overlaps when multiple aliases match. Track generic unleaded traps when generic `unleaded` also matches a more specific unleaded alias.
- Compare observed canonical fuel to the vehicle expected fuel.
- Vehicle exceptions remove a mismatched purchase from the mismatch queue but still keep it in effective fuel totals.
- Zero-gallon effective purchases remain in the evaluated set and audit lists.
- For API-vs-CSV reconciliation, use the API as current state. CSV-only and stale CSV records are excluded from operational totals and should be isolated in source-delta fields when requested.

## Logistics Cost Audits

- Exclude non-void records with negative amounts, missing amounts, invalid units, or invalid currencies from corrected totals.
- Count void records separately from invalid records.
- Use the currency reference rates exactly. Convert and round each included event to cents before summing totals by cost type and lane.
- `non_usd_currency` diagnostics and non-USD samples should be based on included effective non-USD events, not invalid or void records.
- `advisory_note` counts non-invalid quality notes on source events.
- Unit counts are counts of included effective events by controlled source unit after exclusions.

## Facilities Charge Audits

- Resolve facilities category from `raw_category` using the category alias reference. Do not let description phrases such as fuel surcharge, detention, or monthly service override the raw category unless the template explicitly instructs that behavior.
- Retain amended charges and exclude the original superseded charge from spend.
- Keep invalid IDs separate from superseded IDs.
- Spend by vendor and category is based only on effective retained charges.
- Do not invent source-conflict review reasons from description text unless the task explicitly defines that field behavior.

## Common Pitfalls

- Do not drop a whole CRM person just because one duplicate row is suppressed; an active steward correction can still retain the person.
- Do not include suppressed rows in retained duplicate lineage evidence after suppression has removed them from canonical selection.
- Do not count invalid logistics rows in non-USD diagnostics once they are excluded from the effective set.
- Do not ignore generated/background records that match the scoped API filter.
- Do not classify facilities charges from description text when `raw_category` has a usable alias.
