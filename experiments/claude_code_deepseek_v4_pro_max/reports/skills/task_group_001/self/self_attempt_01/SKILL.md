# HarborCRM Skill

## Environment

Base URL: read from the runner or `environment_access.md`. The standard remote is `http://34.46.77.124:8001`. Never use localhost/127.0.0.1 unless the remote URL itself points there; `environment_access.md` overrides any localhost references in task prompts.

## API Reference

All endpoints are public GET. No auth required.

### Events
- `GET /api/events` — list all events
- `GET /api/events/{event_id}` — single event (includes `campaign_code`, `start_date`, `end_date`, `followup_days_after_end`, `sponsor_followup_days_after_end`, `lead_opportunity_amount`, `status`)
- `GET /api/events/{event_id}/orders` — sponsor orders for the event
- `GET /api/events/{event_id}/badges` — badge scans for the event
- `GET /api/events/{event_id}/sponsor_packages` — same data as orders (alias)

### Finance
- `GET /api/finance/invoices?event_id={event_id}` — invoices filtered by event

### CRM
- `GET /api/crm/accounts` — all CRM accounts
- `GET /api/crm/contacts` — all CRM contacts
- `GET /api/crm/opportunities` — all opportunities; supports `?event_id=` filter
- `GET /api/crm/campaign_members?event_id={event_id}` — campaign members for an event

### Trade Shows
- `GET /api/tradeshows` — list all trade shows
- `GET /api/tradeshows/{show_id}/exhibitors` — exhibitors for a show
- `GET /api/tradeshows/{show_id}/meeting_interest` — meeting interest data

### Import Batches
- `GET /api/import_batches` — list all import batches
- `GET /api/import_batches/{batch_id}/raw_contacts` — raw rows to import
- `GET /api/import_batches/{batch_id}/suppression` — suppression list for the batch

### Policies
- `GET /api/policies` — qualification and platform metadata

---

## Business Rules

### 1. Sponsor Status Determination

Cross-reference **orders** and **invoices** for each sponsor account at the event:

| Order Status | Invoice Status | Sponsor Status |
|---|---|---|
| `confirmed` | `paid_deferred` (paid in full) | `paid_deferred` |
| `confirmed` | `open` (balance remaining) | `open_invoice` |
| `proposal_sent` | No invoice | `proposal_only` |
| `canceled` | — | Exclude entirely (`inactive_sponsor_record`) |

- **Open balance** = invoice `amount` − invoice `paid_amount`
- Sponsor revenue totals are integers in USD. Sum `paid_deferred` accounts' order amounts under `paid_deferred`; `open_invoice` accounts' order amounts under `open_invoice`; `proposal_only` order amounts under `proposal_only`. Report `open_invoice_balance` as the sum of open balances across all `open_invoice` accounts.
- A sponsor account with a `canceled` order is **not** reported in sponsor statuses or revenue totals — it is inactive.

### 2. Badge Classification

Each badge scan must be classified by `badge_type` and relationship to sponsors:

| Badge Type | Company is Active Sponsor? | Classification |
|---|---|---|
| `sponsor` | Yes | `sponsor_attendee` — excluded |
| `attendee` | Yes | `sponsor_attendee` — excluded (even if sponsor is proposal-only) |
| `attendee` | No | Evaluate as potential **qualified non-sponsor lead** |
| `student` | — | `non_business_badge` — excluded |
| `press` | — | `non_business_badge` — excluded |

- A company is an "active sponsor" if it has an order with `order_status` of `confirmed` or `proposal_sent` (NOT `canceled`).
- Sponsor ticket contacts (from `orders[].ticket_contacts`) who do **not** appear in badge scans still count as sponsor affiliates and should not appear as qualified leads. Their campaign member status should be preserved.

### 3. Qualified Non-Sponsor Lead Rules

A badge is a qualified non-sponsor lead when ALL of the following hold:
1. `badge_type` is `attendee` (not `sponsor`, `student`, `press`)
2. Company is NOT an active sponsor (no `confirmed` or `proposal_sent` order)
3. Company's CRM account (if it exists) is NOT disqualified (`status != "disqualified"`)

For each qualified lead:
- **CRM account action**: `create_account` if the company has no CRM account; `update_existing` if the company already has a CRM account.
- **CRM contact action**: `create_contact` if the contact name/email is not in existing CRM contacts for that account; `update_existing` if they already exist.
- **Campaign member action**: `add_campaign_member` for new leads.
- **Opportunity amount**: Use the event's `lead_opportunity_amount` for each qualified non-sponsor account.
- **Lead pipeline total** = sum of opportunity amounts for all qualified accounts.

### 4. Exclusion Reasons

| Reason | When to Apply |
|---|---|
| `sponsor_attendee` | Badge belongs to an active sponsor's contact |
| `existing_disqualified` | CRM account exists with `status == "disqualified"` |
| `inactive_sponsor_record` | Company had a sponsor order with `order_status == "canceled"` |
| `non_business_badge` | `badge_type` is `student`, `press`, or other non-business type |

For trade-show prospecting tasks, use the domain-specific exclusion reasons from the answer template (e.g., `distributor_only`, `service_only`, `sensor_vendor_only`, `sensor_only`, `research_only`, `not_target_market`).

### 5. Follow-Up Dates

Calculate from the event's `end_date`:
- **Lead follow-up due date** = `end_date` + `followup_days_after_end` days
- **Sponsor finance due date** = `end_date` + `sponsor_followup_days_after_end` days

Use `YYYY-MM-DD` format. Add days to the date; do not skip weekends or holidays.

### 6. Follow-Up Task Counts

- **Lead task count** = number of qualified non-sponsor lead accounts
- **Sponsor finance task count** = number of sponsor accounts with `open_invoice` status
- **Sponsor finance accounts** = list of account names with `open_invoice` status, sorted ascending

---

## Contact Normalization

### Email
- Trim leading/trailing whitespace
- Convert to lowercase
- Empty string `""` if no email was supplied (whitespace-only emails → treat as missing)

### Phone
- Strip all non-digit characters (spaces, parentheses, dashes, dots, leading `+`, country code prefix)
- Result is a digits-only string (e.g., `+1 (415) 555-0101` → `14155550101`)
- Empty string `""` if no phone was supplied
- Do NOT drop leading country codes (US `1`, etc.) — strip the `+` but keep the digits

---

## CRM Matching

### Account Matching
Match a company/account name against CRM accounts by exact name match (case-sensitive as returned by the API). If a trade-show exhibitor has a `crm_account_id` field, use that directly.

### Contact Matching
Match a contact against CRM contacts:
1. By email: normalize the badge/import email, compare against normalized CRM contact emails
2. By name: exact match on `contact_name` within the matched account

### CRM Action Assignment
| CRM Account Exists? | CRM Contact Exists? | Account Action | Contact Action |
|---|---|---|---|
| No | — | `create_account` | `create_contact` |
| Yes | No | `update_existing` | `create_contact` |
| Yes | Yes (same account) | `update_existing` | `update_existing` |

---

## Import Batch Processing

### Step 1: Normalize all raw contact emails and phones

### Step 2: Remove unusable rows
A row is unusable if **both** `contact_name` is effectively blank AND `email` normalizes to empty. Also remove rows where the normalized email is empty and phone is empty (unreachable). Removal reason: `missing_contact`.

### Step 3: Deduplicate
- **Dedup key**: normalized email (lowercase, trimmed)
- **Winner**: the row with the earliest `captured_at` timestamp
- **Tiebreaker**: if timestamps are equal, the row with the lower `row_id` (lexicographic) wins
- Removed duplicates get reason `duplicate`
- The winning row's `row_id` becomes both `clean_contact_id` and `source_row_id`
- For the winning row, use its own `captured_at`, `source_name`, and original row data

### Step 4: Suppression check
Match each surviving row's normalized email and normalized phone against the suppression list. A row is **suppressed** if its normalized email or normalized phone matches any suppression entry. Removal reason: `suppressed`. Suppression is checked AFTER dedup (only on winning rows).

### Step 5: CRM matching for survivors
Match each survivor's company name and contact name/email against CRM accounts and contacts. Assign `crm_action`:
- `create_account` — no matching CRM account
- `update_existing` — matching CRM account found
- `no_import` — matching account exists but is disqualified, or contact opted out
- `suppress` — matched suppression list (use only if suppressed rows remain in clean_contacts)

Set `existing_account_id` and `existing_contact_id` to the matched CRM IDs (or `null`).

### Step 6: Campaign member import count
Count of surviving clean contacts that will become campaign members for the batch's campaign. Rows with `crm_action == "suppress"` or `"no_import"` are NOT counted.

---

## Trade Show Prospecting

### Platform Classification
Classify each exhibitor into zero or more of the standard platforms:
- **AUV** — builds/manufactures autonomous underwater vehicles
- **ROV** — builds/manufactures remotely operated vehicles
- **Underwater Camera** — manufactures underwater camera modules/systems

Read the exhibitor `description` field. A company qualifies when it **builds or OEM-manufactures** the platform category. Mere integration of third-party sensors/cameras does NOT confer platform classification if the company doesn't build the platform itself. A camera array built into a company's own ROV counts as ROV (the camera is a component); a standalone underwater camera product counts as Underwater Camera.

### Qualification
An exhibitor is qualified when it manufactures at least one of the target platforms AND is not excluded by a domain rule:
- **Distributors/resellers** → `distributor_only` — company sells others' products, doesn't manufacture
- **Service providers** → `service_only` — consulting, rentals, or operations using others' equipment
- **Sensor-only vendors** → `sensor_vendor_only` / `sensor_only` — makes sensors but not the platforms that carry them
- **Research/analytics only** → `research_only` — software/analytics, no hardware
- **Not target market** → `not_target_market` — completely unrelated business

### Priority Tiering
When the task specifies tier rules, apply them exactly as stated. Common pattern across tasks:
- **A**: demo requested + high interest score (≥90)
- **B**: demo requested + moderate interest score (≥80)
- **C**: all other qualified leads

When the task does NOT specify tier rules, infer from the meeting interest data: prioritize demo requests, then score, then platform breadth.

### Ranking
When specified, rank qualified leads by the given criteria (typically: demo request first, then interest score descending, then platform coverage count descending, then company name ascending).

### Opportunity Sizing
When tier-based amounts are specified (e.g., A=$120000, B=$90000, C=$50000), apply them by tier. When no tier amounts are specified, use the event's `lead_opportunity_amount`.

---

## Campaign Member Reconciliation

When reconciling campaign members with badge scans:

1. List all existing campaign members for the event
2. List all badge scans for the event
3. For each badge scan:
   - If the person is already a campaign member, determine if their status needs updating (e.g., `registered_sponsor` → `attended_sponsor` if they scanned in)
   - If the person is NOT a campaign member and is a qualified lead, action is `create` with target status `attended`
4. For existing campaign members NOT in badge scans:
   - Keep their current status (action: `no_action`)
5. Action values: `create`, `update`, `no_action`, `no_import`
6. Target status values: `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`

The `subject_key` for sorting is typically `{account_name}|{contact_name}` or `{account_id}|{contact_id}`.

---

## Sorting Rules (Default)

- Sponsor statuses / account lists: by `account_name` ascending
- Badge decisions: by `badge_id` ascending
- Qualified leads/accounts: by `account_name` ascending (unless ranked)
- Excluded records: by `company_name` ascending, then `contact_name` ascending
- Clean contacts: by `clean_contact_id` ascending
- Duplicate keys: by `key` ascending
- Removed rows: by `row_id` ascending
- Platform lists: in enum declaration order (AUV, ROV, Underwater Camera)
- CRM account IDs: ascending lexicographic

---

## Output Conventions

- All currency amounts are **integers** (whole USD, no decimals)
- All dates are **YYYY-MM-DD** strings
- All counts are **integers**
- Return valid JSON only — no prose outside the JSON object
- Do not add fields not declared in the answer template
- Use `null` for missing IDs (not `""` or `"none"`)
- Empty email/phone when not supplied: `""` (empty string)
- Follow the answer template's key names, enum values, and structure exactly

---

## Common Pitfalls

1. **Canceled sponsors are NOT sponsors**: A company with `order_status: "canceled"` is inactive. Do not list them in sponsor statuses. Their contacts are excluded as `inactive_sponsor_record`, not `sponsor_attendee`.
2. **Proposal-only sponsors are still sponsors**: A company with `order_status: "proposal_sent"` IS an active sponsor (status `proposal_only`). Their badge-scanning contacts are `sponsor_attendee`, not qualified leads.
3. **Disqualified CRM accounts trump badge qualification**: Even if a badge looks like a good lead, if the CRM account is disqualified, exclude as `existing_disqualified`.
4. **Dedup before suppression**: Always deduplicate raw contacts first (so suppressed duplicates don't create extra removal rows), then check suppression on survivors.
5. **Timestamp tiebreaking in dedup**: When two rows share the same normalized email AND the same `captured_at`, use the lower `row_id` as winner.
6. **Normalization is idempotent**: Normalize emails (trim, lowercase) and phones (digits only) before any comparison — matching, dedup, and suppression all use normalized values.
7. **Empty email is not always missing**: A contact with an empty email but a valid phone and name is still reachable and qualifies (unless the task specifically requires email). Only mark `missing_contact` when truly unreachable.
8. **Campaign member counting**: Only surviving clean contacts with `crm_action` of `create_account` or `update_existing` count toward campaign member imports. Suppressed and no_import records do not.
9. **Sponsor ticket contacts without badges**: If a sponsor's `ticket_contacts` lists someone who doesn't appear in badge scans, they remain as a sponsor campaign member — they are not a qualified lead, nor are they excluded.
10. **Platform classification requires manufacturing**: Reading "camera" in a description is not enough — the company must build the platform, not just use it. "ROV with camera arrays" → ROV (the camera is a component). "Underwater camera manufacturer" → Underwater Camera.
