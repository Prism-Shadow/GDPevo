#!/usr/bin/env python3
"""Browser and API service for the Aster Legal Deal Desk environment."""

from __future__ import annotations

import html
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from judge_api import judge_answer_request


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "dealdesk.json"


def ensure_data_file() -> None:
    if DATA_FILE.exists():
        return
    import generate_data

    generate_data.main()


def load_data() -> dict:
    ensure_data_file()
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


DATA = load_data()
DEALS = DATA["deals"]
DOCUMENTS = DATA["documents"]
POLICIES = DATA["policies"]
CLAUSES = DATA["clauses"]
BENCHMARKS = DATA["benchmarks"]
DEALS_BY_ID = {deal["deal_id"]: deal for deal in DEALS}
DOCS_BY_ID = {doc["doc_id"]: doc for doc in DOCUMENTS}
POLICIES_BY_ID = {policy["policy_id"]: policy for policy in POLICIES}


def counts() -> dict:
    return {
        "deals": len(DEALS),
        "documents": len(DOCUMENTS),
        "policies": len(POLICIES),
        "clauses": len(CLAUSES),
        "benchmarks": len(BENCHMARKS),
    }


def esc(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def fmt_money(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        return f"${value:,.0f}"
    return esc(value)


def fmt_percent(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        return f"{value:g}%"
    return esc(value)


def compact_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def badge(value: object) -> str:
    label = esc(value)
    css = "badge"
    lower = str(value).lower()
    if lower == "active":
        css += " active"
    elif lower == "stale":
        css += " stale"
    elif lower in {"template", "policy", "benchmark"}:
        css += " muted"
    return f'<span class="{css}">{label}</span>'


def page(title: str, body: str, query: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} - Aster Legal Deal Desk</title>
  <style>
    :root {{
      --ink: #18202a;
      --muted: #5e6978;
      --line: #d7dde5;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --nav: #27313f;
      --nav2: #384658;
      --link: #0a5f78;
      --good: #1f7a4d;
      --warn: #9a5d00;
      --soft: #eef2f5;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ background: var(--nav); color: #fff; border-bottom: 4px solid var(--nav2); }}
    .topbar {{ max-width: 1320px; margin: 0 auto; padding: 14px 20px; display: flex; gap: 18px; align-items: center; flex-wrap: wrap; }}
    .brand {{ font-size: 18px; font-weight: 700; letter-spacing: 0; }}
    nav {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    nav a {{ color: #fff; text-decoration: none; padding: 6px 9px; border: 1px solid rgba(255,255,255,.24); border-radius: 4px; }}
    nav a:hover {{ background: rgba(255,255,255,.12); }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 20px; }}
    h1 {{ font-size: 25px; margin: 0 0 14px; }}
    h2 {{ font-size: 18px; margin: 22px 0 10px; }}
    h3 {{ font-size: 15px; margin: 16px 0 8px; }}
    a {{ color: var(--link); }}
    .searchbar {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-left: auto; }}
    .searchbar input, input, select {{ border: 1px solid var(--line); border-radius: 4px; padding: 7px 8px; background: #fff; color: var(--ink); min-height: 34px; }}
    button, .button {{ border: 1px solid #144e65; background: #0a5f78; color: #fff; border-radius: 4px; padding: 7px 10px; text-decoration: none; cursor: pointer; min-height: 34px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 14px; margin: 0 0 14px; }}
    .section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 14px; margin: 0 0 14px; }}
    .section h2:first-child, .section h3:first-child {{ margin-top: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; min-width: 0; }}
    .metric {{ background: var(--soft); border: 1px solid var(--line); border-radius: 4px; padding: 10px; min-width: 0; overflow-wrap: break-word; }}
    .metric b {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .toolbar {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 8px 0 14px; }}
    .subgrid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 12px; min-width: 0; }}
    .section-stack {{ display: grid; grid-template-columns: 1fr; gap: 12px; min-width: 0; }}
    .record {{ border: 1px solid var(--line); border-radius: 5px; background: #fff; padding: 10px; min-width: 0; overflow: hidden; }}
    .record h3, .record h4 {{ margin: 0 0 8px; }}
    dl.defs {{ display: grid; grid-template-columns: minmax(150px, 240px) minmax(0, 1fr); gap: 0; margin: 0; border: 1px solid var(--line); border-bottom: 0; background: #fff; min-width: 0; }}
    dl.defs dt, dl.defs dd {{ margin: 0; padding: 7px 9px; border-bottom: 1px solid var(--line); overflow-wrap: break-word; word-break: normal; min-width: 0; }}
    dl.defs dt {{ background: #eef2f5; color: #334052; font-weight: 700; }}
    dl.defs dd {{ background: #fff; }}
    .list-inline {{ display: flex; gap: 5px; flex-wrap: wrap; }}
    .chip {{ display: inline-block; border: 1px solid var(--line); background: #f7f8fa; border-radius: 3px; padding: 2px 6px; font-size: 12px; }}
    details.raw {{ border: 1px solid var(--line); border-radius: 5px; background: #fff; margin-top: 10px; }}
    details.raw summary {{ cursor: pointer; padding: 8px 10px; color: var(--link); font-weight: 700; }}
    details.raw pre {{ margin: 0; border-radius: 0 0 5px 5px; background: #f5f7f9; color: var(--ink); border-top: 1px solid var(--line); }}
    .table-wrap {{ width: 100%; overflow-x: auto; overflow-y: hidden; border: 1px solid var(--line); background: #fff; }}
    table {{ width: max-content; min-width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px 9px; text-align: left; vertical-align: top; overflow-wrap: break-word; word-break: normal; }}
    th {{ background: #e9edf2; color: #283442; font-weight: 700; }}
    tr:hover td {{ background: #f4f7f9; }}
    .badge {{ display: inline-block; border: 1px solid var(--line); border-radius: 3px; padding: 2px 6px; font-size: 12px; background: #fff; color: var(--muted); white-space: nowrap; }}
    .badge.active {{ color: var(--good); border-color: #9fd0ba; background: #edf8f3; }}
    .badge.stale {{ color: var(--warn); border-color: #e3c27b; background: #fff7e6; }}
    .badge.muted {{ color: #57606a; background: #f0f2f4; }}
    pre {{ white-space: pre-wrap; overflow: auto; background: #101820; color: #e8edf2; padding: 12px; border-radius: 4px; font-size: 12px; }}
    .muted {{ color: var(--muted); }}
    .split {{ display: grid; grid-template-columns: minmax(260px, 1fr) minmax(260px, 1fr); gap: 14px; }}
    @media (max-width: 900px) {{ .subgrid {{ grid-template-columns: 1fr; }} dl.defs {{ grid-template-columns: 1fr; }} dl.defs dt {{ border-bottom: 0; }} }}
    @media (max-width: 780px) {{ .split {{ grid-template-columns: 1fr; }} .searchbar {{ width: 100%; }} .searchbar input {{ flex: 1; min-width: 160px; }} }}
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div class="brand">Aster Legal Deal Desk</div>
      <nav>
        <a href="/">Home</a>
        <a href="/deals">Deals</a>
        <a href="/policies">Policies</a>
        <a href="/benchmarks">Benchmarks</a>
        <a href="/clauses/compare">Clause Compare</a>
        <a href="/api/health">API Health</a>
      </nav>
      <form class="searchbar" action="/" method="get">
        <input name="q" value="{esc(query)}" placeholder="Search deals, clauses, docs">
        <button type="submit">Search</button>
      </form>
    </div>
  </header>
  <main>{body}</main>
</body>
</html>"""


def deal_summary(deal: dict) -> dict:
    return {
        "deal_id": deal["deal_id"],
        "codename": deal["codename"],
        "client": deal["client"],
        "client_side": deal["client_side"],
        "structure": deal["structure"],
        "status": deal["status"],
        "target": deal["target"],
        "buyer": deal["buyer"],
        "seller": deal["seller"],
        "policy_id": deal["policy_id"],
        "headline_value": deal["headline_value"],
        "equity_value": deal["equity_value"],
        "industry": deal["industry"],
        "signing_date": deal["signing_date"],
        "closing_deadline": deal["closing_deadline"],
    }


def docs_for_deal(deal_id: str) -> list[dict]:
    return [doc for doc in DOCUMENTS if doc.get("deal_id") == deal_id]


def clauses_for_deal(deal_id: str) -> list[dict]:
    return [clause for clause in CLAUSES if clause["deal_id"] == deal_id]


def benchmark_filter(params: dict[str, list[str]]) -> list[dict]:
    records = BENCHMARKS
    topic = params.get("topic", [""])[0].strip().lower()
    industry = params.get("industry", [""])[0].strip().lower()
    year = params.get("year", [""])[0].strip()
    q = params.get("q", [""])[0].strip().lower()
    if topic:
        records = [row for row in records if topic in row["topic"].lower()]
    if industry:
        records = [row for row in records if industry in row["industry"].lower()]
    if year:
        records = [row for row in records if str(row["year"]) == year]
    if q:
        records = [row for row in records if q in json.dumps(row, sort_keys=True).lower()]
    return records


def search_records(query: str, limit: int = 50) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    candidates: list[tuple[str, str, str, str, dict]] = []
    for deal in DEALS:
        candidates.append(("deal", deal["deal_id"], deal["codename"], f"/deals/{quote(deal['deal_id'])}", deal))
    for doc in DOCUMENTS:
        candidates.append(("document", doc["doc_id"], doc["title"], f"/documents/{quote(doc['doc_id'])}", doc))
    for policy in POLICIES:
        candidates.append(
            ("policy", policy["policy_id"], policy["title"], f"/policies/{quote(policy['policy_id'])}", policy)
        )
    for clause in CLAUSES:
        candidates.append(
            (
                "clause",
                clause["clause_id"],
                f"{clause['deal_id']} {clause['topic']}",
                f"/clauses/compare?deal_id={quote(clause['deal_id'])}",
                clause,
            )
        )
    for bench in BENCHMARKS:
        candidates.append(
            (
                "benchmark",
                bench["benchmark_id"],
                f"{bench['topic']} / {bench['industry']} / {bench['year']}",
                f"/benchmarks?q={quote(query)}",
                bench,
            )
        )

    results = []
    for kind, ident, title, url, record in candidates:
        text = json.dumps(record, sort_keys=True)
        lower = text.lower()
        if q not in lower and q not in ident.lower() and q not in title.lower():
            continue
        idx = lower.find(q)
        if idx >= 0:
            start = max(0, idx - 70)
            end = min(len(text), idx + 180)
            snippet = text[start:end]
        else:
            snippet = title
        results.append({"type": kind, "id": ident, "title": title, "url": url, "snippet": snippet})
    return results[:limit]


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def titleize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def value_html(value: object) -> str:
    if isinstance(value, bool):
        return badge("true" if value else "false")
    if value is None:
        return '<span class="muted">n/a</span>'
    if isinstance(value, (int, float)):
        return esc(value)
    if isinstance(value, list):
        if not value:
            return '<span class="muted">None</span>'
        if all(not isinstance(item, (dict, list)) for item in value):
            return (
                '<span class="list-inline">'
                + "".join(f'<span class="chip">{esc(item)}</span>' for item in value)
                + "</span>"
            )
        return render_list(value)
    if isinstance(value, dict):
        return definition_list(value)
    return esc(value)


def definition_list(record: dict) -> str:
    items = []
    for key, value in record.items():
        items.append(f"<dt>{esc(titleize(str(key)))}</dt><dd>{value_html(value)}</dd>")
    return '<dl class="defs">' + "".join(items) + "</dl>"


def render_list(items: list) -> str:
    if not items:
        return '<span class="muted">None</span>'
    if all(isinstance(item, dict) for item in items):
        keys: list[str] = []
        for item in items:
            for key in item:
                if key not in keys:
                    keys.append(key)
        rows = [[value_html(item.get(key)) for key in keys] for item in items]
        return table([titleize(str(key)) for key in keys], rows)
    return "".join(f'<div class="record">{value_html(item)}</div>' for item in items)


def raw_json_details(title: str, value: object) -> str:
    return f'<details class="raw"><summary>{esc(title)}</summary><pre>{esc(compact_json(value))}</pre></details>'


def data_section(title: str, value: object, raw_title: str | None = None) -> str:
    body = value_html(value)
    raw = raw_json_details(raw_title or f"Raw {title} JSON", value)
    return f'<section class="section"><h2>{esc(title)}</h2>{body}{raw}</section>'


def grouped_data_section(
    title: str, groups: dict[str, object], raw_value: object | None = None, layout: str = "grid"
) -> str:
    cards = []
    for key, value in groups.items():
        cards.append(f'<div class="record"><h3>{esc(titleize(str(key)))}</h3>{value_html(value)}</div>')
    raw = raw_json_details(f"Raw {title} JSON", raw_value if raw_value is not None else groups)
    container_class = "section-stack" if layout == "stack" else "subgrid"
    return f'<section class="section"><h2>{esc(title)}</h2><div class="{container_class}">{"".join(cards)}</div>{raw}</section>'


def home_page(params: dict[str, list[str]]) -> str:
    q = params.get("q", [""])[0]
    ct = counts()
    search_html = ""
    if q.strip():
        rows = [
            [
                badge(result["type"]),
                f'<a href="{esc(result["url"])}">{esc(result["id"])}</a>',
                esc(result["title"]),
                f'<span class="muted">{esc(result["snippet"])}</span>',
            ]
            for result in search_records(q)
        ]
        search_html = f"<h2>Search Results</h2>{table(['Type', 'ID', 'Title', 'Snippet'], rows) if rows else '<p>No matching records.</p>'}"
    recent_rows = [
        [
            f'<a href="/deals/{quote(deal["deal_id"])}">{esc(deal["deal_id"])}</a>',
            esc(deal["codename"]),
            esc(deal["client"]),
            badge(deal["client_side"]),
            esc(deal["structure"]),
            fmt_money(deal["headline_value"]),
        ]
        for deal in DEALS[:10]
    ]
    body = f"""
<h1>Deal Desk Workspace</h1>
<div class="grid">
  <div class="metric"><b>Deals</b>{ct["deals"]}</div>
  <div class="metric"><b>Documents</b>{ct["documents"]}</div>
  <div class="metric"><b>Policies</b>{ct["policies"]}</div>
  <div class="metric"><b>Clauses</b>{ct["clauses"]}</div>
  <div class="metric"><b>Benchmarks</b>{ct["benchmarks"]}</div>
</div>
{search_html}
<h2>Active Matter Index</h2>
{table(["Deal ID", "Codename", "Client", "Side", "Structure", "Headline Value"], recent_rows)}
"""
    return page("Home", body, q)


def deals_page(params: dict[str, list[str]]) -> str:
    q = params.get("q", [""])[0].strip().lower()
    side = params.get("side", [""])[0]
    structure = params.get("structure", [""])[0]
    rows_deals = DEALS
    if q:
        rows_deals = [deal for deal in rows_deals if q in json.dumps(deal, sort_keys=True).lower()]
    if side:
        rows_deals = [deal for deal in rows_deals if deal["client_side"] == side]
    if structure:
        rows_deals = [deal for deal in rows_deals if deal["structure"] == structure]
    rows = [
        [
            f'<a href="/deals/{quote(deal["deal_id"])}">{esc(deal["deal_id"])}</a>',
            esc(deal["codename"]),
            esc(deal["client"]),
            badge(deal["client_side"]),
            esc(deal["structure"]),
            esc(deal["status"]),
            esc(deal["target"]),
            fmt_money(deal["headline_value"]),
        ]
        for deal in rows_deals
    ]
    form = f"""
<form class="panel" method="get" action="/deals">
  <input name="q" value="{esc(params.get("q", [""])[0])}" placeholder="Filter text">
  <select name="side">
    <option value="">Any side</option>
    <option value="BUYER" {"selected" if side == "BUYER" else ""}>BUYER</option>
    <option value="SELLER" {"selected" if side == "SELLER" else ""}>SELLER</option>
  </select>
  <select name="structure">
    <option value="">Any structure</option>
    {"".join(f'<option value="{esc(s)}" {"selected" if structure == s else ""}>{esc(s)}</option>' for s in sorted({d["structure"] for d in DEALS}))}
  </select>
  <button type="submit">Apply</button>
</form>
"""
    body = f"<h1>Deal Index</h1>{form}{table(['Deal ID', 'Codename', 'Client', 'Side', 'Structure', 'Status', 'Target', 'Headline'], rows)}"
    return page("Deals", body)


def linked_doc_table(documents: list[dict]) -> str:
    rows = [
        [
            f'<a href="/documents/{quote(doc["doc_id"])}">{esc(doc["doc_id"])}</a>',
            esc(doc["title"]),
            esc(doc["doc_type"]),
            badge(doc["version_status"]),
            esc(doc["effective_date"]),
        ]
        for doc in documents
    ]
    return table(["Document ID", "Title", "Type", "Status", "Effective Date"], rows)


def deal_page(deal_id: str) -> str:
    deal = DEALS_BY_ID.get(deal_id)
    if not deal:
        return page("Deal Not Found", f"<h1>Deal not found</h1><p>{esc(deal_id)}</p>")
    docs = docs_for_deal(deal_id)
    clauses = clauses_for_deal(deal_id)
    active_docs = [doc for doc in docs if doc["version_status"] == "ACTIVE"]
    other_docs = [doc for doc in docs if doc["version_status"] != "ACTIVE"]
    active_clause_rows = [
        [
            esc(clause["clause_code"]),
            esc(clause["topic"]),
            badge(clause["version_status"]),
            esc(clause["draft_value"]),
            esc(clause["playbook_value"]),
            esc(clause["risk_hint"]),
        ]
        for clause in clauses
    ]
    workbench_links = f"""
<div class="toolbar">
  <a class="button" href="/clauses/compare?deal_id={quote(deal_id)}">Clause Compare</a>
  <a class="button" href="/api/deals/{quote(deal_id)}">Deal API</a>
  <a class="button" href="/benchmarks?industry={quote(deal["industry"])}">Industry Benchmarks</a>
  <a class="button" href="/policies/{quote(deal["policy_id"])}">Client Policy</a>
</div>
"""
    deal_fact_sections = (
        grouped_data_section("Economics", deal["economics"], deal["economics"])
        + grouped_data_section("Parties", deal["parties"], deal["parties"], layout="stack")
        + grouped_data_section("Schedules", deal["schedules"], deal["schedules"], layout="stack")
        + grouped_data_section(
            "Client Positions and Negotiation Context",
            {
                "client_positions": deal["client_positions"],
                "negotiation_context": deal["negotiation_context"],
            },
            {
                "client_positions": deal["client_positions"],
                "negotiation_context": deal["negotiation_context"],
            },
            layout="stack",
        )
        + data_section("Current Draft Terms", deal["draft_terms"], "Raw Draft Terms JSON")
    )
    body = f"""
<h1>{esc(deal["codename"])} <span class="muted">{esc(deal_id)}</span></h1>
{workbench_links}
<div class="grid">
  <div class="metric"><b>Client</b>{esc(deal["client"])}</div>
  <div class="metric"><b>Side</b>{badge(deal["client_side"])}</div>
  <div class="metric"><b>Structure</b>{esc(deal["structure"])}</div>
  <div class="metric"><b>Status</b>{esc(deal["status"])}</div>
  <div class="metric"><b>Target</b>{esc(deal["target"])}</div>
  <div class="metric"><b>Headline</b>{fmt_money(deal["headline_value"])}</div>
  <div class="metric"><b>Equity</b>{fmt_money(deal["equity_value"])}</div>
  <div class="metric"><b>Policy</b><a href="/policies/{quote(deal["policy_id"])}">{esc(deal["policy_id"])}</a></div>
</div>
{deal_fact_sections}
<h2>Active Documents</h2>
{linked_doc_table(active_docs)}
<h2>Stale, Template, and Other Records</h2>
{linked_doc_table(other_docs)}
<h2>Clause Comparison</h2>
{table(["Code", "Topic", "Status", "Draft Value", "Playbook Value", "Review Note"], active_clause_rows)}
<h2>Relevant Benchmarks</h2>
<p><a href="/benchmarks?industry={quote(deal["industry"])}">Benchmarks for {esc(deal["industry"])}</a></p>
{raw_json_details("Raw Deal JSON", deal)}
"""
    return page(deal["codename"], body)


def document_page(doc_id: str) -> str:
    doc = DOCS_BY_ID.get(doc_id)
    if not doc:
        return page("Document Not Found", f"<h1>Document not found</h1><p>{esc(doc_id)}</p>")
    section_html = "".join(
        f'<section class="section"><h2>{esc(sec["heading"])}</h2><p>{esc(sec["text"])}</p></section>'
        for sec in doc["sections"]
    )
    related_links = []
    for related in doc.get("related_ids", []):
        if related in DEALS_BY_ID:
            related_links.append(f'<a href="/deals/{quote(related)}">{esc(related)}</a>')
        elif related in POLICIES_BY_ID:
            related_links.append(f'<a href="/policies/{quote(related)}">{esc(related)}</a>')
        elif related in DOCS_BY_ID:
            related_links.append(f'<a href="/documents/{quote(related)}">{esc(related)}</a>')
        else:
            related_links.append(esc(related))
    deal_link = ""
    if doc.get("deal_id"):
        deal_link = (
            f'<div class="metric"><b>Deal</b><a href="/deals/{quote(doc["deal_id"])}">{esc(doc["deal_id"])}</a></div>'
        )
    body = f"""
<h1>{esc(doc["title"])}</h1>
<div class="toolbar">
  <a class="button" href="/api/documents/{quote(doc_id)}">Document API</a>
  {f'<a class="button" href="/deals/{quote(doc["deal_id"])}">Open Deal</a>' if doc.get("deal_id") else ""}
</div>
<div class="grid">
  <div class="metric"><b>Document ID</b>{esc(doc["doc_id"])}</div>
  {deal_link}
  <div class="metric"><b>Type</b>{esc(doc["doc_type"])}</div>
  <div class="metric"><b>Status</b>{badge(doc["version_status"])}</div>
  <div class="metric"><b>Effective Date</b>{esc(doc["effective_date"])}</div>
  <div class="metric"><b>Related</b>{", ".join(related_links)}</div>
</div>
{section_html}
{raw_json_details("Raw Document JSON", doc)}
"""
    return page(doc["title"], body)


def policies_page() -> str:
    rows = [
        [
            f'<a href="/policies/{quote(policy["policy_id"])}">{esc(policy["policy_id"])}</a>',
            esc(policy["title"]),
            esc(policy["client"]),
            esc(policy["policy_type"]),
            esc(policy["version"]),
            esc(policy["effective_date"]),
            str(len(policy["rules"])),
        ]
        for policy in POLICIES
    ]
    return page(
        "Policies",
        f"<h1>Policy Directory</h1>{table(['Policy ID', 'Title', 'Client', 'Type', 'Version', 'Effective Date', 'Rules'], rows)}",
    )


def policy_page(policy_id: str) -> str:
    policy = POLICIES_BY_ID.get(policy_id)
    if not policy:
        return page("Policy Not Found", f"<h1>Policy not found</h1><p>{esc(policy_id)}</p>")
    rules = [
        [
            esc(item["rule_id"]),
            esc(item["topic"]),
            esc(item["preferred"]),
            esc(item["fallback_position"]),
            esc(item["threshold"]),
            esc(item["approval_category"]),
            esc("; ".join(item["escalation_triggers"])),
        ]
        for item in policy["rules"]
    ]
    linked_deals = [deal for deal in DEALS if deal["policy_id"] == policy_id]
    linked_rows = [
        [
            f'<a href="/deals/{quote(deal["deal_id"])}">{esc(deal["deal_id"])}</a>',
            esc(deal["codename"]),
            esc(deal["client_side"]),
            esc(deal["structure"]),
            esc(deal["status"]),
        ]
        for deal in linked_deals
    ]
    metadata = {
        "policy_id": policy["policy_id"],
        "client": policy["client"],
        "policy_type": policy["policy_type"],
        "version": policy["version"],
        "effective_date": policy["effective_date"],
    }
    body = f"""
<h1>{esc(policy["title"])}</h1>
<div class="toolbar">
  <a class="button" href="/api/policies/{quote(policy_id)}">Policy API</a>
  <a class="button" href="/deals?q={quote(policy["client"])}">Deals for Client</a>
</div>
<section class="section"><h2>Policy Metadata</h2>{definition_list(metadata)}</section>
<section class="section"><h2>Rules</h2>{table(["Rule ID", "Topic", "Preferred", "Fallback", "Threshold", "Approval", "Triggers"], rules)}</section>
<section class="section"><h2>Linked Deals</h2>{table(["Deal ID", "Codename", "Side", "Structure", "Status"], linked_rows)}</section>
{raw_json_details("Raw Policy JSON", policy)}
"""
    return page(policy["title"], body)


def benchmarks_page(params: dict[str, list[str]]) -> str:
    records = benchmark_filter(params)
    topic = params.get("topic", [""])[0]
    industry = params.get("industry", [""])[0]
    year = params.get("year", [""])[0]
    q = params.get("q", [""])[0]
    form = f"""
<form class="panel" method="get" action="/benchmarks">
  <input name="topic" value="{esc(topic)}" placeholder="Topic">
  <input name="industry" value="{esc(industry)}" placeholder="Industry">
  <input name="year" value="{esc(year)}" placeholder="Year">
  <input name="q" value="{esc(q)}" placeholder="Search text">
  <button type="submit">Filter</button>
  <a class="button" href="/benchmarks">Clear</a>
</form>
"""
    rows = [
        [
            esc(row["benchmark_id"]),
            esc(row["topic"]),
            esc(row["industry"]),
            esc(row["year"]),
            esc(row["sample_size"]),
            fmt_percent(row.get("median_percent")),
            fmt_percent(row.get("mean_percent")),
            esc(row.get("count_above_threshold")),
            esc(row.get("range_low")),
            esc(row.get("range_high")),
            esc(row.get("definition")),
            esc(row.get("notes")),
        ]
        for row in records
    ]
    body = f"""
<h1>Benchmark Directory</h1>
<div class="toolbar"><a class="button" href="/api/benchmarks">Benchmarks API</a></div>
{form}
<p class="muted">Filtered records: {len(records)}</p>
{table(["Benchmark ID", "Topic", "Industry", "Year", "N", "Median %", "Mean %", "Above Threshold", "Low", "High", "Definition", "Notes"], rows)}
{raw_json_details("Raw Filtered Benchmarks JSON", records)}
"""
    return page("Benchmarks", body)


def clause_compare_page(params: dict[str, list[str]]) -> str:
    deal_id = params.get("deal_id", [""])[0].strip()
    if not deal_id:
        rows = [
            [
                f'<a href="/clauses/compare?deal_id={quote(deal["deal_id"])}">{esc(deal["deal_id"])}</a>',
                esc(deal["codename"]),
                esc(deal["client"]),
                esc(deal["structure"]),
                esc(deal["status"]),
            ]
            for deal in DEALS
        ]
        return page(
            "Clause Compare",
            f"<h1>Clause Compare</h1><p>Select a deal to compare draft terms against applicable policy positions.</p>{table(['Deal ID', 'Codename', 'Client', 'Structure', 'Status'], rows)}",
        )
    deal = DEALS_BY_ID.get(deal_id)
    if not deal:
        return page("Clause Compare", f"<h1>Deal not found</h1><p>{esc(deal_id)}</p>")
    policy = POLICIES_BY_ID.get(deal["policy_id"])
    clauses = clauses_for_deal(deal_id)
    rows = [
        [
            esc(clause["clause_id"]),
            esc(clause["clause_code"]),
            esc(clause["topic"]),
            badge(clause["version_status"]),
            esc(clause["draft_value"]),
            esc(clause["playbook_value"]),
            esc(clause["policy_threshold"]),
            esc(clause["calculation_base"]),
            esc(clause["risk_hint"]),
            f'<a href="/documents/{quote(clause["source_doc_id"])}">{esc(clause["source_doc_id"])}</a>',
        ]
        for clause in clauses
    ]
    body = f"""
<h1>Clause Compare: <a href="/deals/{quote(deal_id)}">{esc(deal["codename"])}</a></h1>
<div class="toolbar">
  <a class="button" href="/api/clauses?deal_id={quote(deal_id)}">Clauses API</a>
  <a class="button" href="/deals/{quote(deal_id)}">Deal Detail</a>
</div>
<div class="grid">
  <div class="metric"><b>Deal ID</b>{esc(deal_id)}</div>
  <div class="metric"><b>Client Side</b>{badge(deal["client_side"])}</div>
  <div class="metric"><b>Policy</b><a href="/policies/{quote(deal["policy_id"])}">{esc(deal["policy_id"])}</a></div>
  <div class="metric"><b>Policy Title</b>{esc(policy["title"] if policy else "")}</div>
</div>
{table(["Clause ID", "Code", "Topic", "Status", "Draft Value", "Playbook Value", "Threshold", "Base", "Review Note", "Source"], rows)}
{raw_json_details("Raw Clause JSON", clauses)}
"""
    return page("Clause Compare", body)


def filtered_deals(params: dict[str, list[str]]) -> list[dict]:
    rows = DEALS
    q = params.get("q", [""])[0].strip().lower()
    if q:
        rows = [deal for deal in rows if q in json.dumps(deal, sort_keys=True).lower()]
    for param, field in [
        ("client_side", "client_side"),
        ("structure", "structure"),
        ("industry", "industry"),
        ("status", "status"),
        ("client", "client"),
    ]:
        value = params.get(param, [""])[0].strip().lower()
        if value:
            rows = [deal for deal in rows if value in str(deal.get(field, "")).lower()]
    return rows


class DealDeskHandler(BaseHTTPRequestHandler):
    server_version = "AsterDealDesk/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}\n")

    def send_json(self, payload: object, status: int = 200) -> None:
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def send_html(self, raw: str, status: int = 200) -> None:
        data = raw.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def not_found(self) -> None:
        self.send_json({"error": "not_found"}, status=404)

    def do_POST(self) -> None:
        if urlparse(self.path).path.rstrip("/") != "/api/judge":
            self.not_found()
            return
        if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
            self.not_found()
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.send_json(payload, status=status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        params = parse_qs(parsed.query)
        if path.startswith("/api/"):
            self.handle_api(path, params)
            return
        if path == "/":
            self.send_html(home_page(params))
            return
        if path == "/deals":
            self.send_html(deals_page(params))
            return
        if path.startswith("/deals/"):
            self.send_html(deal_page(unquote(path.removeprefix("/deals/"))))
            return
        if path.startswith("/documents/"):
            self.send_html(document_page(unquote(path.removeprefix("/documents/"))))
            return
        if path == "/policies":
            self.send_html(policies_page())
            return
        if path.startswith("/policies/"):
            self.send_html(policy_page(unquote(path.removeprefix("/policies/"))))
            return
        if path == "/benchmarks":
            self.send_html(benchmarks_page(params))
            return
        if path == "/clauses/compare":
            self.send_html(clause_compare_page(params))
            return
        self.send_html(page("Not Found", "<h1>Not found</h1>"), status=404)

    def handle_api(self, path: str, params: dict[str, list[str]]) -> None:
        if path == "/api/health":
            self.send_json(
                {
                    "status": "ok",
                    "system": DATA["metadata"]["system"],
                    "seed": DATA["metadata"]["seed"],
                    "counts": counts(),
                }
            )
            return
        if path == "/api/deals":
            self.send_json(
                {
                    "deals": [deal_summary(deal) for deal in filtered_deals(params)],
                    "count": len(filtered_deals(params)),
                }
            )
            return
        if path.startswith("/api/deals/"):
            deal_id = unquote(path.removeprefix("/api/deals/"))
            deal = DEALS_BY_ID.get(deal_id)
            if not deal:
                self.not_found()
                return
            clause_topics = {clause["topic"] for clause in clauses_for_deal(deal_id)}
            related_benchmarks = [
                row
                for row in BENCHMARKS
                if row["industry"].lower() in {deal["industry"].lower(), "middle market", "public company m&a"}
                or row["topic"] in clause_topics
            ][:25]
            self.send_json(
                {
                    "deal": deal,
                    "documents": docs_for_deal(deal_id),
                    "policy": POLICIES_BY_ID.get(deal["policy_id"]),
                    "clauses": clauses_for_deal(deal_id),
                    "benchmarks": related_benchmarks,
                }
            )
            return
        if path.startswith("/api/documents/"):
            doc_id = unquote(path.removeprefix("/api/documents/"))
            doc = DOCS_BY_ID.get(doc_id)
            if not doc:
                self.not_found()
                return
            self.send_json({"document": doc})
            return
        if path == "/api/policies":
            self.send_json({"policies": POLICIES, "count": len(POLICIES)})
            return
        if path.startswith("/api/policies/"):
            policy_id = unquote(path.removeprefix("/api/policies/"))
            policy = POLICIES_BY_ID.get(policy_id)
            if not policy:
                self.not_found()
                return
            self.send_json(
                {
                    "policy": policy,
                    "linked_deals": [deal_summary(deal) for deal in DEALS if deal["policy_id"] == policy_id],
                }
            )
            return
        if path == "/api/clauses":
            deal_id = params.get("deal_id", [""])[0].strip()
            status = params.get("status", [""])[0].strip().upper()
            records = CLAUSES
            if deal_id:
                records = [clause for clause in records if clause["deal_id"] == deal_id]
            if status:
                records = [clause for clause in records if clause["version_status"] == status]
            self.send_json({"clauses": records, "count": len(records)})
            return
        if path == "/api/benchmarks":
            records = benchmark_filter(params)
            self.send_json({"benchmarks": records, "count": len(records)})
            return
        if path == "/api/search":
            q = params.get("q", [""])[0]
            self.send_json({"query": q, "results": search_records(q), "count": len(search_records(q))})
            return
        self.not_found()


def main() -> None:
    port = int(os.environ.get("TASK_ENV_PORT", os.environ.get("PORT", "9020")))
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    host = os.environ.get("TASK_ENV_BIND", os.environ.get("TASK_ENV_HOST", "0.0.0.0"))
    httpd = ThreadingHTTPServer((host, port), DealDeskHandler)
    print(f"Aster Legal Deal Desk running at http://{host}:{port}", flush=True)
    print("Public pages: /, /deals, /policies, /benchmarks, /clauses/compare", flush=True)
    print(
        "API: /api/health, /api/deals, /api/documents/<doc_id>, /api/policies, /api/clauses, /api/benchmarks, /api/search?q=<query>",
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
