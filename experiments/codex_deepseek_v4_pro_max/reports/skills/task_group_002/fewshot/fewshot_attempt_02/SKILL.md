## MedBridge Sales Ops — Account-Ready JSON Decision Package

### What this skill covers

You are expected to query the shared **MedBridge Sales Ops API** (a read‑only REST API) and assemble a JSON decision package for a sales‑ops business process. The prompt describes a specific business scenario (quote revision, RFQ response, opportunity reconciliation, engagement reconciliation, etc.) and references concrete entity IDs. The task environment base URL is always provided as `<TASK_ENV_BASE_URL>` in the prompt.

### Workflow

Follow these steps in order for every task:

1.  **Extract the base URL**. Search the prompt for `<TASK_ENV_BASE_URL>`. The runner will have substituted it with an actual `http://<host>:<port>/` value. Store this value; every API call starts with it.

2.  **Read the answer template**. The template is always at `input/payloads/answer_template.json` relative to the prompt directory. Load it and study every key, nested object, and enum constraint. The template is the single source of truth for the output shape.

3.  **Identify required entities from the prompt**. Parse the prompt for:
    - quote IDs (e.g. `Q-TR-…`), RFQ IDs (e.g. `RFQ-TR-…`), opportunity IDs (e.g. `OPP-TR-…`)
    - customer IDs (e.g. `CUST-…`)
    - product codes (e.g. `WC-KIT-A`, `LD-REAGENT-44`, `IEHK-BASIC`)
    - event IDs, voucher codes, contact names, dates, quantities

4.  **Map template fields to API endpoints**. Use the table below to decide which endpoints to call:

    | Template concerns | API endpoints (GET) |
    |---|---|
    | Customer name, customer-level defaults | `/api/customers`, `/api/customers/{id}` |
    | Product pricing, tier, lead time, shelf life, article numbers | `/api/products`, `/api/products/{code}` |
    | Quote header, EXW unit price, quantity, quote date | `/api/quotes`, `/api/quotes/{id}` |
    | RFQ header, requested products/modules, quantities | `/api/rfqs`, `/api/rfqs/{id}` |
    | Freight options (AIR/SEA/ROAD), costs, transit, validity, risks | `/api/freight-quotes`, `/api/freight-quotes/{id}` |
    | Payment terms, reconfirmation rules, recommended mode, basis | `/api/policies`, `/api/policies/{id}` |
    | Opportunity stage, won amount, milestones, contacts | `/api/opportunities`, `/api/opportunities/{id}` |
    | Invoice totals, payment status, due dates | `/api/invoices`, `/api/invoices/{id}` |
    | Payment amounts, payment state per invoice/milestone | `/api/payments`, `/api/payments/{id}` |
    | Revenue-recognition journal entries per milestone | `/api/revenue-journals`, `/api/revenue-journals/{id}` |
    | Client celebration/briefing events, status, dates | `/api/events`, `/api/events/{id}` |
    | Voucher codes, discount, max uses, status | `/api/vouchers`, `/api/vouchers/{code}` |

    Call the collection endpoint (e.g. `/api/quotes`) when you need to list all records and find a specific one by its ID. Call the specific endpoint (e.g. `/api/quotes/{id}`) when you already have the ID from the prompt or from a previous response.

5.  **Fetch all required data**. Make the API calls. Use `curl -s "$BASE_URL/api/…"` to retrieve JSON. Always include the `-s` flag to suppress progress output. Pipe through `python3 -m json.tool` or `jq` if you need to inspect the response or extract values.

6.  **Compute derived values**. Several template fields are not direct API values but calculations:
    - `exw_total_usd` = `unit_price_usd` × `confirmed_quantity` (or for line‑item templates, `line_total` = `unit_price` × `quantity`)
    - `grand_total_usd` = `exw_total_usd` + `freight_cost_usd` (per freight option)
    - `outstanding_balance` = sum of `amount_unpaid` across milestones
    - `phase_total_amount` = sum of milestone `amount` fields
    - `opportunity_matches_milestones` / `opportunity_matches_phase_total` = `won_amount` equals the sum of milestone amounts
    - `total_paid_amount` = sum of `paid_amount` or `amount_paid` across milestones

7.  **Determine status/action fields**. Use the API responses to fill in controlled-vocabulary fields:
    - `payment_status` / `payment_state`: compare `amount_paid` vs `invoice_total`. `PAID` if equal and > 0; `PARTIAL` if > 0 but less; `UNPAID` otherwise.
    - `revenue_recognition_status` / `recognition_status`: check whether a revenue‑journal record exists for the milestone. `RECOGNIZED` if a journal entry exists; `MISSING_REVENUE_JOURNAL` / `REQUIRED_MISSING` if milestone is paid but no journal entry found; `NOT_REQUIRED_UNPAID` if milestone is unpaid.
    - `validity_status`: compare `valid_until` against the quote date; `STALE` if `valid_until` < quote date, `VALID` otherwise.
    - `freight_reconfirmation_required`: check the policy record for the `reconfirmation_required` flag, or infer `true` if any freight option is stale or has high risk.
    - `recommended_mode`: prefer the policy's recommended mode; otherwise rank by lowest non‑stale `grand_total_usd` with `risk_level` as a tiebreaker prefixed to a safe fallback (SEA is typically safest).

8.  **Assemble the JSON response**. Populate the answer template exactly. Use the actual API‑returned values, the derived calculations, and the determined status/action fields. Keep currency values as numbers with two decimal places. Use ISO `YYYY-MM-DD` dates. Use the exact enum values declared in the template.

9.  **Output only the JSON**. Never include markdown fences, explanatory text, or commentary outside the JSON object. The output must be parseable as valid JSON directly.

### Common scenario patterns

- **Quote revision with freight**: prompt mentions a quote ID and product code → call `/api/quotes/{quote_id}`, `/api/customers/{customer_id}`, `/api/products/{product_code}`, `/api/freight-quotes`, `/api/policies`. Build `pricing` + `transport_decisions` + `client_warnings` (or `quote_summary` + `freight_options` + `policy_flags` depending on the template).

- **RFQ / new-account EXW‑only quote**: prompt mentions an RFQ ID and no destination → call `/api/rfqs/{rfq_id}`, `/api/customers/{customer_id}`, `/api/products/{code}` for each line item, `/api/policies`. Build `quote_header` + `line_items` + `quote_controls`. Set `freight_excluded: true`.

- **Opportunity / account reconciliation**: prompt mentions an opportunity ID and contact name → call `/api/opportunities/{id}`, `/api/customers/{id}`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events/{id}`, `/api/vouchers/{code}`. Build account status, milestones with payment/revenue state, event/voucher info, and follow‑up tasks.

### API reference (summary)

All endpoints are read‑only `GET`. The base URL is the value substituted for `<TASK_ENV_BASE_URL>`. No authentication is required.

Accept headers are not required; the API returns `application/json` by default.

| Endpoint | Returns |
|---|---|
| `GET /api` | API index / available endpoints |
| `GET /api/search?q=…` | Free‑text search across entities |
| `GET /api/customers` | List of all customers |
| `GET /api/customers/{id}` | Single customer record |
| `GET /api/products` | List of all products |
| `GET /api/products/{code}` | Single product record |
| `GET /api/rfqs` | List of all RFQs |
| `GET /api/rfqs/{id}` | Single RFQ with requested line items |
| `GET /api/quotes` | List of all quotes |
| `GET /api/quotes/{id}` | Single quote record |
| `GET /api/freight-quotes` | List of all freight quotes |
| `GET /api/freight-quotes/{id}` | Single freight quote record |
| `GET /api/policies` | List of all policy records |
| `GET /api/policies/{id}` | Single policy record |
| `GET /api/opportunities` | List of all opportunities |
| `GET /api/opportunities/{id}` | Single opportunity with milestones & contacts |
| `GET /api/invoices` | List of all invoices |
| `GET /api/invoices/{id}` | Single invoice record |
| `GET /api/payments` | List of all payments |
| `GET /api/payments/{id}` | Single payment record |
| `GET /api/revenue-journals` | List of revenue‑recognition journal entries |
| `GET /api/revenue-journals/{id}` | Single journal entry |
| `GET /api/events` | List of all events |
| `GET /api/events/{id}` | Single event record |
| `GET /api/vouchers` | List of all vouchers |
| `GET /api/vouchers/{code}` | Single voucher record |
