#!/usr/bin/env python3
"""Minimal read-only client for the Asteria Fleet Data Quality Hub.

Runtime connection details (base URL + bearer token) are NOT hard-coded. They
are read from the per-task `environment_access.md` file that ships with every
task. Point --env at that file (default: ./environment_access.md).

Usage as a library:
    from hub_client import Hub
    hub = Hub.from_env_file("environment_access.md")
    hub.sql("SELECT COUNT(*) FROM v_source_snapshots")      # -> {columns,rows,row_count,truncated}
    hub.sql_all("SELECT row_id FROM v_contacts WHERE ...")  # -> list[dict], auto-paginated
    hub.get("/api/source-snapshots", collection="fuel_purchases_2026_01")

Usage from the shell:
    python3 hub_client.py sql "SELECT snapshot_id, snapshot_status FROM v_source_snapshots WHERE collection_id='X'"
    python3 hub_client.py get /api/catalog/collections
"""
import json
import re
import sys
import urllib.request
import urllib.parse


class Hub:
    def __init__(self, base_url, token):
        self.base = base_url.rstrip("/") + "/"
        self.token = token

    @classmethod
    def from_env_file(cls, path="environment_access.md"):
        text = open(path, "r", encoding="utf-8").read()
        m_url = re.search(r"GDPEVO_ENV_BASE_URL\s*=\s*(\S+)", text)
        m_tok = re.search(r"Bearer\s+(\S+)", text)
        if not m_url or not m_tok:
            raise ValueError(f"Could not find base URL / bearer token in {path}")
        return cls(m_url.group(1), m_tok.group(1))

    def _headers(self, extra=None):
        h = {"Authorization": f"Bearer {self.token}"}
        if extra:
            h.update(extra)
        return h

    def get(self, path, **params):
        url = self.base.rstrip("/") + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def get_all(self, path, page=500, **params):
        """Follow limit/offset pagination on a REST list endpoint. Returns list of items."""
        out, offset = [], 0
        while True:
            page_data = self.get(path, limit=page, offset=offset, **params)
            items = page_data.get("items", [])
            out.extend(items)
            total = page_data.get("total")
            offset += page
            if not items or (total is not None and offset >= total):
                break
        return out

    def sql(self, query):
        req = urllib.request.Request(
            self.base.rstrip("/") + "/api/query",
            data=json.dumps({"query": query}).encode(),
            headers=self._headers({"Content-Type": "application/json"}),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())

    def sql_rows(self, query):
        """Run a query and return rows as list[dict]. Raises if the server truncated
        the result (>2000 rows) so you never silently lose data."""
        res = self.sql(query)
        cols = res["columns"]
        rows = [dict(zip(cols, row)) for row in res["rows"]]
        if res.get("truncated"):
            raise RuntimeError(
                "Query result was TRUNCATED at the 2000-row server cap. "
                "Aggregate server-side (GROUP BY/COUNT) or use sql_all() to page."
            )
        return rows

    def sql_all(self, query, page=1500):
        """Page a row-returning query with LIMIT/OFFSET to defeat the 2000-row cap.
        `query` must NOT already contain LIMIT/OFFSET and SHOULD contain an ORDER BY
        for a stable page order."""
        out, offset = [], 0
        while True:
            res = self.sql(f"{query} LIMIT {page} OFFSET {offset}")
            cols = res["columns"]
            batch = [dict(zip(cols, row)) for row in res["rows"]]
            out.extend(batch)
            if len(batch) < page:
                break
            offset += page
        return out


def _main(argv):
    env = "environment_access.md"
    if "--env" in argv:
        i = argv.index("--env")
        env = argv[i + 1]
        del argv[i : i + 2]
    hub = Hub.from_env_file(env)
    if not argv:
        print(__doc__)
        return
    cmd = argv[0]
    if cmd == "sql":
        print(json.dumps(hub.sql(argv[1]), indent=2))
    elif cmd == "get":
        params = dict(p.split("=", 1) for p in argv[2:])
        print(json.dumps(hub.get(argv[1], **params), indent=2))
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    _main(sys.argv[1:])
