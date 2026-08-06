#!/usr/bin/env python3
"""Read-only client for the Asteria Fleet Data Quality Hub.

The hub exposes REST resources plus a read-only SQL endpoint (`/api/query`).
This client reads the base URL and bearer token from `environment_access.md`
(found next to the task, or via --env), so nothing about the connection is
hard-coded. It works with only the Python standard library.

Typical use from a solving agent:

    # one-shot SQL (the SQL endpoint returns *all* rows, no pagination cap)
    python3 hub_client.py sql "SELECT COUNT(*) FROM v_fuel_transactions
                               WHERE collection_id='<COLLECTION_ID>'"

    # a REST resource (auto-follows limit/offset until 'total' is reached)
    python3 hub_client.py get /api/source-snapshots collection=<COLLECTION_ID>

Importable:

    from hub_client import Hub
    hub = Hub.from_env("environment_access.md")
    rows = hub.rows("SELECT * FROM v_source_snapshots WHERE collection_id=:c",
                    c="<COLLECTION_ID>")
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def _find_env(path=None):
    """Locate environment_access.md by walking up from cwd if not given."""
    if path and os.path.exists(path):
        return path
    here = os.getcwd()
    for _ in range(6):
        cand = os.path.join(here, "environment_access.md")
        if os.path.exists(cand):
            return cand
        here = os.path.dirname(here)
    raise FileNotFoundError("environment_access.md not found; pass --env <path>")


def parse_env(path=None):
    """Return (base_url, bearer_token) parsed from environment_access.md."""
    text = open(_find_env(path)).read()
    base = re.search(r"(?:GDPEVO_ENV_BASE_URL\s*=\s*)?(https?://[^\s]+)", text)
    tok = re.search(r"Bearer\s+([^\s]+)", text, re.IGNORECASE)
    if not base:
        raise ValueError("No base URL found in environment_access.md")
    if not tok:
        raise ValueError("No 'Bearer <token>' found in environment_access.md")
    return base.group(1).rstrip("/"), tok.group(1)


class Hub:
    def __init__(self, base_url, token, timeout=60):
        self.base = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    @classmethod
    def from_env(cls, path=None, timeout=60):
        base, tok = parse_env(path)
        return cls(base, tok, timeout)

    def _req(self, path, data=None):
        headers = {"Authorization": "Bearer " + self.token}
        if data is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data).encode()
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, {"error": e.read().decode()}

    # ---- SQL endpoint --------------------------------------------------
    def query(self, sql, **binds):
        """POST /api/query. Simple :name binds are substituted as SQL literals
        (strings quoted, numbers inlined). Returns the raw response dict with
        keys: columns, rows, row_count, truncated."""
        for k, v in binds.items():
            lit = str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'"
            sql = re.sub(r":" + re.escape(k) + r"\b", lit, sql)
        st, body = self._req("/api/query", {"query": sql})
        if st != 200:
            raise RuntimeError("query failed %s: %s" % (st, body))
        return body

    def rows(self, sql, **binds):
        """Return SQL results as a list of dicts."""
        r = self.query(sql, **binds)
        cols = r["columns"]
        return [dict(zip(cols, row)) for row in r["rows"]]

    def scalar(self, sql, **binds):
        r = self.query(sql, **binds)
        return r["rows"][0][0] if r["rows"] else None

    # ---- REST resources ------------------------------------------------
    def get(self, path, **params):
        """GET a REST resource. If the response is a paginated envelope
        ({items,total,limit,offset}) this follows pages and returns the full
        concatenated items list; otherwise it returns the parsed body."""
        if params:
            qs = urllib.parse.urlencode(params)
            path = path + ("&" if "?" in path else "?") + qs
        st, body = self._req(path)
        if st != 200:
            raise RuntimeError("GET %s failed %s: %s" % (path, st, body))
        if isinstance(body, dict) and "items" in body and "total" in body:
            items = list(body["items"])
            total = body["total"]
            limit = body.get("limit") or len(items) or 100
            offset = len(items)
            while offset < total:
                sep = "&" if "?" in path else "?"
                st, page = self._req("%s%soffset=%d&limit=%d" % (path, sep, offset, limit))
                if st != 200 or not page.get("items"):
                    break
                items.extend(page["items"])
                offset += len(page["items"])
            return items
        return body


def _main(argv):
    env = None
    if "--env" in argv:
        i = argv.index("--env")
        env = argv[i + 1]
        del argv[i:i + 2]
    if len(argv) < 2:
        print(__doc__)
        return 1
    hub = Hub.from_env(env)
    cmd = argv[1]
    if cmd == "sql":
        print(json.dumps(hub.query(argv[2]), indent=1))
    elif cmd == "get":
        params = dict(kv.split("=", 1) for kv in argv[3:])
        print(json.dumps(hub.get(argv[2], **params), indent=1)[:200000])
    else:
        print("unknown command:", cmd)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
