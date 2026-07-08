# MedBridge Sales Ops Reconciliation Skill

Use this skill for MedBridge Sales Ops tasks that ask for account-ready JSON about RFQs, revised quotes, freight options, invoices, milestone revenue, payments, events, or vouchers.

## API Use

- Use the task-provided API base URL. Check `GET /health` only if availability is uncertain, then inspect `GET /api` for routes.
- Use public business routes only: `/api/customers`, `/api/products`, `/api/rfqs`, `/api/quotes`, `/api/freight-quotes`, `/api/policies`, `/api/opportunities`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`, and `/api/search?q=...`.
- Start with the exact ID in the prompt. Fetch the exact record by route when possible, then use search to collect linked records and detect distractors.
- Never infer from old RFQs, superseded requests, stale freight, or similarly named records when an exact quote/RFQ/opportunity exists.

## Source Precedence

- Prompt constraints and the exact target ID define the task scope.
- Current API records override customer notes, prior quote quantities, older RFQs, and prior unit prices.
- For revised quotes, use the quote `confirmed_quantity`, `quote_date`, `customer_id`, and `primary_product_code` or active line item product.
- For RFQs, use the RFQ `requested_modules` exactly. Component/composition details are medical or packing context unless the prompt explicitly asks for component-level pricing.
- For accounts, reconcile by `customer_id` and `opportunity_id`; only include invoices, payments, journals, events, and vouchers linked to both where available.

## Quote And RFQ Pricing

- Select the catalog `price_tiers` row where `min_qty <= confirmed/requested quantity <= max_qty`; a null `max_qty` means no upper limit.
- Use the selected tier unit price and lead time, not a prior quote price.
- `exw_total` or line total equals `quantity * unit_price`.
- Preserve the output template's field names and controlled values. Use numeric money values, not strings.
- For module RFQs, one output line equals one requested module line. Do not split into catalog components.
- If destination is pending or the prompt says indicative/no transport estimate, quote EXW only and exclude freight.
- Standard catalog quote validity is 30 calendar days from quote date unless the API gives a more specific override.

## Freight Rules

- Include freight records tied to the target `quote_id`; ignore distractor routes, wrong shipment sizes, old benchmarks, and unrelated records.
- Prefer active/current freight rows. If the template asks for warnings or visibility, include stale/expired rows but mark them stale/invalid.
- A freight option is valid on the quote date only when it is not stale and `valid_until >= quote_date`.
- Grand total equals EXW total plus that freight cost, even for a row shown only as a warned/invalid option.
- Use uppercase mode and risk values when the template uses controlled status style: `AIR`, `SEA`, `ROAD`, `LOW`, `MEDIUM`, `HIGH`.
- Use `NONE` for low-risk flags when a risk flag field is required and no special warning applies.
- Freight always requires reconfirmation at final order, even when current freight rows are valid.
- Recommended mode: choose the lowest-cost valid/current option unless route risk, cold-chain suitability, short validity, or prompt urgency makes a safer active mode more appropriate. Reflection favored SEA over AIR when SEA was current, materially cheaper, cold-chain capable, and only medium risk; never recommend stale/expired road freight.

## Payment And Policy Rules

- New NGO/prospect accounts use `PREPAY_100`.
- Recurring NGO accounts use `NET_30_AFTER_PO` unless a customer-specific restriction says otherwise.
- Recurring commercial/customer records with `payment_profile` already set should use that profile when it is an accepted terms code.
- EXW excludes freight, insurance, import duty, customs clearance, and last-mile handling unless freight is explicitly shown as separate options.

## Account Reconciliation

- Map opportunity `closed_won` to `WON`; use `OPEN` or `LOST` only when source stage supports it.
- `opportunity_matches_phase_total` is true when won amount equals the sum of opportunity phase amounts or matched invoice milestone totals.
- Outstanding balance comes from the opportunity or sum of linked invoice outstanding amounts; verify the two agree when both exist.
- Milestone payment status:
  - `PAID`: invoice paid amount equals invoice amount and posted payment exists.
  - `PARTIAL`: paid amount is greater than zero but less than invoice amount.
  - `UNPAID`/`OPEN`: no posted payment and outstanding amount remains.
- Revenue recognition:
  - Paid, completed milestone with a posted revenue journal: `RECOGNIZED`.
  - Paid, completed milestone missing a journal: `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`.
  - Unpaid future or unpaid outstanding milestone: `NOT_REQUIRED_UNPAID`.
- Revenue actions should record only the paid completed milestone that is missing a journal, with debit `DEFERRED_REVENUE` and credit `IMPLEMENTATION_SERVICES_REVENUE`.
- For fixed milestone templates using `MS1`, `MS2`, `MS3`, map them by ascending opportunity phase order rather than by source phase ID text.
- Collection follow-up for unpaid not-yet-due milestones should use `MONITOR_UNPAID_NOT_DUE` and account-management ownership when the template supports it; send collection notices only for due or overdue unpaid milestones.

## Event And Voucher Rules

- Link events and vouchers by both `opportunity_id` and `customer_id`; also confirm the event's `voucher_code` matches the voucher record.
- Map event and voucher statuses to the template's uppercase enum values.
- Use voucher `discount_percent` as the voucher discount value when no separate currency discount field exists.
- Use voucher `max_redemptions` for max-use fields.
- If the prompt says the invitation has not gone out yet, use the send-invite action and the named customer contact from the source records.

## Output Discipline

- Return only JSON matching the supplied answer template. Do not add markdown or narrative.
- Keep dates as ISO `YYYY-MM-DD`; use null only where the template permits it.
- Keep money as numbers with cent-level precision. Recalculate totals rather than copying inconsistent notes.
- Preserve template array order when it is specified; otherwise follow source order or a natural mode/milestone order.
- Avoid raw API fields that are not requested.
