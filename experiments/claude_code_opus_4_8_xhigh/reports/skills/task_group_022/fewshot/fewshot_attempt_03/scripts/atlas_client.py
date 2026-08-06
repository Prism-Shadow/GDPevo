#!/usr/bin/env python3
"""Thin client for the Atlas Commerce Operations workplace service.

Reads the base URL and bearer token from an ``environment_access.md`` file
(the one staged alongside the task), then exposes the documented endpoints:

    GET  /api/schema
    GET  /api/data-dictionary
    GET  /api/correction-audit
    POST /api/sql               {"sql": "..."}
    POST /api/sql/transaction   {"statements": [...]}  (shape probed at runtime)

Only Python stdlib is used (urllib), so it runs anywhere.

CLI usage (handy for exploration; every call retries on transient 5xx):

    python3 atlas_client.py schema
    python3 atlas_client.py dict
    python3 atlas_client.py audit
    python3 atlas_client.py sql "SELECT count(*) AS c FROM some_table"
    python3 atlas_client.py sql-file query.sql
    python3 atlas_client.py introspect        # best-effort table/column list

Import usage:

    from atlas_client import AtlasClient
    c = AtlasClient.from_access_file("environment_access.md")
    rows = c.sql("SELECT 1 AS x")["rows"]
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DEFAULT_ACCESS_CANDIDATES = [
    "environment_access.md",
    "input/environment_access.md",
    "../environment_access.md",
    "/work/environment_access.md",
]


class AtlasClient:
    def __init__(self, base_url, token, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    # ---- construction -----------------------------------------------------
    @classmethod
    def from_access_file(cls, path=None, **kw):
        text = None
        candidates = [path] if path else DEFAULT_ACCESS_CANDIDATES
        for cand in candidates:
            if cand and os.path.exists(cand):
                with open(cand) as fh:
                    text = fh.read()
                break
        if text is None:
            raise FileNotFoundError(
                "environment_access.md not found; pass an explicit path. "
                "Tried: %s" % ", ".join(str(c) for c in candidates)
            )
        base = re.search(r"Base URL:\s*(\S+)", text)
        tok = re.search(r"Bearer\s+(\S+)", text)
        if not base or not tok:
            raise ValueError("Could not parse Base URL / Bearer token from access file")
        return cls(base.group(1), tok.group(1), **kw)

    # ---- low level --------------------------------------------------------
    def _request(self, method, path, body=None, retries=6, backoff=1.5):
        url = self.base_url + path
        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        last = None
        for attempt in range(retries):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                payload = e.read().decode(errors="replace")
                last = "HTTP %s: %s" % (e.code, payload[:400])
                # 5xx are often transient (catalog warming up) -> retry
                if 500 <= e.code < 600 and attempt < retries - 1:
                    time.sleep(backoff * (attempt + 1))
                    continue
                # 4xx is a real client error; surface it immediately
                raise RuntimeError("%s %s -> %s" % (method, path, last))
            except (urllib.error.URLError, TimeoutError) as e:
                last = str(e)
                if attempt < retries - 1:
                    time.sleep(backoff * (attempt + 1))
                    continue
                raise RuntimeError("%s %s -> %s" % (method, path, last))
        raise RuntimeError("%s %s failed after retries -> %s" % (method, path, last))

    # ---- documented endpoints --------------------------------------------
    def schema(self):
        return self._request("GET", "/api/schema")

    def data_dictionary(self):
        return self._request("GET", "/api/data-dictionary")

    def correction_audit(self):
        return self._request("GET", "/api/correction-audit")

    def sql(self, query):
        return self._request("POST", "/api/sql", {"sql": query})

    def transaction(self, statements):
        """Controlled write endpoint.

        The exact request shape is environment-specific; the schema/data
        dictionary document it. ``statements`` may be a list of SQL strings or
        a list of {"sql": ..., "params": ...} objects. Confirm the accepted
        shape before mutating (see references/playbook.md, correction task).
        """
        return self._request("POST", "/api/sql/transaction", {"statements": statements})

    # ---- best-effort introspection (when /api/schema is unavailable) ------
    def introspect(self):
        """Try several catalogs to list tables+columns. Returns whatever works.

        The service's SQL validator may block system catalogs; if so this
        returns an empty dict and you should rely on GET /api/schema and
        GET /api/data-dictionary instead.
        """
        attempts = [
            "SELECT table_name, column_name, data_type FROM information_schema.columns "
            "WHERE table_schema NOT IN ('pg_catalog','information_schema') "
            "ORDER BY table_name, ordinal_position",
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        ]
        for q in attempts:
            try:
                return self.sql(q)
            except Exception:
                continue
        return {}


def _pp(obj):
    print(json.dumps(obj, indent=2, default=str))


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    client = AtlasClient.from_access_file(os.environ.get("ATLAS_ACCESS_FILE"))
    cmd = argv[0]
    if cmd == "schema":
        _pp(client.schema())
    elif cmd == "dict":
        _pp(client.data_dictionary())
    elif cmd == "audit":
        _pp(client.correction_audit())
    elif cmd == "introspect":
        _pp(client.introspect())
    elif cmd == "sql":
        _pp(client.sql(argv[1]))
    elif cmd == "sql-file":
        with open(argv[1]) as fh:
            _pp(client.sql(fh.read()))
    else:
        print("unknown command: %s" % cmd)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
