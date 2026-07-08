# SKILL: MedBridge Sales-Ops — B2B Quote & Engagement-Reconciliation Solver

## What this is / when it applies
You get ONE task: an email-style `prompt.txt` from an account manager plus an
`answer_template.json`. You must return ONLY a JSON object that exactly matches
the template (same keys, same shape, no markdown, no prose). All business facts
come from a single read-only HTTP API ("MedBridge Sales Ops"). There are no gold
answers and no judge — you must derive the answer yourself from live API data.

The domain has THREE task families (detect by the template + prompt):
1. **EXW + freight decision package** — a confirmed catalog quote with a
   destination; output catalog pricing + 3 freight options + recommended mode +
   policy flags. (template has `freight_options[]` with AIR/SEA/ROAD and a
   `policy_flags`/`transport_decisions` block.)
2. **Module / RFQ EXW-only quote** — an indicative RFQ with NO destination;
   output module-level line items, EXW only, freight excluded. (template has
   `quote_header.quote_basis = "EXW_ONLY"`, `line_items[]`, `quote_controls`.)
3. **CRM milestone / engagement reconciliation** — reconcile a won opportunity's
   phases vs invoices/payments/revenue-journals, plus a linked event+voucher,
   then route follow-up tasks. (template has `milestones[]`, `revenue_recognition`,
   `event`, `follow_up_tasks` / `invoice_actions` / `event_actions`.)

---

## The API
Base URL: provided by the runner (env var like `API_BASE_URL`/`BASE_URL`/`PORT`,
or for reference `<remote-env-url>`). Read-only JSON over GET.
Use `curl` or python `urllib` (it is a NETWORK resource, querying is expected).

Collections (list = `/api/<coll>`, single = `/api/<coll>/<id>`):
`customers, products, rfqs, quotes, freight-quotes, policies, opportunities,
invoices, payments, revenue-journals, events, vouchers`.
Also `GET /api/search?q=<text>` = full-text across all collections (great for
resolving an ID mentioned in the prompt to its record and linked records).

Filtering: list endpoints accept `?field=value`, nested keys flattened, matched
case-insensitively, numbers also match 2-decimal form. KNOWN GOTCHAS:
- `freight-quotes` are linked to quotes by **`quote_id`**, NOT `customer_id`.
  Use `?quote_id=<QUOTE_ID>` (filtering freight by customer_id returns 0).
- `invoices`, `payments`, `revenue-journals` carry both `opportunity_id` and
  `phase_id` (and `invoice_id`). Filter by `?opportunity_id=<OPP>` or just pull
  the whole small collection and match in code.

### Resolving IDs from the prompt
The prompt names the key record IDs directly (quote `Q-...`, rfq `RFQ-...`,
opportunity `OPP-...`, customer `CUST-...`, event `EVT-...`, voucher code).
Fetch that record first, then follow its foreign keys:
- quote → `customer_id`, `primary_product_code`, `confirmed_quantity`, `quote_date`.
- rfq → `customer_id`, `requested_modules[]` (each `product_code`+`quantity`).
- opportunity → `customer_id`, `phases[]` (each `phase_id`, `amount_usd`,
  `invoice_id`, `completion_date`, `name`), `won_amount_usd`, `stage`, `contact`.
Use the **API record's own values** (e.g. customer `name`) even if the prompt's
wording differs slightly (prompts sometimes paraphrase the customer name).

---

## FAMILY 1 — EXW + freight decision package (SOP)
Example shape: `Q-TR-WC-1187`, `Q-TR-LD-5521`.

1. GET the quote. Read `customer_id`, `primary_product_code`,
   `confirmed_quantity` (use the CONFIRMED/revised qty, not `prior_quote_quantity`),
   `quote_date`, `destination`.
2. GET the product. Pick the **price tier** whose `[min_qty, max_qty]` contains
   the confirmed quantity (`max_qty: null` = open-ended top tier). From that tier
   take `unit_price_usd`, `lead_time_days`, and the product's `shelf_life_months`.
   The confirmed qty's tier OVERRIDES any prior unit price in the quote.
3. `exw_total_usd = unit_price_usd * confirmed_quantity` (round 2 decimals).
4. GET freight via `?quote_id=<QUOTE_ID>`. Keep exactly the **real** AIR/SEA/ROAD
   option for this quote and DROP distractors. A record is a distractor if any:
   `id` contains `DIS`, `destination == "Distractor route"`, or `status` is
   `stale`/`mismatch` (also `expired` valid_until). Keep `status: active` ones
   that match the real destination/shipment. (You expect one each AIR/SEA/ROAD;
   a stale/expired ROAD is still REPORTED but flagged — see below.)
5. For each kept option compute `grand_total_usd = exw_total_usd + cost_usd`.
   Map fields: `freight_id=id`, `mode` = uppercased `mode`
   (air→AIR, sea→SEA, road→ROAD), `freight_cost_usd=cost_usd`,
   `transit_days = transit_days_text` (string like "4-6 days"),
   `valid_until`, plus risk fields (below).
6. **Risk fields.** `route_risk` (low/medium/high) → `risk_level`
   (LOW/MEDIUM/HIGH). `risk_flag` / `customs_border_risk`:
   - low route_risk → `NONE` (or "" / LOW depending on template default).
   - medium route_risk with border/customs note → `MEDIUM_BORDER_RISK`.
   - high route_risk → `HIGH_BORDER_RISK` / `HIGH`.
   Follow the template's own enum spelling and per-row defaults: the template's
   placeholder rows usually pre-fill the expected `risk_level`/`risk_flag` per
   mode — honor that pattern.
7. **Validity / staleness.** A freight option is VALID on the quote date iff
   `valid_until >= quote_date`. If a ROAD (or any) quote's `status` is `stale`
   or `valid_until < quote_date`, it is stale/expired:
   - `validity_status` = "VALID" vs "EXPIRED"/"STALE"; `source_is_stale=true`;
   - set the family's stale-warning boolean (e.g. `road_quote_invalid_or_stale`)
     = true and write a `freight_warning` describing it (e.g. road quote expired
     before quote date / customs risk high — reconfirm before PO).
   `all_freight_options_valid_on_quote_date` = true only if EVERY reported
   option is valid on the quote date.
8. **recommended_mode.** Recommend the **cheapest** (lowest `grand_total_usd`)
   option that is BOTH valid on the quote date AND low route-risk (avoid
   medium/high risk and stale options). Respect cold-chain: if the product has
   `cold_chain_required: true`, the recommended option must have
   `cold_chain_support: true`. (Worked examples: WC-360 → SEA is lowest-cost
   LOW-risk valid → recommend SEA; LD-1000 with stale/high ROAD and medium SEA →
   AIR is the cheapest LOW-risk valid cold-chain option → recommend AIR.)
9. **Policy flags.** `freight_reconfirmation_required = true` (policy
   POL-FREIGHT-RECONFIRM — freight always reconfirmed at order). `quote_basis`
   = "EXW" / "EXW plus freight options" per template. `payment_terms` &
   `customer_policy`: see Payment-terms rules below.

## FAMILY 2 — Module / RFQ EXW-only quote (SOP)
Example: `RFQ-TR-IEHK-204` (new NGO, no destination).

1. GET the rfq. Read `customer_id`, `quote_date`, `requested_modules[]`.
2. Quote at **module line level only**. IGNORE component-composition /
   distractor tables — do NOT split modules into component SKUs (policy
   POL-MODULE-GRANULARITY). One `line_items[]` entry per requested module.
3. For each module GET the product: `product_code` (=code), `article_number`,
   `quantity` (from the RFQ line), single-tier `unit_price`,
   `lead_time_days`, `shelf_life_months`, and
   `line_total = unit_price * quantity`.
4. `grand_total = sum(line_total)`. `currency="USD"`,
   `quote_basis="EXW_ONLY"`, `freight_excluded=true` (no destination → EXW only,
   policy POL-INDICATIVE-EXW / POL-EXW-SCOPE).
5. `payment_terms` = `PREPAY_100` for a NEW NGO / new-client account
   (`payment_profile: NEW_CLIENT_REVIEW`, policy POL-NEW-CLIENT-PAYMENT).
6. `offer_validity_days` = 30 (POL-QUOTE-VALIDITY, catalog pricing valid 30
   calendar days). `who_documentation_required` = true for NGO/emergency-health
   (WHO/donor docs) unless the data says otherwise.

## FAMILY 3 — CRM milestone / engagement reconciliation (SOP)
Examples: `OPP-TR-HELIOS`, `OPP-TR-MERIDIAN`.

1. GET the opportunity + customer. `stage`: `closed_won`→WON, open→OPEN,
   lost→LOST. `won_amount` = `won_amount_usd`. `customer_name` from the customer
   record. `primary_contact` = opportunity `contact` (also the prompt names them).
2. **Phase ↔ milestone totals.** `phase_total_amount` = sum of phase
   `amount_usd`. `opportunity_matches_milestones`/`opportunity_matches_phase_total`
   = (won_amount == phase_total). (Both worked examples matched.)
3. For EACH phase, gather its invoice (by `invoice_id`/`phase_id`), its
   payment(s), and its revenue-journal:
   - `invoice_total`/`amount` = invoice `amount_usd`.
   - `invoice_state`: invoice `status` → PAID/OPEN(unpaid)/VOID; map
     `unpaid`→UNPAID/OPEN, `paid`→PAID, `draft`→OPEN/UNKNOWN, `overdue`→OPEN
     (still unpaid). Use the template's enum set.
   - `paid_amount`/`amount_paid` = invoice `paid_amount_usd` (or sum of posted
     payments for that invoice). `amount_unpaid` = `outstanding_amount_usd`.
   - `payment_state`: PAID if fully paid, PARTIAL if 0<paid<amount, else UNPAID.
   - `due_date`: invoice `due_date`. CONVENTION: for a PAID milestone many
     templates expect `due_date: null` (it is settled — no due date applies);
     for UNPAID/open milestones report the invoice `due_date`. Honor whichever
     the template's wording implies; default = null once paid.
   - `recognition_status` per phase:
     * paid milestone WITH a revenue-journal → `RECOGNIZED`.
     * paid milestone WITHOUT a revenue-journal → `REQUIRED_MISSING` /
       `MISSING_REVENUE_JOURNAL`.
     * unpaid milestone → `NOT_REQUIRED_UNPAID` (recognize only paid+complete
       milestones — policy POL-REVREC).
4. **Rollups.** `total_paid_amount` = sum of fully/partly paid amounts.
   `outstanding_balance` = sum of unpaid invoice outstanding =
   opportunity `outstanding_amount_usd`. `recognized_amount` = sum of amounts of
   milestones that actually have posted revenue-journals.
   `recognition_status` (engagement-level):
   * all paid milestones recognized → `COMPLETE_FOR_PAID_MILESTONES`.
   * some paid milestone missing its journal → `MISSING_FOR_PAID_MILESTONES`.
   * no paid milestones → `NOT_REQUIRED`.
5. **Event + voucher.** GET the event (by id or `?opportunity_id=`) and its
   `voucher_code` → GET voucher. `event_date`, `voucher_discount`/`discount_amount`
   = `discount_percent`, `voucher_max_uses`/`max_uses` = `max_redemptions`.
   `event_status`: live→ACTIVE, scheduled→SCHEDULED, confirmed→SCHEDULED,
   completed→COMPLETED, cancelled→CANCELLED, else UNKNOWN.
   `voucher_status`: active→ACTIVE, draft→DRAFT, expired→EXPIRED,
   disabled→DISABLED, else UNKNOWN.
6. **Action routing** (use the task's `as_of_date`/current business date — read
   it from the prompt, e.g. "treat 2026-06-01 as current"):
   - **Accounting action**: if a paid milestone is MISSING its revenue journal →
     `RECORD_REVENUE_<MSx>` (e.g. RECORD_REVENUE_MS2), `milestone_id`=that MS,
     `amount`=its amount, `debit_account=DEFERRED_REVENUE`,
     `credit_account=IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue=ACCOUNTING`.
     If all paid milestones already recognized → `VERIFY_REVENUE_ONLY` (or
     NO_ACCOUNTING_ACTION) with milestone NONE / amount 0 / accounts NONE.
   - **Collection action**: take the earliest UNPAID milestone with a future
     invoice. If its `due_date` is in the future (as-of < due) →
     `MONITOR_UNPAID_NOT_DUE`, owner `ACCOUNT_MANAGEMENT`. If overdue
     (as-of > due) → `SEND_COLLECTION_NOTICE`, owner `COLLECTIONS`. If nothing
     unpaid → `NO_COLLECTION_ACTION`/NONE. Fill `milestone_id`, `amount`,
     `due_date`, `contact_name`.
   - **Event/invite action**: scheduled/confirmed event not yet sent →
     `SEND_BRIEFING_INVITE`/`SEND_EVENT_INVITATION`, owner `ACCOUNT_MANAGEMENT`,
     with `event_id`, `voucher_code`, `contact_name`, `customer_id`. Completed →
     VERIFY/NO action.
   - `follow_up_tasks[]` (HELIOS-style template): emit ONE COLLECTION task per
     unpaid-and-due milestone (`next_action=COLLECT_UNPAID_MILESTONE`,
     `amount_due`, `milestone_id`, `due_date`=invoice due date) and ONE
     EVENT_INVITATION task (`next_action=SEND_EVENT_INVITATION`, `event_id`,
     `voucher_code`, `due_date`=event_date or a sensible lead date), both tied to
     the named account contact and customer/opportunity IDs.

### Milestone-ID naming (IMPORTANT, differs by template)
- If the template's `milestone_id` enum is `MS1 | MS2 | MS3`, NORMALIZE: order
  phases ascending by phase order and label them MS1, MS2, MS3 (NOT the raw
  `phase_id`). The accounting action then says e.g. `RECORD_REVENUE_MS2`.
- If the template says "stable phase or invoice milestone id", use the raw
  `phase_id` (e.g. `HEL-P1`) or invoice id as given.

---

## Output conventions (all families)
- Return ONLY the JSON object matching the template — no markdown fences, no
  commentary. Keep every key in the template; do not add keys.
- Money: numbers with 2 decimals (e.g. `42480.0`), USD. Totals MUST reconcile:
  `exw_total = unit_price*qty`; `grand_total = exw_total + freight_cost`;
  `phase_total = sum(phase amounts)`; `outstanding = sum(unpaid outstanding)`;
  `recognized_amount = sum(amounts with posted journals)`.
- Dates: ISO `YYYY-MM-DD`. Enums: use EXACTLY the controlled values listed in
  that template field's annotation (their spelling/casing wins over this doc).
- `null` usage: use null where the template says "string or null" / "number or
  null" and the fact doesn't apply (e.g. paid-milestone due_date,
  no-collection milestone_id/amount, no-event fields). Don't invent zeros/blanks
  where null is the right "not applicable" marker.
- `transit_days` is a STRING (e.g. "4-6 days"), taken from `transit_days_text`.

## Common misjudgments to avoid
- Filtering freight by `customer_id` (returns 0) — use `quote_id`.
- Including distractor / stale / wrong-shipment freight rows (`id` has DIS,
  destination "Distractor route", `status` stale/mismatch). Keep the real
  active AIR/SEA/ROAD for the quote.
- Using `prior_quote_quantity`/`prior_unit_price_usd` instead of the CONFIRMED
  quantity and its catalog tier (the tier overrides prior pricing).
- Expanding module RFQs into component SKUs — keep module-level lines only.
- Adding freight to an indicative/no-destination RFQ — EXW only, freight excluded.
- Recommending a cheaper but stale/expired or higher-risk freight mode — the
  recommendation must be valid AND low-risk (and cold-chain-safe if required).
- Recognizing revenue for UNPAID milestones — recognize only PAID+complete ones;
  unpaid = NOT_REQUIRED_UNPAID and drives collection (not accounting) tasks.
- Treating a paid milestone that is simply missing its journal as "complete" —
  that is the MISSING/REQUIRED_MISSING case and triggers RECORD_REVENUE.
- Confusing collection vs accounting routing: missing-journal-on-paid → ACCOUNTING
  (record revenue); unpaid invoice → ACCOUNT_MANAGEMENT/COLLECTIONS (collect).
- Not normalizing milestone IDs to MS1/MS2/MS3 when the template's enum demands it.

## Quick reference: policies (from /api/policies)
- POL-NEW-CLIENT-PAYMENT: new NGO → PREPAY_100 before production.
- POL-RECURRING-NGO-PAYMENT: recurring NGO → NET_30_AFTER_PO (unless grant
  restricts). Recurring commercial milestone-billing accounts likewise follow
  their `payment_profile`.
- POL-INDICATIVE-EXW: no destination → EXW only, exclude freight.
- POL-FREIGHT-RECONFIRM: freight valid only to `valid_until`; reconfirm at order.
- POL-MODULE-GRANULARITY: quote module RFQs at module line level.
- POL-REVREC: recognize revenue only for paid+complete milestones; unpaid future
  milestones stay outstanding and drive collection tasks when due/overdue.
- POL-QUOTE-VALIDITY: catalog pricing valid 30 calendar days from quote date.
- POL-EXW-SCOPE: EXW excludes freight, insurance, duty, customs, last-mile.

### Payment terms by account (set `payment_terms`/`customer_policy`)
Derive from the customer's `payment_profile` + segment, cross-checked vs policy:
- `NEW_CLIENT_REVIEW` / new NGO → `PREPAY_100` (POL-NEW-CLIENT-PAYMENT).
- `NET_30_AFTER_PO` recurring NGO/commercial → `NET_30_AFTER_PO`
  (POL-RECURRING-NGO-PAYMENT); name the matching policy id in `customer_policy`.
- `MILESTONE_BILLING` implementation-services accounts → milestone billing terms.
Always prefer the customer record's stated `payment_profile`; use the policy to
confirm/justify it.
