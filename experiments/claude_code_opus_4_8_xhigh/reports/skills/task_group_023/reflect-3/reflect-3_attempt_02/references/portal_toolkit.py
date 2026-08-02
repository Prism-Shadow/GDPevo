"""
Generic Public Health Observatory portal toolkit.

Transferable helper for the PHO "registered algorithmic audit" task family.
Reads ONLY the read-only evidence portal whose base URL each task provides
(prompt.txt references it as a placeholder such as <TASK_ENV_BASE_URL>).

Contains NO task-specific values and does NOT contact any grader/scoring
service — it only loads and resolves published portal records.

Typical use:
    P = Portal(base_url)                 # base_url comes from the task
    rows = P.dataset("state_health")     # list[dict] of raw rows
    resolved = resolve_final(rows, ["state_abbr","year","measure_id"],
                             extra_filter=lambda r: r["value_type"]=="AGE_ADJUSTED"
                                              and r["source_type"]=="DIRECT_SURVEY")
"""
import csv, io, collections, urllib.request, urllib.parse

DATASETS = ["states", "counties", "countries", "state_health", "state_socioeconomic",
            "county_health", "county_socioeconomic", "country_indicators", "revisions"]

class Portal:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
    def dataset(self, name, **filters):
        # The portal exposes a CSV export of every dataset (linked as "CSV" from
        # /catalog and each /data/* page). Filters are optional query params.
        q = {"dataset": name, "format": "csv"}
        q.update({k: v for k, v in filters.items() if v is not None})
        url = self.base + "/download?" + urllib.parse.urlencode(q)
        with urllib.request.urlopen(url, timeout=120) as r:
            text = r.read().decode()
        return list(csv.DictReader(io.StringIO(text)))

def num(x):
    if x is None: return None
    x = str(x).strip()
    if x == "": return None
    try: return float(x)
    except ValueError: return None

def resolve_final(rows, key_fields, extra_filter=None,
                  status_field="release_status", rev_field="revision",
                  released_field="released_at", tiebreak_fields=()):
    """Registered-final-release resolution (see /methodology 'Surveillance release
    lifecycle'): drop PROVISIONAL, keep FINAL, take the HIGHEST revision; break
    ties by latest released_at then by any extra tiebreak id fields.

    Returns {key_tuple: winning_row}. A resolved row is still returned even when
    its value is suppressed — suppression affects *completeness*, not the count of
    resolved records.
    """
    g = collections.defaultdict(list)
    for r in rows:
        if r.get(status_field) != "FINAL": continue
        if extra_filter and not extra_filter(r): continue
        g[tuple(r[k] for k in key_fields)].append(r)
    out = {}
    for k, v in g.items():
        v.sort(key=lambda r: (int(r[rev_field]), r.get(released_field, ""),
                              *[r.get(tb, "") for tb in tiebreak_fields]))
        out[k] = v[-1]
    return out

def is_suppressed(row):
    return row.get("suppression_flag") == "1" or row.get("quality_flag") == "SUPPRESSED"

def value_or_none(row):
    """Usable value of a resolved health row, honouring suppression (never zero-fill)."""
    if row is None or is_suppressed(row): return None
    return num(row.get("value"))

# ---- geography helpers (state division/region, county rucc, country reconciliation) ----
def state_geo(portal):
    return {r["state_abbr"]: r for r in portal.dataset("states")}   # region, division, ...

def county_geo(portal):
    return {r["county_fips"]: r for r in portal.dataset("counties")}  # region, rucc, ...

def reconcile_country_labels(portal, requested_labels):
    """Map free-text portal labels to canonical countries using canonical_name,
    portal_label and the pipe-separated alternate_labels. Returns
    (resolved: {label->iso3}, alias_count, unresolved: [labels]).
    alias_count = resolved labels whose text differs from the canonical name."""
    idx = {}
    countries = portal.dataset("countries")
    for c in countries:
        keys = [c["canonical_name"], c["portal_label"]]
        keys += (c["alternate_labels"].split("|") if c.get("alternate_labels") else [])
        for k in keys:
            idx.setdefault(k.strip().lower(), c)
    resolved, alias, unresolved = {}, 0, []
    for lb in requested_labels:
        c = idx.get(lb.strip().lower())
        if c is None: unresolved.append(lb); continue
        resolved[lb] = c["iso3"]
        if lb.strip().lower() != c["canonical_name"].strip().lower(): alias += 1
    return resolved, alias, unresolved
