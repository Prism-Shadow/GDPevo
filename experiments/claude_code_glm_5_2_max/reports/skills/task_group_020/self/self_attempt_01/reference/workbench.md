# Workbench Access

## Source of network access

Read `environment_access.md` from the task working directory. It is the **only**
source for network access. It provides:

- The workbench base URL (an env var such as `GDPEVO_ENV_BASE_URL`). The prompt's
  `<TASK_ENV_BASE_URL>` placeholder resolves to this value.
- The read-only SQL token for `POST /api/query`.
- The allow-list of endpoints. Use **only** the endpoints it lists; do not invent
  routes.

Do not hardcode the base URL or token into reusable artifacts — read them from
`environment_access.md` at runtime. If `environment_access.md` is somehow absent,
fall back to the `<TASK_ENV_BASE_URL>` placeholder in the prompt, but the file is
authoritative when present.

## Pin to the exact deal_id

Use the `deal_id` stated in the prompt (pattern `PRJ_<NAME>`). Substitute it into
every `<deal_id>` route. Never assume records from a similarly named project
apply to your deal_id — always filter to the exact id.

## Endpoint purposes

Confirm every endpoint against the `environment_access.md` allow-list before
calling it. Typical purposes (names may vary slightly by environment):

- `GET /` , `GET /workspace` — workbench landing / workspace context.
- `GET /api/deals` — deal index.
- `GET /api/deals/<deal_id>` — deal record: headline value, sides, signing/closing
  dates, currency, status. Source of the quantification base.
- `GET /api/deals/<deal_id>/terms` — current draft terms (`term_id`, clause ref,
  metric, value, unit). Primary input for issue/deviation classification.
- `GET /api/playbooks` , `GET /api/playbooks/<pb>/rules` — playbook preferred and
  fallback positions per term. The side's negotiating positions.
- `GET /api/policies` , `GET /api/policies/<policy>/thresholds` — committee policy
  thresholds (for escalation tasks).
- `GET /api/deals/<deal_id>/risk-estimates` — quantified exposure low/high per
  issue/finding, with `source_estimate_id` for exposure objects.
- `GET /api/deals/<deal_id>/benchmarks` — market median / upper quartile, sample
  size, and position classification.
- `GET /api/deals/<deal_id>/consents` — required consents (change-of-control,
  assignment), `condition_type`, counterparty, `amount_at_risk`.
- `GET /api/deals/<deal_id>/material-contracts` — material contracts with
  conditions and `annual_revenue`.
- `GET /api/deals/<deal_id>/employees` — employee data: service-credit, PTO
  liability, WARN risk, and stable employee IDs.
- `GET /api/deals/<deal_id>/cap-table` — holders, security classes,
  fully-diluted %, as-converted shares (for holder-level allocation).
- `GET /api/deals/<deal_id>/regulatory` — HSR threshold basis, hell-or-high-water,
  approvals expected.
- `GET /api/deals/<deal_id>/diligence-findings` — findings (privacy, working
  capital, etc.) with stable finding IDs and quantified amounts.
- `GET /api/deals/<deal_id>/notes` — negotiation notes. Use for context only, not
  as authoritative values.
- `GET /api/deals/<deal_id>/documents` — document references.
- `GET /api/search` — cross-record search.
- `POST /api/query` — read-only SQL; token from `environment_access.md`.

## Cross-table checks with `POST /api/query`

Use SQL to **reconcile**, not as the primary read path. Typical checks:

- Confirm a `term_id` referenced in the draft actually exists in `/terms`.
- Join consents to material contracts to confirm which contracts trigger required
  consents and the revenue at risk.
- Sum PTO liability across employees and reconcile to the employee total.
- Verify holder allocation shares sum to the cap table / 100%.
- Reconcile risk-estimate IDs cited in exposure objects back to
  `/risk-estimates`.

Token: read from `environment_access.md` (do not hardcode). Read-only: `SELECT`
only.

## Stable IDs

- Reuse the workbench's own IDs verbatim — `term_id`, consent/`source_id`,
  `contract_id`, `finding_id`, `employee_id`, `estimate_id`, holder name,
  security class. Do not mint new source IDs.
- For issue/redline IDs, use **only** the stable IDs enumerated in the template
  (`possible_issue_ids`, `stable_issue_ids`, `stable_redline_ids`, or the
  `issue_id` enum). If the template provides a synthetic-ID slot (e.g., a
  regulatory blocker id), you may synthesize there and only there.
- Use an empty array `[]` for `source_term_ids` when a required term is missing
  from the current draft.
