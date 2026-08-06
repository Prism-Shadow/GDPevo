"""Truncation-safe data-access client for licensing-review tasks.

Reads the base URL and the SQL auth token from the task's own
`environment_access.md` (nothing is hardcoded, so this works across tasks).

Key rule this class enforces: the data service caps every response at ~200 rows.
Some tables exceed that, so ALWAYS scope reads to your target ids with a SQL
WHERE ... IN (...) filter and let `sql()` raise if the result was truncated.
"""
import json, re, urllib.request


def read_access(env_path="environment_access.md"):
    text = open(env_path).read()
    m_base = re.search(r"BASE_URL\s*=\s*(\S+)", text)
    m_tok = re.search(r"X-Task-Token:\s*(\S+)", text)
    base = m_base.group(1).rstrip("/") if m_base else None
    token = m_tok.group(1) if m_tok else None
    return base, token


class EnvClient:
    def __init__(self, env_path="environment_access.md"):
        self.base, self.token = read_access(env_path)
        if not self.base:
            raise RuntimeError("could not find base URL in " + env_path)

    def get(self, path):
        """GET a REST endpoint (returns a list). Note: also capped at 200 rows;
        prefer sql() with a WHERE filter for anything that might be larger."""
        if not path.startswith("/"):
            path = "/" + path
        with urllib.request.urlopen(self.base + path, timeout=30) as r:
            return json.loads(r.read())

    def sql(self, query):
        """POST /api/sql with the task token. Raises on error or truncation."""
        body = json.dumps({"query": query}).encode()
        req = urllib.request.Request(
            self.base + "/api/sql", data=body,
            headers={"Content-Type": "application/json",
                     "X-Task-Token": self.token})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        if "rows" not in d:
            raise RuntimeError("sql error: " + json.dumps(d))
        if d.get("truncated"):
            raise RuntimeError("sql result truncated; narrow the WHERE filter: " + query)
        return d["rows"]

    def count(self, table):
        return self.sql("SELECT COUNT(*) AS n FROM " + table)[0]["n"]

    @staticmethod
    def inlist(vals):
        """Render a python list as a SQL IN (...) tuple, safely quoted."""
        return "(" + ",".join("'" + str(v).replace("'", "''") + "'" for v in vals) + ")"
