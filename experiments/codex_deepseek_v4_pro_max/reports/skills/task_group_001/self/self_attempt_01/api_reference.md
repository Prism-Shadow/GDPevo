## HarborCRM API Reference

Base URL: `<TASK_ENV_BASE_URL>` (supplied by runner). All endpoints are GET; no authentication.

### Events

| Endpoint | Returns |
|---|---|
| `GET /api/events` | List of all events |
| `GET /api/events?status=<status>` | Events filtered by status |
| `GET /api/events/{event_id}` | Single event detail |
| `GET /api/events/{event_id}/orders` | Sponsor orders for an event |
| `GET /api/events/{event_id}/badges` | Badge scans for an event |
| `GET /api/events/{event_id}/sponsor_packages` | Sponsor packages for an event |

### Finance

| Endpoint | Returns |
|---|---|
| `GET /api/finance/invoices?event_id=<event_id>` | Invoices by event |
| `GET /api/finance/invoices?account_id=<account_id>` | Invoices by account |

### CRM

| Endpoint | Returns |
|---|---|
| `GET /api/crm/accounts` | All CRM accounts |
| `GET /api/crm/accounts?status=<status>` | Accounts filtered by status |
| `GET /api/crm/accounts?owner_region=<owner_region>` | Accounts by owner region |
| `GET /api/crm/contacts` | All CRM contacts |
| `GET /api/crm/contacts?account_id=<account_id>` | Contacts for an account |
| `GET /api/crm/opportunities` | All opportunities |
| `GET /api/crm/opportunities?event_id=<event_id>` | Opportunities by event |
| `GET /api/crm/opportunities?account_id=<account_id>` | Opportunities by account |
| `GET /api/crm/campaign_members` | All campaign members |
| `GET /api/crm/campaign_members?event_id=<event_id>` | Campaign members by event |
| `GET /api/crm/campaign_members?account_id=<account_id>` | Campaign members by account |

### Trade Shows

| Endpoint | Returns |
|---|---|
| `GET /api/tradeshows` | List of all trade shows |
| `GET /api/tradeshows/{show_id}` | Single trade show detail |
| `GET /api/tradeshows/{show_id}/exhibitors` | Exhibitors for a trade show |
| `GET /api/tradeshows/{show_id}/meeting_interest` | Meeting interest / demo requests |

### Import Batches

| Endpoint | Returns |
|---|---|
| `GET /api/import_batches` | List of import batches |
| `GET /api/import_batches/{batch_id}` | Single batch detail |
| `GET /api/import_batches/{batch_id}/raw_contacts` | Raw contacts in a batch |
| `GET /api/import_batches/{batch_id}/suppression` | Suppression list for a batch |

### Policies

| Endpoint | Returns |
|---|---|
| `GET /api/policies` | Policy metadata (follow-up windows, thresholds, etc.) |
