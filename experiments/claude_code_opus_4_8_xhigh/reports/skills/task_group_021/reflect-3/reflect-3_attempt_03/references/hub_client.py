"""
Read-only client for the Asteria Fleet Data Quality Hub.

Reads the base URL and bearer token from `environment_access.md` at runtime
(never hardcode them), then exposes:
    get(path)                     -> (status, json)     e.g. get("/api/catalog/schema")
    query(sql)                    -> parsed query result ({columns, rows, ...})
    rows(sql)                     -> list[dict] (columns zipped onto each row)
    fetch_collection(view, cid)   -> list[dict] for one collection

This helper deliberately exposes only the read-only interfaces used to gather
evidence. It does not know about, and must not be used for, any feedback/scoring
endpoint.

Usage:
    import hub_client as hub
    hub.load("environment_access.md")          # or set env GDPEVO_ENV_BASE_URL / token
    print(hub.rows("SELECT * FROM v_source_snapshots LIMIT 3"))
"""
import json, os, re, urllib.request, urllib.parse, urllib.error

_BASE = None
_TOKEN = None


def load(access_file="environment_access.md"):
    """Parse base URL + bearer token from the runtime access file."""
    global _BASE, _TOKEN
    text = ""
    if os.path.exists(access_file):
        with open(access_file) as f:
            text = f.read()
    m = re.search(r"GDPEVO_ENV_BASE_URL\s*=\s*(\S+)", text)
    _BASE = (m.group(1) if m else os.environ.get("GDPEVO_ENV_BASE_URL", "")).rstrip("/") + "/"
    m = re.search(r"AUTHORIZATION:\s*Bearer\s+(\S+)", text, re.I)
    _TOKEN = m.group(1) if m else os.environ.get("GDPEVO_ENV_TOKEN", "")
    return _BASE, _TOKEN


def _ensure():
    if _BASE is None:
        load()


def _req(method, path, body=None):
    _ensure()
    url = urllib.parse.urljoin(_BASE, path.lstrip("/"))
    data = json.dumps(body).encode() if body is not None else None
    headers = {"AUTHORIZATION": f"Bearer {_TOKEN}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def get(path):
    return _req("GET", path)


def query(sql):
    st, resp = _req("POST", "/api/query", {"query": sql})
    if st != 200:
        raise RuntimeError(f"query failed {st}: {resp}")
    return resp


def rows(sql):
    r = query(sql)
    cols = r["columns"]
    out = [dict(zip(cols, row)) for row in r["rows"]]
    if r.get("truncated"):
        # 2000-row cap hit; narrow with WHERE/LIMIT-OFFSET or aggregate server-side.
        raise RuntimeError("result truncated at the row cap; refine the query")
    return out


def fetch_collection(view, collection_id, order_by=None):
    sql = f"SELECT * FROM {view} WHERE collection_id='{collection_id}'"
    if order_by:
        sql += f" ORDER BY {order_by}"
    return rows(sql)
