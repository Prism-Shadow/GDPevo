# Northstar Workflow Reference

Read this reference after `SKILL.md` when solving a Northstar payer-operations JSON task.

## Query Strategy

- Start from IDs in `task_context.json`: case IDs, appeal IDs, claim IDs, queue row IDs, document IDs, policy IDs, or reporting periods.
- Use `/api/tables` only to learn available table names/columns. Then run focused SQL queries that filter by target IDs, case IDs, claim IDs, appeal IDs, dates, service domain, plan, modifier, or scoped row IDs.
- Retrieve document bodies by document ID when clinical or packet evidence depends on narrative content.
- Join outward only as needed: case -> request lines -> authorization -> documents -> policy criteria; appeal -> trials/documents/assistance; claim -> lines -> rate schedules; queue IDs -> service margin rows.
- Treat the environment as authoritative over assumptions from labels or stale exports.

## Common Basis Audit Rules

Every audited output has:

- `source_precedence`: choose the template enum that describes why some records control over others.
- `controlling_record_ids`: IDs for environment records that directly determine the outcome or calculations.
- `exception_record_ids`: IDs, criterion IDs, gap IDs, or stale record IDs that explain missing information, unresolved criteria, route priority, exclusions, or adverse results.
- `precedence_record_order`: controlling and exception records in priority order, highest priority first.

Use operational evidence order for controlling IDs. Use business gap order for exceptions: unresolved criteria and route gaps before stale or excluded records when both appear.

## Prior Authorization Determinations

Use for UM nurse summaries and therapy authorization tasks.

- Prefer current clinical records over stale exports or older portal extracts.
- Evaluate each required policy criterion from the template. Typical criteria cover active coverage/benefit status, covered diagnosis, documented functional deficit, plan of care, and requested units.
- If all nurse-review criteria are met and the authorization record supports the requested service, recommend approval with the nurse route and approval letter/action.
- If required evidence is missing but could change the result, pend for information and list missing or unclear criteria.
- If nurse-review criteria fail or require clinical judgment outside nurse approval authority, route according to the template options.
- Populate approved authorization fields from the controlling authorization/request records. Order CPT/HCPCS codes exactly as the template requires.
- Put current clinical documents used in `evidence_documents`; put stale, superseded, or irrelevant case documents in `excluded_documents`.

## Pharmacy Appeals And Assistance

Use for coverage appeal and manufacturer assistance intake dispositions.

- Apply payer appeal facts before manufacturer assistance facts. Assistance status can affect packet gaps and next action, but it should not override the appeal path or appeal deadline.
- Determine appeal path, expedited flag, deadline, and owner from the appeal record, plan rules, denial date, risk attestations, and reporting date.
- Classify prior medication trials as documented only when the environment has adequate fill/claim or clinical evidence for the medication and failure rationale. Put incomplete or unsupported trials in the insufficient list.
- Required packet items should follow payer appeal items before assistance items. Missing packet items should list appeal evidence gaps before assistance information gaps.
- Assistance missing fields use the template's requested ordering, commonly alphabetical by field ID.
- Choose next action from unresolved payer gaps first, then assistance gaps. File or submit only when required evidence is complete.

## Claim Repricing

Use for payment-integrity correction packets.

- Choose the effective benchmark by plan, service date, CPT/HCPCS code, modifier, and schedule effective dates. Reject stale or inapplicable schedules even if their values appear in older exports.
- Keep claim lines in source claim-line order.
- For each line, match the rate row to CPT/HCPCS and modifier. A missing modifier in the claim should be JSON `null`.
- Compute `correct_allowed_amount = benchmark_allowed_amount * units`.
- Compute the correction amount as the nonnegative absolute dollar change between paid and correct allowed. Use `correct_upward` when the corrected amount is higher than paid, `correct_downward` when lower, and `no_change` when equal.
- `paid_total`, `correct_allowed_total`, and total correction/recovery fields must reconcile to the line sums.
- Round currency to two decimals after applying units.

## Peer-To-Peer Summaries

Use for completed P2P authorization summaries.

- Give priority to new patient-specific P2P information over earlier intent-to-deny status. Mark `new_information_changed_review` true only when the P2P supplied material evidence that changes criteria results or the final determination.
- Evaluate final criteria after the P2P event, not merely the pre-P2P status.
- List unresolved criterion IDs in the order required by the template. List missing modality-specific factors in the template's choice order.
- If the final result is adverse, calculate the internal appeal deadline from the final adverse determination date and the plan's stated appeal window. Use `null` only when no internal appeal deadline applies.
- Choose the recommended alternative from policy and clinical records when the requested service remains unsupported.

## UM-Finance Margin Queues

Use for service-margin queue summaries.

- Use only row IDs scoped in `task_context.json`, and preserve that row order in `rows`.
- Compute `total_cost = variable_cost + fixed_cost_allocated`.
- Compute `margin = revenue - total_cost`.
- Compute `revenue_to_cost_ratio = revenue / total_cost`, rounded to the template precision.
- A row is below threshold when its ratio is less than the threshold supplied in context/template.
- Keep charge-sensitive rows separate from below-threshold payer-service issues unless a row has both flags.
- Recommended action usually follows priority: below-threshold rows -> payer contract review; charge-sensitive rows -> monitor charge sensitive; otherwise -> monitor/no action.
- `below_threshold_segments` and `charge_sensitive_segments` follow the template's ordering, often alphabetical by enum value.
- `gap_to_120pct` or equivalent threshold gap is `threshold * total_cost - revenue` for the top below-threshold issue, rounded to cents. If there is no below-threshold issue, use the template's neutral value.
- For margin queues, threshold gaps control before charge-sensitivity monitoring in the audit order.

## Cross-Domain Priority

When a task combines appeal timing, clinical review, and payment-integrity issues, route by the task/template precedence. Appeal deadlines normally outrank clinical completion issues, and clinical issues normally outrank payment-integrity cleanup, unless the template or case facts state a different rule.
