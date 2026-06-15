# Enterprise Export-Failure Response Package

You are an enterprise support lead turning a client complaint (an export
failure) into a structured response: identify the incident, the failed export
window, root cause, SLA credit, owners, and the response artifacts
(channel/folder/report names, share permissions, response status).

Typical template fields: `incident_id`, `enterprise_account_id`,
`root_cause_category`, `contributing_alert_issue`, `failure_window`
(`start_date`/`end_date`/`failed_days`), `backfill_days`, `sla_credit_percent`,
`severity`, `engineering_owner`, `account_owner`, `channel_name`,
`evidence_folder`, `report_title`, `share_permissions`, `response_status`.

## Records to pull

- The complaint email + `response_requirements.json` in the payload. The email
  gives the client name, product, and an approximate incident reference; the
  requirements give `permission_users_to_include` (ordered) and a `naming_style`.
- `GET /api/enterprise/incidents/<incident_id>` → `enterprise_account_id`,
  `product`, `severity`, `status`, `account_owner`, `engineering_owner`,
  `received_at`, `summary`. (If only an approximate reference is given, confirm
  via `/api/enterprise/incidents?account_id=<id>` or `/api/search`.)
- `GET /api/enterprise/accounts/<enterprise_account_id>` → `name`,
  `account_owner`, `finance_owner`, `tier`.
- `GET /api/enterprise/sla/<enterprise_account_id>` → `credit_trigger`,
  `monthly_export_credit_percent`, `executive_contact`.
- `GET /api/enterprise/export-runs?incident_id=<id>` → the run timeline:
  `run_date`, `status` (FAILED/SUCCEEDED), `failure_code`,
  `exported_record_count`.
- `GET /api/enterprise/messages?query=<client or keyword>` → operator notes that
  reveal the true root cause and the alert-routing problem.

## Field derivations

- **incident_id / enterprise_account_id / severity / owners.** From the incident
  record. `engineering_owner` and `account_owner` are the incident's named
  owners. (`severity` is the incident severity, e.g. Critical.)
- **failure_window.** From the export runs: `start_date` = earliest FAILED
  `run_date`, `end_date` = latest consecutive FAILED `run_date`, `failed_days` =
  count of FAILED runs in that consecutive streak. A later SUCCEEDED run with a
  non-zero `exported_record_count` is the recovery/backfill run — it ends the
  window, it is not part of it.
- **backfill_days.** The number of failed days that had to be re-run = same as
  `failed_days` (the SUCCEEDED backfill run covers each missed day).
- **root_cause_category.** A concise phrase synthesized from the export-run
  `failure_code` and the corroborating message. E.g. `failure_code` =
  STALE_CREDENTIAL plus a message "credential rotation completed; scheduler pod
  still references old secret" → "stale credential after rotation". Keep it a
  short human category, grounded in the evidence.
- **contributing_alert_issue.** Enum (ARCHIVED_ALERT_ROUTE | NONE | UNKNOWN).
  Set ARCHIVED_ALERT_ROUTE when the relevant alert/message was posted to an
  archived/stale alert channel (e.g. `channel == "export-alerts-archive"`),
  meaning the alert went to a dead route and delayed detection. NONE if no such
  routing problem; UNKNOWN if evidence is insufficient.
- **sla_credit_percent.** From the SLA contract (`monthly_export_credit_percent`)
  once the `credit_trigger` is met (e.g. "3 consecutive failed export runs").
  Confirm the trigger condition holds against the run timeline before applying
  the percent. Output an integer percent.
- **response_status.** Enum (READY_TO_SEND | NEEDS_FINANCE_REVIEW |
  NEEDS_ENGINEERING_REVIEW | UNDER_INVESTIGATION). When an SLA credit applies
  (`sla_credit_percent > 0`), finance must sign off the credit before the
  response goes out → `NEEDS_FINANCE_REVIEW`. (Use the incident `status` /
  remaining-work signals only when no credit gates it: still investigating →
  UNDER_INVESTIGATION; engineering action pending → NEEDS_ENGINEERING_REVIEW;
  fully closed with no credit → READY_TO_SEND.)

## Naming conventions (follow the requirements' `naming_style` exactly)

- **channel_name** — lowercase, hyphenated client name. "Asteri Retail Inc." →
  `asteri-retail-inc` (drop punctuation, spaces → hyphens, lowercase).
- **evidence_folder** — `<Client Name> <Month YYYY> Investigation`, using the
  incident month/year (e.g. derived from the failure window / received date):
  "Asteri Retail Inc. May 2026 Investigation".
- **report_title** — `<Client Name> Export Failure - Resolution Report`.

Match the exact casing/punctuation style the requirements describe ("lowercase
hyphen channel; client-date investigation folder; client export failure report
title").

## share_permissions

- Build one entry per user in `permission_users_to_include`, **in the order
  listed** in the requirements (do not re-sort).
- Permission per user: the **finance owner** (matching the enterprise account's
  `finance_owner`) gets `view` (they review the credit, read-only). The other
  collaborator listed in the requirements gets `edit`. Use `upload_only` only if
  a user's role is upload-only evidence intake.
- Example: requirements list `["laura.brown", "jun.chen"]`; laura.brown is the
  account's finance_owner → `view`; jun.chen → `edit`. Output preserves that
  order.

## Validation

- Every owner/percent/date comes from a record, never invented.
- `failed_days`, `backfill_days`, and the window dates must be consistent with
  the FAILED export-run timeline.
- Names follow the requirements' style character-for-character.
- `share_permissions` order matches the requirements list.
