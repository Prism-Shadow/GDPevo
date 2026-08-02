"""
hub_toolkit.py — helpers for Fleet Data Quality Hub reconciliation tasks.

Read-only. Runtime connection details (base URL, auth header, endpoint list) are
parsed from the task's own `environment_access.md`; nothing is hardcoded. This
toolkit deliberately refuses to call any feedback/grading endpoint — solve from
the data in one shot.

Typical use:
    from hub_toolkit import Hub, norm_email, phone_digits, title_name, \
        resolve_category, validate
    hub = Hub.from_access("environment_access.md")
    rows = hub.query("SELECT * FROM v_source_snapshots WHERE collection_id=...")
"""
import json, re, unicodedata, urllib.request, urllib.parse

PLACEHOLDERS = {"", "n/a", "na", "none", "null", "unknown", "-"}


# ---------------------------------------------------------------- access / IO
def load_access(path="environment_access.md"):
    """Parse base URL, auth header, and endpoint list from environment_access.md."""
    base, auth, endpoints = None, None, []
    with open(path) as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if "BASE_URL" in s and "=" in s:
                base = s.split("=", 1)[1].strip()
            elif s.lower().startswith("authorization:"):
                auth = s.split(":", 1)[1].strip()
            elif re.match(r"^(GET|POST)\s+/", s):
                method, path_ = s.split(None, 1)
                endpoints.append((method.upper(), path_.strip()))
    if base and not base.endswith("/"):
        base += "/"
    return {"base": base, "auth": auth, "endpoints": endpoints}


class Hub:
    def __init__(self, base, auth, endpoints=None):
        self.base = base.rstrip("/")
        self.auth = auth
        self.endpoints = endpoints or []

    @classmethod
    def from_access(cls, path="environment_access.md"):
        a = load_access(path)
        return cls(a["base"], a["auth"], a["endpoints"])

    def _headers(self):
        h = {}
        if self.auth:
            h["Authorization"] = self.auth
        return h

    def _query_path(self):
        for m, p in self.endpoints:
            if m == "POST" and "query" in p and "judge" not in p:
                return p
        return "/api/query"

    def _guard(self, path):
        # never contact a feedback/grading endpoint from a solver
        if "judge" in path or "feedback" in path or "grade" in path:
            raise RuntimeError("refusing to call a feedback/grading endpoint")

    def get(self, path, **params):
        self._guard(path)
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def query(self, sql):
        """Run a read-only SQL query; return a list of dict rows.

        Pages automatically if the interface reports truncation and the query is
        ordered by a single ascending text/number key.
        """
        path = self._query_path()
        self._guard(path)
        rows, cols = [], None
        offset_clause = ""
        while True:
            body = json.dumps({"query": sql + offset_clause}).encode()
            req = urllib.request.Request(
                self.base + path, data=body, method="POST",
                headers={**self._headers(), "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read())
            cols = resp["columns"]
            page = [dict(zip(cols, row)) for row in resp["rows"]]
            rows.extend(page)
            if not resp.get("truncated") or not page:
                break
            # naive keyset paging on the first selected column if present
            offset_clause = f" LIMIT 100000 OFFSET {len(rows)}"
        return rows


# ---------------------------------------------------------------- normalizers
def norm_text(s):
    if s is None:
        return None
    s = unicodedata.normalize("NFKC", str(s)).strip()
    return None if s.lower() in PLACEHOLDERS else s


def norm_email(s):
    s = norm_text(s)
    return s.lower() if s else None


def phone_digits(s, keep_country_code=False):
    s = norm_text(s)
    if s is None:
        return None
    d = re.sub(r"\D", "", s)
    if not d:
        return None
    # national form: drop a leading country code on 11+ digit numbers
    if not keep_country_code and len(d) > 10 and d[0] == "1":
        d = d[1:]
    return d


def title_name(s):
    s = norm_text(s)
    return s.title() if s else None


# ---------------------------------------------------------------- resolvers
def resolve_category(description, business_date, aliases):
    """Return ('recognized', class) | ('ambiguous', None) | ('unrecognized', None).

    aliases: iterable of dicts with alias_text, canonical_value, reference_status,
    valid_from, valid_to (dates as 'YYYY-...' strings or None).
    Whole-word match; longest matched alias wins over shorter contained ones.
    """
    d = (description or "").lower()
    bd = business_date[:10]
    matched = []
    for a in aliases:
        if a.get("reference_status") != "ACTIVE":
            continue
        vf, vt = a.get("valid_from"), a.get("valid_to")
        if vf and bd < vf[:10]:
            continue
        if vt and bd > vt[:10]:
            continue
        at = a["alias_text"].lower()
        if re.search(r"(?<![a-z0-9])" + re.escape(at) + r"(?![a-z0-9])", d):
            matched.append((at, a["canonical_value"]))
    texts = [t for t, _ in matched]
    survivors = {cv for t, cv in matched if not any(t != o and t in o for o in texts)}
    if len(survivors) == 1:
        return ("recognized", next(iter(survivors)))
    if not survivors:
        return ("unrecognized", None)
    return ("ambiguous", None)


def fx_table(rows, status="CERTIFIED"):
    """rows from v_fx_rates -> {(currency, rate_date): usd_per_unit} for a status."""
    return {(r["currency"], r["rate_date"]): r["usd_per_unit"]
            for r in rows if r.get("rate_status") == status}


def conversion_table(rows, kind):
    """rows from v_unit_conversions -> {from_unit: factor} for a kind."""
    return {r["from_unit"]: r["factor"] for r in rows if r["kind"] == kind}


def dedup_logical(rows, key, authoritative_snapshot):
    """Collapse raw rows to one per business key, preferring the authoritative
    (certified) snapshot's occurrence."""
    by = {}
    for r in rows:
        k = r[key]
        if k not in by or r.get("snapshot_id") == authoritative_snapshot:
            by[k] = r
    return by


# ---------------------------------------------------------------- validation
def validate(obj, schema, path="$"):
    """Minimal JSON-Schema check for self-verifying an answer. Returns a list of
    human-readable error strings ([] means it conforms to the checked subset)."""
    errs = []
    t = schema.get("type")
    if t == "object" or "properties" in schema or "required" in schema:
        if not isinstance(obj, dict):
            return [f"{path}: expected object"]
        for k in schema.get("required", []):
            if k not in obj:
                errs.append(f"{path}.{k}: missing required")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in obj:
                if k not in props:
                    errs.append(f"{path}.{k}: unexpected key")
        for k, v in obj.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
    elif t == "array":
        if not isinstance(obj, list):
            return [f"{path}: expected array"]
        if "minItems" in schema and len(obj) < schema["minItems"]:
            errs.append(f"{path}: <{schema['minItems']} items")
        if "maxItems" in schema and len(obj) > schema["maxItems"]:
            errs.append(f"{path}: >{schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(x, sort_keys=True) for x in obj]
            if len(set(seen)) != len(seen):
                errs.append(f"{path}: items not unique")
        if "items" in schema:
            for i, x in enumerate(obj):
                errs += validate(x, schema["items"], f"{path}[{i}]")
    else:
        if "enum" in schema and obj not in schema["enum"]:
            errs.append(f"{path}: {obj!r} not in enum")
        if schema.get("type") == "integer" and not isinstance(obj, int):
            errs.append(f"{path}: expected integer")
        if schema.get("type") == "string":
            if not isinstance(obj, str):
                errs.append(f"{path}: expected string")
            elif "pattern" in schema and not re.search(schema["pattern"], obj):
                errs.append(f"{path}: {obj!r} !~ /{schema['pattern']}/")
        if "multipleOf" in schema and isinstance(obj, (int, float)):
            q = obj / schema["multipleOf"]
            if abs(q - round(q)) > 1e-6:
                errs.append(f"{path}: {obj} not multiple of {schema['multipleOf']}")
    return errs


if __name__ == "__main__":
    import sys
    hub = Hub.from_access(sys.argv[1] if len(sys.argv) > 1 else "environment_access.md")
    print(json.dumps(hub.query("SELECT collection_id FROM v_source_snapshots LIMIT 5"),
                     indent=2))
