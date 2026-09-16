# Bundled scripts

## `fetch_all.py`

Handles cursor-based pagination for Asteria DQ Hub endpoints that paginate
(`/api/contacts`, `/api/transactions/fuel`, `/api/transactions/freight`,
`/api/maintenance/events`, and `/api/query`).

### Usage

```bash
python3 /work/skill/scripts/fetch_all.py <URL> [--query FILE]
```

**Arguments:**

- `URL` — full endpoint URL including the base URL from `environment_access.md`.
- `--query FILE` — path to a JSON file containing the POST body for `/api/query`.
  Optional; if omitted, the script sends a GET request.

### Behavior

1. Sends the initial request (GET or POST).
2. Extracts `next_cursor` from the response.
3. If `next_cursor` is non-null, sends the next request with `?cursor=...` (for
   GET) or `{"cursor": "..."}` in the body (for POST).
4. Accumulates all rows into a single JSON array.
5. Writes the complete array to stdout.

### Example

```bash
# Fetch all fuel transactions
python3 /work/skill/scripts/fetch_all.py "http://task-env:9021/api/transactions/fuel" > /tmp/fuel.json

# Fetch all freight charges
python3 /work/skill/scripts/fetch_all.py "http://task-env:9021/api/transactions/freight" > /tmp/freight.json

# Fetch all maintenance events
python3 /work/skill/scripts/fetch_all.py "http://task-env:9021/api/maintenance/events" > /tmp/events.json

# Query with filtering
echo '{"collection_id":"some_collection","filters":[],"limit":500}' > /tmp/query.json
python3 /work/skill/scripts/fetch_all.py "http://task-env:9021/api/query" --query /tmp/query.json > /tmp/results.json
```

### Notes

- The script uses only the Python standard library (`urllib`, `json`). No
  dependencies required.
- Authentication credentials from `environment_access.md` are not passed
  automatically; add headers as needed if the hub requires them.
- The script handles both GET and POST pagination patterns transparently.\n