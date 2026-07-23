# Environment Access

## Connection

- The base URL and credentials live in the task's `environment_access.md`. Read it at the start of every run; do not hardcode URLs or tokens (they vary by task group).
- `POST /api/sql` requires the request header `X-Task-Token: <token from environment_access.md>`. GET endpoints do not require the token unless the access file says so.
- Use ONLY the endpoints listed in `environment_access.md`. Do not invent paths and do not probe other URLs.

## Endpoint catalog

The environment exposes a read-only licensing dataset. Endpoints group by domain.

**Cross-cutting**
- `GET /api/policies` — current and prior policy baselines (currency thresholds, endorsement requirements, policy-impact comparison). Fetch first for every task.
- `GET /api/renewal/rules` — renewal-queue rules: violation→next_step_label and →risk_tier mappings, boundary semantics, match-confidence rules. Fetch for Type C tasks.
- `POST /api/sql` — read-only SQL over the dataset (see below).

**Contractor licensing (Type A)**
- `GET /api/contractor/applications` — applications in the batch.
- `GET /api/contractor/bonds` — surety bonds (amount, status, dates).
- `GET /api/contractor/insurance` — insurance certificates (coverage window, amount, status).
- `GET /api/contractor/license-history` — prior licenses, suspensions.
- `GET /api/contractor/violations` — open/closed violations and complaints.
- `GET /api/contractor/correspondence` — case correspondence (for stale/unverified flags).
- `GET /api/contractor/inspections` — inspection records and documentation.

**Liquor licensing (Type B)**
- `GET /api/liquor/applications` — the target application and premises.
- `GET /api/liquor/settlements` — prior settlements, same-premises basis, tax holds.
- `GET /api/liquor/privileges` — granted privileges/controls in place.
- `GET /api/liquor/incidents` — incidents and police memos.
- `GET /api/liquor/site-evidence` — floor plans, signage, photos, camera/food-service evidence.

**Alcohol licensing & renewal (Type C)**
- `GET /api/alcohol/licensees` — licenses and facility addresses.
- `GET /api/alcohol/violations` — violations with dates, linked license numbers, categories.

## SQL usage

`POST /api/sql` runs read-only queries over the same dataset. Send the `X-Task-Token` header. Use it when a REST endpoint would force many round-trips:

- Join licensees to violations by `license_no` AND by facility address (to find `close_address` matches via old/prior license numbers).
- Aggregate per-application deficiency counts, or per-license violation counts and most-recent dates.
- Collect and sort correspondence flagged stale/unverified.

Rules:

- Issue `SELECT` only. Never `INSERT`/`UPDATE`/`DELETE` — the dataset is read-only for analysis.
- Keep queries scoped to the target entities (filter by the application/license IDs from the prompt) to avoid pulling unrelated rows.
- Treat SQL results as a convenience layer over the REST data; cross-check surprising results against the REST endpoints.

## Network discipline

- Reach the environment only through the base URL in `environment_access.md`.
- If an endpoint returns paged results, page through them until exhausted before deriving counts or lists.
- Do not retry failed mutations or attempt endpoints not listed in the access file.
