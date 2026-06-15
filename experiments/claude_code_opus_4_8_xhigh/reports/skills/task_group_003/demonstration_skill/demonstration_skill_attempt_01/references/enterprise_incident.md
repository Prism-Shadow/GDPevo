# Enterprise Export-Incident Response Package

Family: a client complaint about a failed export pipeline. You produce ONE flat
JSON object describing the incident, the failed/backfill window, the SLA credit,
the internal owners, and the response artifacts (channel, evidence folder,
report title, share permissions, response status). Read
`payloads/response_requirements.json` — it lists `required_fields`, the exact
`permission_users_to_include` (and their order), and a `naming_style` hint.

## Records you need

1. The complaint email in `payloads/` gives the client name, product, and an
   approximate incident reference (e.g. `INC-7301`).
2. `GET /api/enterprise/incidents/<incident_id>` → `enterprise_account_id`,
   `product`, `severity`, `engineering_owner`, `account_owner`, `status`,
   `summary`.
3. `GET /api/enterprise/accounts/<enterprise_account_id>` → `name` (client),
   `account_owner`, `finance_owner`, `tier`.
4. `GET /api/enterprise/export-runs?incident_id=<id>` → the run timeline with
   `run_date`, `status` (FAILED/SUCCEEDED), `failure_code`,
   `exported_record_count`.
5. `GET /api/enterprise/sla/<enterprise_account_id>` → `credit_trigger` (prose
   condition) and `monthly_export_credit_percent`.
6. `GET /api/enterprise/messages?query=<client name or keyword>` → engineering
   notes. Inspect both the **body** (root cause) and the **channel** (alert
   routing). Try a few queries (client name, "credential", "alert", failure
   code) since messages are sparse.

## How each field is derived

- **incident_id** — confirm the email's reference against the incidents
  endpoint; use the real id.
- **enterprise_account_id** — from the incident record.
- **root_cause_category** — a concise human phrase inferred from the runs'
  `failure_code` plus the engineering message body. Examples:
  `failure_code STALE_CREDENTIAL` + "credential rotation completed; scheduler
  pod still references old secret" → "stale credential after rotation";
  `failure_code STAGING_STORAGE_QUOTA` + "staging bucket reached quota" →
  "staging storage quota exceeded". Describe the cause, don't just echo the code.
- **contributing_alert_issue** ∈ {ARCHIVED_ALERT_ROUTE, NONE, UNKNOWN}.
  `ARCHIVED_ALERT_ROUTE` only when the relevant engineering alert message lives
  in an **archived alert channel** (channel name contains `archive`, e.g.
  `export-alerts-archive`) — i.e. the alert went to a dead route. If the alert
  messages are in normal channels (e.g. `data-platform`, `account-escalations`,
  `support`) → `NONE`. Use `UNKNOWN` only when evidence is genuinely missing/
  ambiguous.
- **failure_window** — over the export runs for this incident:
  - `start_date` = earliest FAILED `run_date`
  - `end_date` = latest FAILED `run_date` (the consecutive failing streak;
    the first SUCCEEDED run ends the window and is NOT included)
  - `failed_days` = count of FAILED runs in that streak
- **backfill_days** — the number of failed days that must be manually
  backfilled, which equals `failed_days` (each failed run needs a backfill;
  engineering notes often confirm this, e.g. "four days require manual
  backfill").
- **sla_credit_percent** — read `credit_trigger` from the SLA, evaluate it
  against the actual failure run, and if it is met, use
  `monthly_export_credit_percent`. Triggers vary in phrasing:
  - "3 consecutive failed export runs" → met when `failed_days >= 3`.
  - "critical export outage longer than 72 hours" → met when the failed streak
    spans more than 72 hours (e.g. 4 consecutive daily failures).
  If the trigger is not met, the credit is `0`.
- **severity** ∈ {Critical, High, Medium, Low} — from the incident record (the
  email tone usually agrees).
- **engineering_owner / account_owner** — from the incident (account_owner also
  appears on the enterprise account; they should agree).
- **channel_name** — the client name in lowercase-hyphen style: lowercase,
  spaces→hyphens, drop punctuation. "Asteri Retail Inc." → `asteri-retail-inc`.
  Follow the `naming_style` hint in the requirements.
- **evidence_folder** — "<Client Name> <Month Year> Investigation", where the
  month/year is the failure window's month. E.g. failure in May 2026 →
  "Asteri Retail Inc. May 2026 Investigation".
- **report_title** — "<Client Name> Export Failure - Resolution Report".
- **share_permissions[]** — one entry per user in
  `permission_users_to_include`, **in that listed order**. Permission by role:
  - a user who is the **finance_owner** (or other read-only reviewer role) →
    `view`
  - a collaborating engineer/editor not otherwise restricted → `edit`
  - a contributor who should only drop files in → `upload_only`
  Determine each user's role from the account/incident records; the finance
  owner is read-only because finance reviews rather than edits the report.
- **response_status** ∈ {READY_TO_SEND, NEEDS_FINANCE_REVIEW,
  NEEDS_ENGINEERING_REVIEW, UNDER_INVESTIGATION}. Decision order:
  - If a monetary **SLA credit applies** (`sla_credit_percent > 0`), it needs
    finance sign-off → `NEEDS_FINANCE_REVIEW`.
  - Else if the **root cause is still unresolved** (no SUCCEEDED run yet /
    incident still actively under investigation with no fix) →
    `UNDER_INVESTIGATION`.
  - Else if the **engineering root cause is uncertain** and needs review →
    `NEEDS_ENGINEERING_REVIEW`.
  - Else → `READY_TO_SEND`.
  (Note the incident's own `status` field may say `UNDER_INVESTIGATION` even
  after a successful run; base the response_status on the rules above, the SLA
  credit being the dominant factor.)

## Common misjudgments (exclusion rules)

- **failed_days counts only FAILED runs**; the trailing SUCCEEDED run ends the
  window and is excluded. Trust the run records over the complaint's stated
  day-count (the email may round or estimate).
- **ARCHIVED_ALERT_ROUTE is keyed on the channel name** (`*archive*`), not on
  the existence of an alert message. Normal-channel notes → `NONE`.
- **The SLA credit percent comes from the SLA contract**, and only applies if
  its `credit_trigger` is actually met — re-check the trigger against the real
  failure streak rather than assuming a credit is always owed.
- **Naming is mechanical**: derive channel/folder/title from the client name and
  failure month exactly per the conventions; don't invent decorative wording.
- **Preserve the requirements' user order** in `share_permissions`; don't sort
  alphabetically.
- A credit being present makes the package `NEEDS_FINANCE_REVIEW` even if
  engineering has fully root-caused and backfilled the data.
