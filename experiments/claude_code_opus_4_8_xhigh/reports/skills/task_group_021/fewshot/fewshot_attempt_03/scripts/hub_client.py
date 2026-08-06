#!/usr/bin/env python3
"""
hub_client.py — thin, dependency-free client for the Asteria Fleet Data Quality Hub.

Reads the base URL and bearer token from the task's `environment_access.md`
(never hard-code them: they rotate per environment). Provides:

    HubClient.get(path)           -> parsed JSON of a GET endpoint
    HubClient.get_all(path, ...)  -> auto-paginated list for {items,total,limit,offset} endpoints
    HubClient.query(sql)          -> {columns, rows, row_count, truncated} from POST /api/query
    HubClient.rows(sql)           -> list[dict] convenience wrapper over query()

CLI:
    python3 hub_client.py catalog
    python3 hub_client.py schema
    python3 hub_client.py snapshots <collection_id>
    python3 hub_client.py sql "SELECT ... "
    python3 hub_client.py get /api/contacts?collection=<id>

Only standard library is used (urllib) so it runs anywhere Python 3 is present.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

DEFAULT_ENV_FILES = [
    "environment_access.md",
    "input/environment_access.md",
    "../environment_access.md",
    "/work/environment_access.md",
]


def _find_env_file(explicit=None):
    candidates = ([explicit] if explicit else []) + DEFAULT_ENV_FILES
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    # last resort: walk up from cwd
    d = os.getcwd()
    for _ in range(6):
        p = os.path.join(d, "environment_access.md")
        if os.path.isfile(p):
            return p
        d = os.path.dirname(d)
    raise FileNotFoundError(
        "environment_access.md not found; pass its path explicitly to HubClient()."
    )


def parse_env_access(path=None):
    """Return (base_url, bearer_token) parsed from environment_access.md."""
    path = _find_env_file(path)
    text = open(path, "r", encoding="utf-8").read()
    base = None
    token = None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"(?i)^GDPEVO_ENV_BASE_URL\s*=\s*(\S+)", s)
        if m:
            base = m.group(1).rstrip("/")
        m = re.match(r"(?i)^AUTHORIZATION\s*:\s*Bearer\s+(\S+)", s)
        if m:
            token = m.group(1)
    if not base or not token:
        raise ValueError(f"Could not parse base URL / bearer token from {path}")
    return base, token


class HubClient:
    def __init__(self, env_path=None, timeout=30):
        self.base, self.token = parse_env_access(env_path)
        self.timeout = timeout
        self._auth = {"Authorization": f"Bearer {self.token}"}

    def _open(self, req):
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {e.code} for {req.full_url}: {body}") from None

    def get(self, path):
        url = self.base + (path if path.startswith("/") else "/" + path)
        req = urllib.request.Request(url, headers=self._auth, method="GET")
        return self._open(req)[1]

    def get_all(self, path, page_size=500):
        """Auto-paginate an {items,total,limit,offset} REST endpoint into one list."""
        sep = "&" if "?" in path else "?"
        items, offset = [], 0
        while True:
            page = self.get(f"{path}{sep}limit={page_size}&offset={offset}")
            batch = page.get("items", [])
            items.extend(batch)
            total = page.get("total")
            offset += len(batch)
            if not batch or (total is not None and offset >= total):
                break
        return items

    def query(self, sql):
        url = self.base + "/api/query"
        data = json.dumps({"query": sql}).encode()
        req = urllib.request.Request(
            url, headers={**self._auth, "Content-Type": "application/json"},
            method="POST", data=data,
        )
        return self._open(req)[1]

    def rows(self, sql):
        res = self.query(sql)
        cols = res["columns"]
        if res.get("truncated"):
            sys.stderr.write("WARNING: query result was truncated; narrow the query.\n")
        return [dict(zip(cols, r)) for r in res["rows"]]


def _main(argv):
    if not argv:
        print(__doc__)
        return 0
    hc = HubClient()
    cmd = argv[0]
    if cmd == "catalog":
        print(json.dumps(hc.get("/api/catalog/collections"), indent=2))
    elif cmd == "schema":
        print(json.dumps(hc.get("/api/catalog/schema"), indent=2))
    elif cmd == "snapshots":
        cid = argv[1]
        print(json.dumps(hc.rows(
            "SELECT snapshot_id, snapshot_status, source_system, business_cutoff, row_count "
            f"FROM v_source_snapshots WHERE collection_id='{cid}' ORDER BY snapshot_id"), indent=2))
    elif cmd == "sql":
        print(json.dumps(hc.query(argv[1]), indent=2))
    elif cmd == "get":
        print(json.dumps(hc.get(argv[1]), indent=2))
    else:
        sys.stderr.write(f"unknown command: {cmd}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
