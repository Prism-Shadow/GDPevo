# Asteria Investment Office Environment

Shared Flask API for the institutional portfolio risk task group.

## Start

```bash
TASK_ENV_PORT=9010 env/setup.sh
```

or:

```bash
env/setup.sh
```

The service listens on `TASK_ENV_BIND` and defaults to port `9010`.

## Generate Data

```bash
python env/generate_data.py
```

This recreates deterministic JSON fixtures under `env/data/` and `env/manifest.json` using seed `20260603`.

## Endpoints

- `GET /` - HTML endpoint index.
- `GET /api/catalog` - available portfolio ids, policy ids, index ids, issuer ids, bond ids, and opportunity sets.
- `GET /api/policies` - portfolio constraints, correlation thresholds, and allocation mapping policy.
- `GET /api/portfolios` - portfolio summaries.
- `GET /api/portfolios/<portfolio_id>` - objective, constraints, and current holdings.
- `GET /api/instruments/bonds` - held and candidate bond universe.
- `GET /api/issuers` - issuer sector, subsector, rating bucket, watchlist, outlook, and tags.
- `GET /api/market/energy` - current oil, gas, LNG, refining, and renewables signals.
- `GET /api/indices` - index metadata.
- `GET /api/index-levels` - monthly index levels for all indices.
- `GET /api/index-levels/<index_id>` - monthly levels for one index.
- `GET /api/allocation/opportunity-sets` - cross-asset opportunity taxonomy.
- `GET /api/allocation/prior-views` - prior active allocation views.
- `GET /api/macro-signals` - current macro and asset-specific signal scores.

Most list endpoints support simple equality filters matching their field names, for example `?rating_bucket=HY`, `?candidate=true`, or `?quarter=Q3_2026`.
