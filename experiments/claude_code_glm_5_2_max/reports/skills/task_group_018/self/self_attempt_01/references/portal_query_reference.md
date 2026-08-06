# Portal Query Reference

Base URL and the allowed endpoint allow-list come from `environment_access.md`. Read that file each run; do not hard-code the host. Auth is none / open within network. Below is the confirmed behavior of each endpoint — treat query param names as something to **re-verify against the live API**, not as guaranteed.

## Endpoints

- `GET /api/jurisdictions` → list of courts. Each row carries `jurisdiction_code`, `court_name`, `court_level`, `county`, `state`, `clerk_office`, `policy_ref`, `timezone`, `active`. Use this to map a court name in a prompt to its `jurisdiction_code` (the key every other endpoint filters on).
- `GET /api/cases?jurisdiction_code=<code>` → case records. Fields include `case_number`, `case_type`, `defendant_first/last`, `defendant_dob`, `counsel_type`, `attorney_label_raw`, `attorney_name`, `status`, `disposition_date`, `filed_date`, `judge`, `prosecutor`, `source_system`, `source_updated_at`. `attorney_label_raw` is the shorthand (PD/RET/APD); `counsel_type` is the resolved classification.
- `GET /api/search?q=<case_number|name|...>` → cross-entity lookup returning mixed `result_type`s (`cases`, charges, etc.). The fastest way to confirm a single matter's reality; returns the same case fields plus `result_id`/`result_type`.
- `GET /api/charges` (filtered by jurisdiction/case) → charges as filed and as convicted. Use to confirm the actual convicted count vs. an amended-away count.
- `GET /api/docket-entries` (filtered by case) → docket text. Use to confirm whether an order was signed/entered and the disposition language.
- `GET /api/fee-schedules?jurisdiction_code=<code>` → fee rows. Each row: `fee_id`, `fee_type`, `label`, `amount`, `effective_date`, `end_date` (null = still current), `mandatory`, `priority`, `statute`, `violation_code`, `notes`.
- `GET /api/payment-policies` → policy bands (min/max monthly), payment application order, account-fee treatment, plan policy ids.
- `GET /api/forms?jurisdiction_code=<code>` → form ids/labels/metadata for the jurisdiction. May return empty for some jurisdictions — fall back to the form-family enum the template allows and the local form excerpt for labels.
- `GET /api/financial-petitions` → petition records (sequence, classification, requested vs. approved terms).
- `GET /api/citations` (filtered by jurisdiction/citation number) → traffic citation records for traffic-closeout matters.

## The current-vs-stale fee-schedule pattern (critical)

The same fee (e.g. a Drug Crime Assessment Fee) often has **multiple rows**: one with `end_date` in the past (`notes` like "Stale amount retained for audit history," `fee_id` ending `-OLD`) and one current (`end_date: null`, `effective_date` in the disposition's year, `notes` like "Current amount for 2025 dispositions").

- Match the row whose `effective_date ≤ disposition_date` and whose `end_date` is null or ≥ disposition_date.
- An "archived amount" / "old local worksheet" / "archived amount" queue line almost always corresponds to the **end-dated** row. Post the **current** row's amount for the disposition year.
- If a fee is `mandatory: true` and supported by a convicted count the judge called out (e.g. lab/drug assessment on a retained controlled-substance conviction), post it even when the worksheet omitted it.

## Querying tips

- Confirm the param spelling with one probe call before relying on it.
- Prefer the filtered list endpoint for breadth (`?jurisdiction_code=`) and `/search?q=` for a single known identifier.
- Cross-check key facts (counsel type, DOB, status, disposition date) between `/api/cases` and `/search` — agree ⇒ high confidence.
- If an endpoint returns empty where you expected data, the matter may genuinely have no record there (e.g. a traffic citation with no separate case/account number opened) — that is itself an answer (use citation number as account reference; hold unsupported fields).
