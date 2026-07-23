# Workbench Access

`environment_access.md` (in the task root) is the **only** source for reaching the running deal workbench. Use it solely for network access — base URL, read-only SQL token, and the allowed-endpoint list. Never treat it as a source of deal data or answer values.

## Read these from environment_access.md each run
- The base URL (typically exposed as `GDPEVO_ENV_BASE_URL`). Substitute it for every `<TASK_ENV_BASE_URL>` placeholder in the task prompt.
- The `POST /api/query` token (read-only SQL). Re-read it each run; do not assume a prior value.
- The allowed-endpoint list. Hit only those routes.

## How to query
Prefer the documented REST routes for structured records; use the read-only SQL endpoint for cross-table checks you cannot get from a single GET.

### REST (GET)
Replace `<base>` with the base URL from `environment_access.md` and `<deal_id>` with the exact deal id from the prompt:
- `<base>/api/deals/<deal_id>` — deal record (headline value, client/counterparty, dates)
- `<base>/api/deals/<deal_id>/terms` — current draft terms (each with a stable term_id)
- `<base>/api/deals/<deal_id>/benchmarks` — market median / upper-quartile per metric
- `<base>/api/deals/<deal_id>/risk-estimates` — quantified low/high exposure bands (stable estimate ids)
- `<base>/api/deals/<deal_id>/employees` — headcount, PTO liability, service-credit, WARN
- `<base>/api/deals/<deal_id>/consents` — change-of-control / assignment consents
- `<base>/api/deals/<deal_id>/material-contracts` — material contracts (annual revenue, change-of-control)
- `<base>/api/deals/<deal_id>/regulatory` — HSR / regulatory status, effort covenants
- `<base>/api/deals/<deal_id>/diligence-findings` — specific quantified findings (stable finding ids)
- `<base>/api/deals/<deal_id>/cap-table` — holder-level fully-diluted shares
- `<base>/api/deals/<deal_id>/documents` — draft document references
- `<base>/api/deals/<deal_id>/notes` — negotiation notes
- `<base>/api/playbooks` and `<base>/api/playbooks/<playbook_id>/rules` — playbook preferred/fallback rules
- `<base>/api/policies` and `<base>/api/policies/<policy_id>/thresholds` — committee policy thresholds
- `<base>/api/search` — search
- `<base>/` and `<base>/workspace` — workspace / UI entry

Pull only the records the deliverable needs; the prompt lists the useful entry points for the task.

### Read-only SQL (POST)
- `POST <base>/api/query` with the token from `environment_access.md`.
- Use for cross-table checks (e.g., joining terms to risk estimates and consents, or summing exposure across categories).
- The token is read-only — do not attempt writes.

## Anti-cross-contamination
- Query by the **exact** `deal_id` from the prompt. Do not assume records from a similarly named project apply.
- Never reuse IDs, term values, or schema from a different deal.
