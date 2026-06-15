# Enterprise Export-Complaint Response Package

Read this for the enterprise export-failure complaint task. Expands SKILL.md section 4.

## Evidence chain (follow in order)

1. **Complaint email** (`payloads/*.txt`): gives the client name, product
   (e.g. `monthly_export`), and an approximate incident reference (e.g. `INC-7301`).
2. `/api/enterprise/incidents/<incident_id>` → `enterprise_account_id`, `severity`,
   `status`, `engineering_owner`, `account_owner`, `product`, `summary`.
3. `/api/enterprise/accounts/<enterprise_account_id>` → client `name`, `account_owner`,
   `finance_owner`, `tier`.
4. `/api/enterprise/sla/<enterprise_account_id>` → `credit_trigger`,
   `monthly_export_credit_percent` (the percent for this product), executive contact.
5. `/api/enterprise/export-runs?incident_id=<id>` → the consecutive `FAILED` runs (each has
   `run_date`, `failure_code`, `exported_record_count == 0`) plus the later `SUCCEEDED`
   backfill run.
6. `/api/enterprise/messages?query=<client>` → the human root-cause narrative and the
   channel an alert was routed to. **Ignore** bulk `generated.user` "Generated support
   message N" noise; the substring search also matches field names, so read bodies, not
   just hit counts.

## Field-by-field

| Field | Source / rule |
|---|---|
| `incident_id` | from the email / incident record |
| `enterprise_account_id` | incident record |
| `root_cause_category` | **concise PROSE phrase** paraphrasing the root-cause message — NOT the raw `failure_code`. e.g. message "credential rotation completed; scheduler still references old secret" → `stale credential after rotation` |
| `contributing_alert_issue` | `ARCHIVED_ALERT_ROUTE` if the alert landed in an archived channel (e.g. `export-alerts-archive`); else `NONE`; `UNKNOWN` if no evidence |
| `failure_window.start_date` | first FAILED `run_date` |
| `failure_window.end_date` | last FAILED `run_date` |
| `failure_window.failed_days` | count of FAILED runs |
| `backfill_days` | failed days reprocessed by the SUCCEEDED run (normally = failed_days) |
| `sla_credit_percent` | SLA percent for the product when the trigger is met (integer) |
| `severity` | incident record (`Critical`/`High`/`Medium`/`Low`) |
| `engineering_owner` | incident record |
| `account_owner` | incident record |

## Naming conventions (parse `naming_style` literally)

Given `naming_style: "lowercase hyphen channel; client-date investigation folder;
client export failure report title"`:

| Field | Convention | Example for "Asteri Retail Inc." |
|---|---|---|
| `channel_name` | client name slugified lowercase-hyphen, NO descriptive suffix | `asteri-retail-inc` |
| `evidence_folder` | Title-case client name + `Month YYYY` (failure window) + `Investigation` | `Asteri Retail Inc. May 2026 Investigation` |
| `report_title` | Title-case client name + `Export Failure - Resolution Report` | `Asteri Retail Inc. Export Failure - Resolution Report` |

Prefer the simplest literal reading. Do not add invented descriptors (`-export-failure`)
or convert the folder/title into slugs or ISO dates.

## share_permissions (role-based)

- Include only the users in `permission_users_to_include`, in that listed order.
- Finance reviewer/owner → `view` (read-only sign-off on the credit).
- Engineering/technical reviewer → `edit`.
- `upload_only` is for a contributor who only deposits artifacts (use if the role data says so).

## response_status

| Value | When |
|---|---|
| `NEEDS_FINANCE_REVIEW` | an SLA credit is being issued → finance must sign off (beats READY_TO_SEND even when root cause + backfill are confirmed) |
| `NEEDS_ENGINEERING_REVIEW` | root cause not yet confirmed |
| `UNDER_INVESTIGATION` | incident itself still unresolved |
| `READY_TO_SEND` | everything confirmed AND no credit/finance sign-off pending |
