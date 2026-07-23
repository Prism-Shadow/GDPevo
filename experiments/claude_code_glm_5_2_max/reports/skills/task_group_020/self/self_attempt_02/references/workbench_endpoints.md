# Workbench Endpoint Catalog

Base URL and read-only SQL token come from `environment_access.md` (read at runtime; do not hardcode). `<TASK_ENV_BASE_URL>` in any prompt maps to that base URL. Below is what each documented endpoint supplies, inferred from the train task entry points and answer-template fields. Treat it as a guide — always confirm fields against the live response.

## Deal core
- `GET /api/deals/<deal_id>` — deal record: client, target/counterparty, transaction type, headline purchase price / equity value, signing & meeting dates, currency.
- `GET /api/deals/<deal_id>/terms` — current draft terms, each with a stable `term_id`, clause refs, and numeric metrics (percent, months, amounts).
- `GET /api/deals/<deal_id>/documents` — draft paper / clause references.

## Playbooks & policies (the comparison yardsticks)
- `GET /api/playbooks` and `GET /api/playbooks/<playbook_id>/rules` — side-appropriate preferred and fallback positions (percent, months, amounts) per issue category. Use the playbook_id named in the prompt (`PB_BUYER_A` / `PB_SELLER_A` pattern).
- `GET /api/policies` and `GET /api/policies/<policy_id>/thresholds` — committee policy thresholds and approved/restricted carveout groups (for escalation tasks).

## Quantification inputs
- `GET /api/deals/<deal_id>/risk-estimates` — exposure ranges (low/high dollars) with stable `estimate_id`s and exposure type (closing_certainty, indemnity_leakage, …).
- `GET /api/deals/<deal_id>/benchmarks` — market metric, sample_size, median, upper_quartile, and the deal's position vs. them.
- `GET /api/deals/<deal_id>/cap-table` — holders, security classes, fully-diluted % and as-converted shares (SPA holder allocation).

## Closing conditions & people
- `GET /api/deals/<deal_id>/consents` — required closing consents with stable `consent_id`, contract/counterparty, condition_type, risk, amount_at_risk.
- `GET /api/deals/<deal_id>/material-contracts` — change-of-control / assignment conditions with stable `contract_id`, annual_revenue.
- `GET /api/deals/<deal_id>/employees` — headcount, stable `employee_id`s, PTO liability, service-credit flags, WARN risk.
- `GET /api/deals/<deal_id>/regulatory` — HSR requirement, threshold basis, industry review, hell-or-high-water covenant.
- `GET /api/deals/<deal_id>/diligence-findings` — findings (stable `finding_id`) driving escrow/indemnity/special indemnity.
- `GET /api/deals/<deal_id>/notes` — negotiation posture and prior positions.

## Cross-table checks
- `POST /api/query` (token from `environment_access.md`, body is a read-only SQL request) — use for joins the GET endpoints can't express (e.g., matching consents to material contracts, or employees to holders). Read-only and secondary.
- `GET /api/search` — general lookup when the right record isn't known by id.

## Don'ts
- Do not fetch records for a similarly-named project and apply them to the prompt's `deal_id`.
- Do not call endpoints outside the `environment_access.md` allow-list.
