"""Read-only Asteria Fleet Data Quality Hub client — credential-free template.

Base URL and bearer token are read from the task's `environment_access.md` so
this file works unchanged across task environments. Set them via
`configure(base, token)` or by setting ASTERIA_HUB_BASE / ASTERIA_HUB_TOKEN.

This client is intentionally READ-ONLY and contains NO judge endpoint: the
judge is a train-only evaluation fixture and is never part of the solving
procedure (see SKILL.md §1).
"""
import json
import os
import re
import urllib.error
import urllib.request
import urllib.parse

_BASE = os.environ.get("ASTERIA_HUB_BASE")
_TOKEN = os.environ.get("ASTERIA_HUB_TOKEN")


def configure(base, token):
    """Set hub base URL + bearer token for this process."""
    global _BASE, _TOKEN
    _BASE, _TOKEN = base, token


def _href(text):
    """Pull the first http(s) URL out of an environment_access.md blob."""
    m = re.search(r"https?://[^\s)`'\"]+", text or "")
    return m.group(0) if m else None


def _token(text):
    """Pull a bearer token out of an environment_access.md blob."""
    m = re.search(r"(?:bearer|token)[\s:=]+([A-Za-z0-9\-_.]+)", text or "", re.I)
    return m.group(1) if m else None


def configure_from_file(path):
    """Read environment_access.md and configure the client from it."""
    txt = open(path).read()
    base = _href(txt) or _BASE
    tok = _token(txt) or _TOKEN
    if base is None:
        raise RuntimeError("no hub base URL found in " + path)
    tok = tok or "asteria-read"
    configure(base.rstrip("/"), tok)
    return base, tok


def _get(path, params=None):
    if not _BASE:
        raise RuntimeError("call configure_from_file(env_access_path) first")
    url = _BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_TOKEN}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def _post(path, body):
    if not _BASE:
        raise RuntimeError("call configure_from_file(env_access_path) first")
    req = urllib.request.Request(
        _BASE + path,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


# ---- SQL (preferred for bulk reads) ----
def sql(query):
    """Run a read-only SQL query; returns (list_of_dicts, truncated).

    SQLite-flavored. Use single-quoted string literals (parameter binding is
    NOT supported). Whitelisted views only: v_contacts, v_fuel_transactions,
    v_freight_charges, v_maintenance_events, v_fx_rates, v_reference_aliases,
    v_unit_conversions, v_source_snapshots. LIKE / LOWER() / sqlite_master are
    rejected. Paginate with LIMIT/OFFSET.
    """
    res = _post("/api/query", {"query": query})
    if "error" in res:
        raise RuntimeError(f"query error: {res['error']} :: {query}")
    cols = res.get("columns", [])
    rows = [dict(zip(cols, row)) for row in res.get("rows", [])]
    return rows, res.get("truncated", False)


def sql_all(query, page=1000, max_pages=10000):
    """Run a query and auto-paginate by appending LIMIT/OFFSET until exhausted.
    (Caller's query must not already contain a LIMIT.) Returns list_of_dicts."""
    out, page_i = [], 0
    while page_i < max_pages:
        q = f"{query.rstrip(';')} LIMIT {page} OFFSET {page_i * page}"
        rows, truncated = sql(q)
        out.extend(rows)
        if len(rows) < page and not truncated:
            break
        page_i += 1
    return out


# ---- REST ----
def collections():
    return _get("/api/catalog/collections")


def schema():
    return _get("/api/catalog/schema")


def snapshots(collection_id):
    """Snapshot list. NOTE: the filter key is `collection`, not `collection_id`."""
    return _get("/api/source-snapshots", {"collection": collection_id})["items"]


def reference_aliases(domain):
    """domain = 'fuel' | 'freight'."""
    return _get("/api/reference/aliases", {"domain": domain})


def reference_conversions(kind):
    """kind = 'volume' | 'distance' | 'weight' | 'odometer'."""
    return _get("/api/reference/conversions", {"kind": kind})


def reference_fx():
    return _get("/api/reference/fx")


# Convenience: the authoritative snapshot by status precedence.
SNAP_ORDER = {"CERTIFIED": 0, "PROVISIONAL": 1, "STALE": 2}


def snapshot_rank(snap):
    return SNAP_ORDER.get(snap.get("snapshot_status"), 3)


def authoritative_snapshot(collection_id, tiebreak="snapshot_id"):
    """Return the snapshot dict to retain (best status; tiebreak ascending)."""
    snaps = snapshots(collection_id)
    return sorted(snaps, key=lambda s: (snapshot_rank(s), s.get(tiebreak)))[0], snaps
