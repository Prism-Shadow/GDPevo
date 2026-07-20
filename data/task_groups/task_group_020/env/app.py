import os
import re
import sqlite3
from pathlib import Path

from flask import Flask, abort, jsonify, render_template_string, request


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "ma_workbench.db"
QUERY_TOKEN = "deal-workbench-readonly"

RELATED_ENDPOINTS = {
    "terms": "/api/deals/{deal_id}/terms",
    "documents": "/api/deals/{deal_id}/documents",
    "benchmarks": "/api/deals/{deal_id}/benchmarks",
    "risk_estimates": "/api/deals/{deal_id}/risk-estimates",
    "cap_table": "/api/deals/{deal_id}/cap-table",
    "consents": "/api/deals/{deal_id}/consents",
    "employees": "/api/deals/{deal_id}/employees",
    "material_contracts": "/api/deals/{deal_id}/material-contracts",
    "regulatory": "/api/deals/{deal_id}/regulatory",
    "diligence_findings": "/api/deals/{deal_id}/diligence-findings",
    "notes": "/api/deals/{deal_id}/notes",
}

MUTATION_KEYWORDS = re.compile(
    r"\b(attach|detach|alter|analyze|create|delete|drop|insert|pragma|reindex|"
    r"replace|update|vacuum|load_extension|writable_schema|begin|commit|rollback|savepoint|release)\b",
    re.IGNORECASE,
)


app = Flask(__name__, static_folder=None)


def ensure_data():
    if not DB_PATH.exists():
        import generate_data

        generate_data.main()


def get_conn(read_only=False):
    if read_only:
        uri = f"file:{DB_PATH}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows(query, params=()):
    with get_conn(read_only=True) as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def one(query, params=()):
    with get_conn(read_only=True) as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def table_count(table):
    return one(f"SELECT COUNT(*) AS count FROM {table}")["count"]


def related_links(deal_id):
    return {key: value.format(deal_id=deal_id) for key, value in RELATED_ENDPOINTS.items()}


def deal_or_404(deal_id):
    deal = one("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
    if deal is None:
        abort(404)
    return deal


@app.get("/")
def dashboard():
    counts = {
        table: table_count(table) for table in ["deals", "draft_terms", "consents", "diligence_findings", "documents"]
    }
    target_deals = rows(
        "SELECT deal_id, project_name, transaction_type, client_side, status, playbook_id, policy_id "
        "FROM deals WHERE deal_id IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ORDER BY deal_id",
        (
            "PRJ_ASTER",
            "PRJ_HELIX",
            "PRJ_JUNIPER",
            "PRJ_KEYSTONE",
            "PRJ_LYRA",
            "PRJ_MERIDIAN",
            "PRJ_NIMBUS",
            "PRJ_ORION",
            "PRJ_ROOK",
            "PRJ_VEGA",
        ),
    )
    recent_flags = rows(
        "SELECT deal_id, category, draft_value, staleness_flag FROM draft_terms "
        "WHERE staleness_flag = 'stale' ORDER BY term_id LIMIT 8"
    )
    return render_template_string(
        BASE_TEMPLATE + DASHBOARD_TEMPLATE, counts=counts, target_deals=target_deals, recent_flags=recent_flags
    )


@app.get("/health")
def health():
    try:
        count = table_count("deals")
    except sqlite3.Error:
        return jsonify({"ok": False, "database": "unavailable"}), 500
    return jsonify({"ok": True, "task_group_id": "task_group_020", "deal_count": count})


@app.get("/workspace")
def workspace():
    q = request.args.get("q", "").strip()
    client_side = request.args.get("client_side", "").strip()
    status = request.args.get("status", "").strip()
    clauses = []
    params = []
    if q:
        like = f"%{q}%"
        clauses.append(
            "(deal_id LIKE ? OR project_name LIKE ? OR target_name LIKE ? OR client_name LIKE ? OR counterparty_name LIKE ? OR industry LIKE ?)"
        )
        params.extend([like] * 6)
    if client_side:
        clauses.append("client_side = ?")
        params.append(client_side)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    deals = rows(
        "SELECT deal_id, project_name, transaction_type, client_side, client_name, counterparty_name, "
        "target_name, headline_value, status, playbook_id, policy_id FROM deals "
        f"{where} ORDER BY deal_id LIMIT 120",
        tuple(params),
    )
    return render_template_string(
        BASE_TEMPLATE + WORKSPACE_TEMPLATE, deals=deals, q=q, client_side=client_side, status=status
    )


@app.get("/deals/<deal_id>")
def deal_detail(deal_id):
    deal = deal_or_404(deal_id)
    context = {
        "deal": deal,
        "terms": rows("SELECT * FROM draft_terms WHERE deal_id = ? ORDER BY term_id", (deal_id,)),
        "consents": rows("SELECT * FROM consents WHERE deal_id = ? ORDER BY consent_id", (deal_id,)),
        "benchmarks": rows("SELECT * FROM benchmarks WHERE deal_id = ? ORDER BY benchmark_id", (deal_id,)),
        "notes": rows("SELECT * FROM deal_notes WHERE deal_id = ? ORDER BY note_id", (deal_id,)),
        "links": related_links(deal_id),
    }
    return render_template_string(BASE_TEMPLATE + DEAL_TEMPLATE, **context)


@app.get("/playbooks")
def playbooks_page():
    playbooks = rows(
        "SELECT playbook_id, COUNT(*) AS rule_count FROM playbook_rules GROUP BY playbook_id ORDER BY playbook_id"
    )
    return render_template_string(BASE_TEMPLATE + PLAYBOOKS_TEMPLATE, playbooks=playbooks)


@app.get("/policies")
def policies_page():
    policies = rows(
        "SELECT policy_id, COUNT(*) AS threshold_count FROM policy_thresholds GROUP BY policy_id ORDER BY policy_id"
    )
    return render_template_string(BASE_TEMPLATE + POLICIES_TEMPLATE, policies=policies)


@app.get("/api/deals")
def api_deals():
    q = request.args.get("q", "").strip()
    clauses = []
    params = []
    for field in ["client_side", "status", "playbook_id", "policy_id", "transaction_type"]:
        value = request.args.get(field, "").strip()
        if value:
            clauses.append(f"{field} = ?")
            params.append(value)
    if q:
        like = f"%{q}%"
        clauses.append(
            "(deal_id LIKE ? OR project_name LIKE ? OR target_name LIKE ? OR client_name LIKE ? OR counterparty_name LIKE ? OR strategic_context LIKE ?)"
        )
        params.extend([like] * 6)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    data = rows(f"SELECT * FROM deals {where} ORDER BY deal_id", tuple(params))
    return jsonify({"deals": data, "count": len(data)})


@app.get("/api/deals/<deal_id>")
def api_deal(deal_id):
    deal = deal_or_404(deal_id)
    return jsonify({"deal": deal, "links": related_links(deal_id)})


def list_endpoint(deal_id, table, order_by):
    deal_or_404(deal_id)
    return jsonify({table: rows(f"SELECT * FROM {table} WHERE deal_id = ? ORDER BY {order_by}", (deal_id,))})


@app.get("/api/deals/<deal_id>/terms")
def api_terms(deal_id):
    return list_endpoint(deal_id, "draft_terms", "term_id")


@app.get("/api/deals/<deal_id>/documents")
def api_documents(deal_id):
    return list_endpoint(deal_id, "documents", "document_id")


@app.get("/api/deals/<deal_id>/benchmarks")
def api_benchmarks(deal_id):
    return list_endpoint(deal_id, "benchmarks", "benchmark_id")


@app.get("/api/deals/<deal_id>/risk-estimates")
def api_risk_estimates(deal_id):
    return list_endpoint(deal_id, "risk_estimates", "estimate_id")


@app.get("/api/deals/<deal_id>/cap-table")
def api_cap_table(deal_id):
    return list_endpoint(deal_id, "cap_table", "holder")


@app.get("/api/deals/<deal_id>/consents")
def api_consents(deal_id):
    return list_endpoint(deal_id, "consents", "consent_id")


@app.get("/api/deals/<deal_id>/employees")
def api_employees(deal_id):
    return list_endpoint(deal_id, "employees", "employee_id")


@app.get("/api/deals/<deal_id>/material-contracts")
def api_material_contracts(deal_id):
    return list_endpoint(deal_id, "material_contracts", "contract_id")


@app.get("/api/deals/<deal_id>/regulatory")
def api_regulatory(deal_id):
    deal_or_404(deal_id)
    return jsonify({"regulatory": one("SELECT * FROM regulatory WHERE deal_id = ?", (deal_id,))})


@app.get("/api/deals/<deal_id>/diligence-findings")
def api_diligence_findings(deal_id):
    return list_endpoint(deal_id, "diligence_findings", "finding_id")


@app.get("/api/deals/<deal_id>/notes")
def api_notes(deal_id):
    return list_endpoint(deal_id, "deal_notes", "note_id")


@app.get("/api/playbooks")
def api_playbooks():
    data = rows(
        "SELECT playbook_id, COUNT(*) AS rule_count FROM playbook_rules GROUP BY playbook_id ORDER BY playbook_id"
    )
    return jsonify({"playbooks": data})


@app.get("/api/playbooks/<playbook_id>/rules")
def api_playbook_rules(playbook_id):
    data = rows("SELECT * FROM playbook_rules WHERE playbook_id = ? ORDER BY category", (playbook_id,))
    if not data:
        abort(404)
    return jsonify({"playbook_id": playbook_id, "rules": data})


@app.get("/api/policies")
def api_policies():
    data = rows(
        "SELECT policy_id, COUNT(*) AS threshold_count FROM policy_thresholds GROUP BY policy_id ORDER BY policy_id"
    )
    return jsonify({"policies": data})


@app.get("/api/policies/<policy_id>/thresholds")
def api_policy_thresholds(policy_id):
    data = rows("SELECT * FROM policy_thresholds WHERE policy_id = ? ORDER BY category", (policy_id,))
    if not data:
        abort(404)
    return jsonify({"policy_id": policy_id, "thresholds": data})


@app.get("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"query": q, "deals": [], "terms": [], "documents": [], "notes": []})
    like = f"%{q}%"
    return jsonify(
        {
            "query": q,
            "deals": rows(
                "SELECT deal_id, project_name, transaction_type, client_side, client_name, counterparty_name, target_name, status "
                "FROM deals WHERE deal_id LIKE ? OR project_name LIKE ? OR target_name LIKE ? OR client_name LIKE ? OR counterparty_name LIKE ? "
                "ORDER BY deal_id LIMIT 50",
                (like, like, like, like, like),
            ),
            "terms": rows(
                "SELECT term_id, deal_id, category, draft_value, numeric_value, unit, basis, staleness_flag "
                "FROM draft_terms WHERE category LIKE ? OR draft_value LIKE ? OR counterparty_rationale LIKE ? ORDER BY term_id LIMIT 50",
                (like, like, like),
            ),
            "documents": rows(
                "SELECT document_id, deal_id, document_type, title, summary, version, effective_date "
                "FROM documents WHERE title LIKE ? OR summary LIKE ? ORDER BY document_id LIMIT 50",
                (like, like),
            ),
            "notes": rows(
                "SELECT note_id, deal_id, author, note_date, topic, content, source_document "
                "FROM deal_notes WHERE topic LIKE ? OR content LIKE ? ORDER BY note_id LIMIT 50",
                (like, like),
            ),
        }
    )


@app.post("/api/query")
def api_query():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token")
    sql = payload.get("sql")
    if token != QUERY_TOKEN:
        return jsonify({"error": "invalid token"}), 401
    if not isinstance(sql, str) or not sql.strip():
        return jsonify({"error": "missing sql"}), 400
    clean_sql = strip_sql_comments(sql).strip()
    if ";" in clean_sql:
        return jsonify({"error": "multiple statements are not allowed"}), 400
    if not re.match(r"^(select|with)\b", clean_sql, re.IGNORECASE):
        return jsonify({"error": "only SELECT or WITH statements are allowed"}), 400
    if MUTATION_KEYWORDS.search(clean_sql):
        return jsonify({"error": "statement contains a blocked keyword"}), 400
    try:
        with get_conn(read_only=True) as conn:
            conn.execute("PRAGMA query_only = ON")
            conn.set_authorizer(readonly_authorizer)
            cursor = conn.execute(clean_sql)
            result_rows = cursor.fetchall()
            columns = [item[0] for item in cursor.description or []]
    except sqlite3.Error:
        return jsonify({"error": "query rejected"}), 400
    return jsonify({"columns": columns, "rows": [list(row) for row in result_rows], "row_count": len(result_rows)})


@app.post("/admin/reseed")
def admin_reseed():
    import generate_data

    generate_data.main()
    return jsonify({"ok": True, "database": "reseeded", "seed": generate_data.SEED})


def strip_sql_comments(sql):
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n\r]*", " ", sql)
    return sql


def readonly_authorizer(action, arg1, arg2, dbname, source):
    denied = {
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_PRAGMA,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_UPDATE,
    }
    for name in [
        "SQLITE_CREATE_INDEX",
        "SQLITE_CREATE_TABLE",
        "SQLITE_CREATE_TEMP_INDEX",
        "SQLITE_CREATE_TEMP_TABLE",
        "SQLITE_CREATE_TEMP_TRIGGER",
        "SQLITE_CREATE_TEMP_VIEW",
        "SQLITE_CREATE_TRIGGER",
        "SQLITE_CREATE_VIEW",
        "SQLITE_REINDEX",
        "SQLITE_ANALYZE",
    ]:
        value = getattr(sqlite3, name, None)
        if value is not None:
            denied.add(value)
    if action in denied:
        return sqlite3.SQLITE_DENY
    if action == getattr(sqlite3, "SQLITE_FUNCTION", -1) and str(arg2 or arg1).lower() == "load_extension":
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


if os.environ.get("TASK_ENV_ENABLE_JUDGE") == "1":
    from judge_api import create_judge_blueprint

    app.register_blueprint(create_judge_blueprint())


BASE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>M&A Workbench</title>
  <style>
    :root { --ink: #20242a; --muted: #667085; --line: #d9dee7; --band: #f5f7fa; --accent: #0b6b5f; --warn: #9a4b00; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: #ffffff; }
    header { border-bottom: 1px solid var(--line); background: #fff; position: sticky; top: 0; z-index: 2; }
    nav { max-width: 1180px; margin: 0 auto; padding: 14px 22px; display: flex; gap: 18px; align-items: center; flex-wrap: wrap; }
    nav a { color: var(--accent); text-decoration: none; font-weight: 700; }
    nav .brand { color: var(--ink); font-size: 18px; margin-right: 12px; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px 22px 48px; }
    h1 { font-size: 28px; margin: 0 0 16px; letter-spacing: 0; }
    h2 { font-size: 19px; margin: 28px 0 10px; letter-spacing: 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
    .stat, .panel { border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: #fff; }
    .stat strong { display: block; font-size: 24px; margin-bottom: 4px; }
    .muted { color: var(--muted); }
    form.filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: end; margin: 12px 0 18px; }
    label { display: grid; gap: 4px; font-size: 13px; color: var(--muted); }
    input, select, button { min-height: 36px; border: 1px solid var(--line); border-radius: 6px; padding: 7px 9px; font: inherit; background: #fff; }
    button { background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 700; cursor: pointer; }
    table { width: 100%; border-collapse: collapse; margin: 8px 0 18px; }
    th, td { border-bottom: 1px solid var(--line); text-align: left; padding: 9px 8px; vertical-align: top; font-size: 14px; }
    th { background: var(--band); font-weight: 700; }
    td a { color: var(--accent); font-weight: 700; text-decoration: none; }
    .tag { display: inline-block; border: 1px solid var(--line); border-radius: 999px; padding: 2px 8px; font-size: 12px; color: var(--muted); background: #fff; }
    .warn { color: var(--warn); font-weight: 700; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px; }
    @media (max-width: 720px) { th:nth-child(5), td:nth-child(5), th:nth-child(6), td:nth-child(6) { display: none; } main { padding: 18px 12px 36px; } }
  </style>
</head>
<body>
<header>
  <nav>
    <a class="brand" href="/">M&A Workbench</a>
    <a href="/workspace">Workspace</a>
    <a href="/playbooks">Playbooks</a>
    <a href="/policies">Policies</a>
    <a href="/api/deals">Deals API</a>
  </nav>
</header>
<main>
"""


DASHBOARD_TEMPLATE = """
<h1>Transaction Counsel Dashboard</h1>
<div class="grid">
  {% for label, value in counts.items() %}
  <div class="stat"><strong>{{ value }}</strong><span class="muted">{{ label.replace('_', ' ') }}</span></div>
  {% endfor %}
</div>
<h2>Target Deal Index</h2>
<table>
  <tr><th>Deal</th><th>Project</th><th>Type</th><th>Side</th><th>Status</th><th>Framework</th></tr>
  {% for deal in target_deals %}
  <tr>
    <td><a href="/deals/{{ deal.deal_id }}">{{ deal.deal_id }}</a></td>
    <td>{{ deal.project_name }}</td>
    <td>{{ deal.transaction_type }}</td>
    <td>{{ deal.client_side }}</td>
    <td>{{ deal.status }}</td>
    <td><span class="tag">{{ deal.playbook_id or deal.policy_id }}</span></td>
  </tr>
  {% endfor %}
</table>
<h2>Stale Draft Flags</h2>
<table>
  <tr><th>Deal</th><th>Category</th><th>Draft value</th><th>Flag</th></tr>
  {% for flag in recent_flags %}
  <tr><td><a href="/deals/{{ flag.deal_id }}">{{ flag.deal_id }}</a></td><td>{{ flag.category }}</td><td>{{ flag.draft_value }}</td><td class="warn">{{ flag.staleness_flag }}</td></tr>
  {% endfor %}
</table>
</main></body></html>
"""


WORKSPACE_TEMPLATE = """
<h1>Deal Workspace</h1>
<form class="filters" method="get">
  <label>Search <input name="q" value="{{ q }}" placeholder="project, client, term"></label>
  <label>Side
    <select name="client_side">
      <option value="">Any</option>
      <option value="buyer" {% if client_side == 'buyer' %}selected{% endif %}>buyer</option>
      <option value="seller" {% if client_side == 'seller' %}selected{% endif %}>seller</option>
    </select>
  </label>
  <label>Status <input name="status" value="{{ status }}" placeholder="committee escalation"></label>
  <button type="submit">Apply</button>
</form>
<table>
  <tr><th>Deal</th><th>Project</th><th>Type</th><th>Side</th><th>Client</th><th>Counterparty</th><th>Value</th><th>Status</th><th>Framework</th></tr>
  {% for deal in deals %}
  <tr>
    <td><a href="/deals/{{ deal.deal_id }}">{{ deal.deal_id }}</a></td>
    <td>{{ deal.project_name }}</td>
    <td>{{ deal.transaction_type }}</td>
    <td>{{ deal.client_side }}</td>
    <td>{{ deal.client_name }}</td>
    <td>{{ deal.counterparty_name }}</td>
    <td>{{ "{:,.0f}".format(deal.headline_value or 0) }}</td>
    <td>{{ deal.status }}</td>
    <td>{{ deal.playbook_id or deal.policy_id or "" }}</td>
  </tr>
  {% endfor %}
</table>
</main></body></html>
"""


DEAL_TEMPLATE = """
<h1>{{ deal.project_name }} <span class="tag">{{ deal.deal_id }}</span></h1>
<div class="panel">
  <strong>{{ deal.transaction_type }}</strong> | {{ deal.client_side }} side | {{ deal.client_name }} vs. {{ deal.counterparty_name }}<br>
  <span class="muted">Target:</span> {{ deal.target_name }} | <span class="muted">Value:</span> {{ "{:,.0f}".format(deal.headline_value or 0) }} {{ deal.currency }} | <span class="muted">Status:</span> {{ deal.status }}<br>
  <span class="muted">Strategic context:</span> {{ deal.strategic_context }}
</div>
<h2>Linked APIs</h2>
<p class="mono">{% for name, path in links.items() %}{{ name }}: {{ path }}<br>{% endfor %}</p>
<h2>Draft Terms</h2>
<table><tr><th>Category</th><th>Draft value</th><th>Numeric</th><th>Basis</th><th>Source</th><th>Flag</th></tr>
{% for term in terms %}
<tr><td>{{ term.category }}</td><td>{{ term.draft_value }}</td><td>{{ term.numeric_value }} {{ term.unit or "" }}</td><td>{{ term.basis }}</td><td>{{ term.source_document }} {{ term.clause_ref }}</td><td>{{ term.staleness_flag }}</td></tr>
{% endfor %}</table>
<h2>Consents</h2>
<table><tr><th>Contract</th><th>Counterparty</th><th>Type</th><th>Closing</th><th>Risk</th><th>Amount at risk</th></tr>
{% for consent in consents %}
<tr><td>{{ consent.contract_name }}</td><td>{{ consent.counterparty }}</td><td>{{ consent.consent_type }}</td><td>{{ consent.required_for_closing }}</td><td>{{ consent.risk_rating }}</td><td>{{ "{:,.0f}".format(consent.amount_at_risk or 0) }}</td></tr>
{% endfor %}</table>
<h2>Benchmarks</h2>
<table><tr><th>Category</th><th>Metric</th><th>Median</th><th>Upper quartile</th><th>Precedent</th></tr>
{% for benchmark in benchmarks %}
<tr><td>{{ benchmark.category }}</td><td>{{ benchmark.metric }}</td><td>{{ benchmark.median_value }}</td><td>{{ benchmark.upper_quartile }}</td><td>{{ benchmark.notable_precedent }}</td></tr>
{% endfor %}</table>
<h2>Notes</h2>
<table><tr><th>Date</th><th>Author</th><th>Topic</th><th>Content</th></tr>
{% for note in notes %}
<tr><td>{{ note.note_date }}</td><td>{{ note.author }}</td><td>{{ note.topic }}</td><td>{{ note.content }}</td></tr>
{% endfor %}</table>
</main></body></html>
"""


PLAYBOOKS_TEMPLATE = """
<h1>Playbook Index</h1>
<table><tr><th>Playbook</th><th>Rules</th><th>API</th></tr>
{% for item in playbooks %}
<tr><td>{{ item.playbook_id }}</td><td>{{ item.rule_count }}</td><td class="mono">/api/playbooks/{{ item.playbook_id }}/rules</td></tr>
{% endfor %}</table>
</main></body></html>
"""


POLICIES_TEMPLATE = """
<h1>Policy Index</h1>
<table><tr><th>Policy</th><th>Thresholds</th><th>API</th></tr>
{% for item in policies %}
<tr><td>{{ item.policy_id }}</td><td>{{ item.threshold_count }}</td><td class="mono">/api/policies/{{ item.policy_id }}/thresholds</td></tr>
{% endfor %}</table>
</main></body></html>
"""


if __name__ == "__main__":
    ensure_data()
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    port = int(os.environ.get("TASK_ENV_PORT", "9020"))
    app.run(host=bind, port=port)
