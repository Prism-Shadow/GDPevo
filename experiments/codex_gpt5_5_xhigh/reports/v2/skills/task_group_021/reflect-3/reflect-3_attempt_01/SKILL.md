---
name: asterops-data-quality-audits
description: Solve AsterOps data-quality audit tasks that require querying a remote workbench, reconciling API records with CSV exports, applying CRM/contact, fleet fuel, logistics cost, facilities charge, alias, suppression, amendment, normalization, rounding, and JSON answer-template rules.
---

# AsterOps Data Quality Audits

## Workflow

1. Read the task prompt and `input/payloads/answer_template.json` first. Treat the template as the contract for keys, enums, ordering, rounding, and whether counts are based on raw rows, effective rows, canonical people, or retained output rows.
2. Use only the remote workbench surfaces named by the task. Start with the catalog, then query the relevant API endpoints with the task's business filters such as `batch_id`, `campaign_id`, `wave_id`, `scope`, `period`, `region`, or `person_key`.
3. Pull CSV downloads only when the prompt or template asks for export/source reconciliation. Treat the current API as the operational record unless the template explicitly says a CSV snapshot drives the metric.
4. Build a small local calculation table with normalized fields, effective-record status, canonical category/fuel/person decisions, and review reasons. Use `Decimal` for money and gallon math.
5. Emit one JSON object only. Keep required keys present, include required zero-valued enum keys, and sort every list exactly as the template says.

## Scope Rules

- Prefer explicit business filters from the prompt/template over cosmetic ID prefixes. Background-looking IDs can still be in scope when they match the target filter.
- Do not add an implicit date bound just because an identifier contains a quarter or month. Apply date/period filters only when the prompt, endpoint filter, or template calls for them.
- For CSV reconciliation, compare rows by stable business keys such as transaction keys or charge/event IDs, then classify API-only current rows, CSV-only legacy rows, stale CSV rows, and source disagreements separately.
- For samples named `canonical_*_sample`, include all retained/effective rows when the dataset is small unless the template gives an explicit sample limit.

## CRM Contacts

- Normalize email with outer whitespace trim plus lowercase. Normalize phone with digits only; preserve country-code digits if present in the source.
- Treat `contact_status=do_not_contact`, `consent_status=revoked`, bounced campaign members, and unsubscribed campaign members as hard blocks/suppression evidence.
- Prefer active steward corrections and trusted CRM records over newer but lower-precedence imports. Do not choose newest source row blindly.
- Keep hard-suppressed source row IDs in suppression audit fields. For duplicate lineage and duplicate-source overage, remove hard-suppressed source rows before deciding the canonical duplicate lineage unless the field specifically asks for raw source rows.
- Count retained-city, domain, and segment aggregates from retained reachable canonical people only.

## Campaign Audiences

- Reconcile campaign members to canonical CRM contacts by `person_key`.
- For duplicate campaign members, retain one canonical member when the person is otherwise reachable; place the noncanonical duplicate member IDs in manual review. Prefer stronger engagement/status and score, for example attended over registered.
- Keep hard-blocked or suppressed member IDs separate from manual-review IDs.
- Map raw segments conservatively: enterprise renewal, strategic renewal, SMB churn risk, partner, ops lead, then `unknown`. Include all required segment keys with zeroes.

## Fleet Fuel Audits

- Resolve product descriptions with the fuel alias reference using normalized lowercase substring matching. When multiple aliases match, select the highest priority alias.
- Flag generic-unleaded traps when `unleaded` co-matches a more specific unleaded alias. Keep alias-priority and generic-trap audit lists separate even when the same purchase appears in both.
- Build effective purchase records by excluding void/superseded rows and retaining amendment rows. Keep superseded and amended IDs in their own audit lists.
- Compare observed canonical fuel to the vehicle's expected fuel. Do not treat every non-`none` vehicle exemption as a blanket waiver; verify that the exception actually explains the mismatch.
- Gallon totals use effective current records and are rounded to two decimals.

## Logistics Cost Audits

- Effective cost events are non-void, non-superseded, and free of invalid amount, unit, and currency issues.
- Invalid event IDs exclude ordinary voided or superseded records. If an event has multiple invalid issue types, list issue types in template enum order.
- Convert each included event to USD using the quality-rule rates and round that event to cents before aggregation. Then sum rounded cents for totals by cost type and lane.
- Count unit totals from included effective events only.
- Count non-USD diagnostics and choose non-USD samples after integrity exclusions. Advisory quality notes, such as detention-style notes, are counted separately from invalid data.

## Facilities Charge Audits

- Use the task's `scope` and `period` together; include all records returned for that slice, not only task-looking IDs.
- Exclude void/superseded charge rows from effective spend and count them in `superseded_charge_ids` or review reasons as requested.
- Resolve the canonical category from the declared raw category alias first. Use description text as context and evidence for review reasons, not as an automatic override, unless the task's rules explicitly make descriptions part of category selection.
- Spend totals and top-vendor totals use effective charges only and are rounded to cents.
- Keep canonical charge samples sorted by `charge_id`; review reason lists use enum-label ascending order.

## Output Conventions

- Preserve enum spelling exactly from the template.
- Sort IDs lexicographically ascending unless the template gives another ordering. Sort object lists by the specified key sequence.
- Include required category/fuel/cost/segment keys even when their values are `0` or `0.00`.
- For money and gallon values, report two decimal places conceptually; JSON numbers may not display trailing zeroes, but the calculations must be cent/two-decimal exact.
- Top-N maps use the template's ordering, usually count descending then name ascending for ties.
- Distinguish raw-row issue counts from effective-row counts. Suppression, void, normalization, and advisory counts often come from source rows; retained aggregates come from canonical effective rows.

## Common Pitfalls

- Newest source row is not necessarily canonical; source precedence and steward corrections can override recency.
- Suppression can affect lineage differently from suppression reporting: a row can be excluded from duplicate lineage but still required in suppression evidence.
- Broad workbench endpoints may return distractor rows that are still valid if they match the task's business filter. Conversely, CSV exports may contain legacy or stale rows that should be audit evidence rather than loaded metrics.
- Do not mix invalid or void records into financial/fuel totals, non-USD diagnostics, or effective samples unless the template explicitly asks for raw-source counts.
