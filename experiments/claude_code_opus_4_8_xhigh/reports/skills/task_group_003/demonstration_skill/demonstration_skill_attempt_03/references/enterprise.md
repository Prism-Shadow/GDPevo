# Enterprise Complaint / Export-Failure Response Package — Family E

Assemble a structured response to an enterprise client complaint (typically a
failed recurring export) by joining several enterprise records. The complaint
email and a `response_requirements.json` are in `payloads/`. The email usually
names the client, product, and an approximate incident id — use those to anchor
the lookups, then derive every field from console evidence.

## Records to fetch

- `/api/enterprise/incidents/<incident_id>` → `enterprise_account_id`, `product`,
  `severity`, `status`, `engineering_owner`, `account_owner`, `summary`,
  `received_at`. (If the id is approximate, confirm via
  `/api/enterprise/incidents?account_id=` or `/api/search?q=`.)
- `/api/enterprise/accounts/<enterprise_account_id>` → `name`, `tier`,
  `account_owner`, `finance_owner`.
- `/api/enterprise/sla/<enterprise_account_id>` → `monthly_export_credit_percent`,
  `credit_trigger`, `executive_contact`.
- `/api/enterprise/export-runs?incident_id=<id>` (or `?account_id=`) → per-day
  runs with `run_date`, `status` (FAILED/SUCCEEDED), `failure_code`,
  `exported_record_count`.
- `/api/enterprise/messages?query=<client name>` → engineer/account notes that
  reveal the root cause and any alert-routing problem.

## Field-by-field derivation

| Output field | How to derive |
|---|---|
| `incident_id`, `enterprise_account_id` | from the incident record |
| `severity` | from the incident record (`Critical`/`High`/`Medium`/`Low`) |
| `engineering_owner`, `account_owner` | from the incident record (account_owner also on the enterprise account) |
| `failure_window.start_date` / `end_date` | first / last `run_date` of the **consecutive FAILED** export runs |
| `failure_window.failed_days` | count of FAILED runs in that streak |
| `backfill_days` | number of days needing manual backfill = `failed_days` (each failed run must be re-run) |
| `sla_credit_percent` | the contract's `monthly_export_credit_percent`, applied when the `credit_trigger` is met (e.g. "3 consecutive failed export runs" and you observed ≥3). Integer percent. |
| `root_cause_category` | a concise human-readable category inferred from the FAILED runs' `failure_code` plus the supporting engineer message. E.g. `STALE_CREDENTIAL` + "credential rotation … old secret" → "stale credential after rotation"; `STAGING_STORAGE_QUOTA` + "bucket reached quota" → "staging storage quota exhausted". |
| `contributing_alert_issue` | `ARCHIVED_ALERT_ROUTE` if the key alert message was posted in an **archived** alert channel (channel name containing `archive`, e.g. `export-alerts-archive`) — i.e. the alert went somewhere nobody watches. If alerts routed normally, `NONE`. If undeterminable, `UNKNOWN`. |
| `response_status` | `NEEDS_FINANCE_REVIEW` when an SLA credit is owed (finance must approve the credit). `NEEDS_ENGINEERING_REVIEW` if root cause is unconfirmed/engineering-blocked. `UNDER_INVESTIGATION` if not yet root-caused. `READY_TO_SEND` only when fully resolved with no open approvals. |

## Naming conventions (follow the requirements `naming_style`)

- `channel_name` — lowercase, hyphen-separated form of the client name with
  punctuation dropped. "Asteri Retail Inc." → `asteri-retail-inc`. ("Inc"/"LLC"
  stay as words; only the punctuation/spaces are normalized.)
- `evidence_folder` — "<Client Name> <Month Year> Investigation", using the
  incident month. e.g. "Asteri Retail Inc. May 2026 Investigation".
- `report_title` — "<Client Name> Export Failure - Resolution Report".

Match the exact phrasing the requirements describe; if `naming_style` gives a
different template, follow the requirements over these defaults.

## Share permissions

`share_permissions[]` is ordered by the users listed in the requirements
(`permission_users_to_include`) — preserve that order exactly. The permission
level reflects each user's role:

- the **finance owner / reviewer** (read-only sign-off) → `view`
- an engineering / editing **collaborator** → `edit`
- an upload-only contributor → `upload_only`

Cross-check roles against the enterprise account (`finance_owner`) and incident
(`engineering_owner`). A user named only in the requirements (not in the console)
still gets included — infer their permission from the requirement's intent /
their apparent role. Default the read-only stakeholder to `view` and the working
collaborator to `edit` when no stronger signal exists.

## Output shape

A single flat JSON object with the keys in `response_requirements.json`'s
`required_fields`: `incident_id`, `enterprise_account_id`, `root_cause_category`,
`contributing_alert_issue`, `failure_window` (object), `backfill_days`,
`sla_credit_percent`, `severity`, `engineering_owner`, `account_owner`,
`channel_name`, `evidence_folder`, `report_title`, `share_permissions` (array of
`{user, permission}`), `response_status`. Emit exactly these keys.
