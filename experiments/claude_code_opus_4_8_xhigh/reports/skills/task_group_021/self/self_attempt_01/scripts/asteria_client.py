#!/usr/bin/env python3
"""
Asteria Fleet Data Quality Hub — authenticated read-only client helper.

This is a *starting point*, not a finished solution. It handles the two things
that are stable across every task in this family:

  1. Reading the base URL and bearer token from `environment_access.md`.
  2. Sending authenticated GET / POST requests and returning parsed JSON.

Pagination shape, query-body shape, and field names are NOT assumed — discover
them at runtime from `/api/catalog/collections`, `/api/catalog/schema`, and the
first response envelope, then adapt `get_all()` / `query()` accordingly.

Uses only the Python standard library (no external deps).

Typical use:
    from asteria_client import Hub
    hub = Hub.from_env("environment_access.md")
    print(hub.get("/api/catalog/collections"))
    print(hub.get("/api/catalog/schema"))
    rows = hub.get_all("/api/contacts", params={"collection_id": "..."})
    result = hub.query({"collection": "...", "select": "..."})  # shape TBD from schema

CLI (ad-hoc exploration while you learn the API):
    python3 asteria_client.py GET /api/catalog/collections
    python3 asteria_client.py GET /api/source-snapshots
    python3 asteria_client.py POST /api/query '{"...": "..."}'
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_ENV_FILE = "environment_access.md"


def load_access(env_file: str = DEFAULT_ENV_FILE):
    """Parse base URL and Authorization header value out of environment_access.md.

    The file format seen across tasks:
        GDPEVO_ENV_BASE_URL=http://task-env:9021/
        AUTHORIZATION: Bearer <token>
        <endpoint lines...>
    Returns (base_url, auth_header_value). Never hardcode the token; it is read
    fresh from the runtime file each time.
    """
    base_url = None
    auth = None
    with open(env_file, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            m = re.match(r"^([A-Z0-9_]+)\s*=\s*(.+)$", line)
            if m and m.group(1).endswith("BASE_URL"):
                base_url = m.group(2).strip()
                continue
            m = re.match(r"^AUTHORIZATION\s*:\s*(.+)$", line, re.IGNORECASE)
            if m:
                auth = m.group(1).strip()
                continue
    if not base_url:
        raise RuntimeError(f"No *BASE_URL line found in {env_file}")
    if not auth:
        raise RuntimeError(f"No AUTHORIZATION line found in {env_file}")
    return base_url.rstrip("/") + "/", auth


class Hub:
    def __init__(self, base_url: str, auth: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/") + "/"
        self.auth = auth
        self.timeout = timeout

    @classmethod
    def from_env(cls, env_file: str = DEFAULT_ENV_FILE, timeout: float = 60.0):
        base_url, auth = load_access(env_file)
        return cls(base_url, auth, timeout=timeout)

    def _url(self, path: str, params: dict | None = None) -> str:
        url = urllib.parse.urljoin(self.base_url, path.lstrip("/"))
        if params:
            sep = "&" if "?" in url else "?"
            url = url + sep + urllib.parse.urlencode(params, doseq=True)
        return url

    def _request(self, method: str, path: str, params=None, body=None):
        url = self._url(path, params)
        data = None
        headers = {"Authorization": self.auth, "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {e.code} on {method} {url}: {detail}") from None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def get(self, path: str, params: dict | None = None):
        return self._request("GET", path, params=params)

    def post(self, path: str, body: dict | None = None, params: dict | None = None):
        return self._request("POST", path, params=params, body=body)

    def query(self, body: dict):
        """POST /api/query. Discover the exact request/response shape from the
        catalog+schema before relying on this."""
        return self.post("/api/query", body=body)

    # --- pagination ---------------------------------------------------------
    # The envelope is unknown until you look. This helper handles the common
    # patterns; verify against a real first page and adjust the key names.
    _LIST_KEYS = ("items", "rows", "data", "records", "results")
    _NEXT_CURSOR_KEYS = ("next_cursor", "nextCursor", "cursor", "next", "next_page_token")

    def get_all(self, path: str, params: dict | None = None, page_limit: int = 10000):
        """Follow pagination until exhausted and return a flat list of rows.

        Handles three common shapes:
          * bare JSON array                     -> returned as-is
          * {"items":[...], "next_cursor": ...} -> follows cursor
          * {"items":[...], total/page/limit}   -> increments page/offset
        If the real API differs, read the first response and adapt.
        """
        params = dict(params or {})
        out = []
        seen_cursor = set()
        for _ in range(page_limit):
            resp = self.get(path, params=params)
            if resp is None:
                break
            if isinstance(resp, list):
                out.extend(resp)
                break  # bare array: assume single page unless params drive paging
            if not isinstance(resp, dict):
                break
            rows = None
            for k in self._LIST_KEYS:
                if isinstance(resp.get(k), list):
                    rows = resp[k]
                    break
            if rows is None:
                # Unknown envelope: hand it back for manual inspection.
                out.append(resp)
                break
            out.extend(rows)
            cursor = next((resp.get(k) for k in self._NEXT_CURSOR_KEYS if resp.get(k)), None)
            if cursor:
                if cursor in seen_cursor:
                    break
                seen_cursor.add(cursor)
                params["cursor"] = cursor
                continue
            # offset/page style
            if "offset" in params or "limit" in params:
                limit = int(params.get("limit", len(rows) or 1))
                if len(rows) < limit:
                    break
                params["offset"] = int(params.get("offset", 0)) + len(rows)
                continue
            if "page" in params:
                total = resp.get("total") or resp.get("total_count")
                params["page"] = int(params["page"]) + 1
                if total is not None and len(out) >= int(total):
                    break
                if not rows:
                    break
                continue
            break  # no pagination signal: single page
        return out


def _cli(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    method = argv[0].upper()
    path = argv[1]
    body = json.loads(argv[2]) if len(argv) > 2 else None
    hub = Hub.from_env()
    if method == "GET":
        result = hub.get(path)
    else:
        result = hub.post(path, body=body)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
