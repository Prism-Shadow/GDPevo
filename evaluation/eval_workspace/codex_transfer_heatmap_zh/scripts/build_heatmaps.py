#!/usr/bin/env python3
"""Build 3x3 transfer heatmap data and an HTML render page."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "heatmap_scope.json"
CELL_ROOT = ROOT / "report" / "cells"
REPORT_JSON = ROOT / "report" / "matrix.json"
REPORT_YAML = ROOT / "report" / "matrix.yaml"
HEATMAP_DATA_DIR = ROOT / "heatmaps" / "data"
HEATMAP_HTML = ROOT / "heatmaps" / "index.html"


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def population_std(values: list[float]) -> float:
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / len(values))


def as_float_list(values) -> list[float]:
    if values is None:
        return []
    if isinstance(values, dict):
        return [float(values[key]) for key in sorted(values)]
    return [float(value) for value in values]


def extract_scores(task_record: dict) -> list[float]:
    if "scores" in task_record:
        return as_float_list(task_record["scores"])
    if "scores_by_skill" in task_record:
        return as_float_list(task_record["scores_by_skill"])
    if "attempts" in task_record:
        return [float(item["score"]) for item in task_record["attempts"]]
    return []


def compute_cell(cell_path: Path) -> dict:
    with cell_path.open("r", encoding="utf-8") as handle:
        record = yaml.safe_load(handle)
    if not isinstance(record, dict):
        record = {}

    task_rows = {}
    task_accs: list[float] = []
    task_stds: list[float] = []

    for task_id, task_record in sorted((record.get("tasks") or {}).items()):
        scores = extract_scores(task_record or {})
        if len(scores) != 3:
            raise ValueError(f"{cell_path}: {task_id} must have exactly 3 scores")
        acc = mean(scores)
        std = population_std(scores)
        task_rows[task_id] = {
            "scores": scores,
            "acc_at_3": acc,
            "std_at_3": std,
        }
        task_accs.append(acc)
        task_stds.append(std)

    if not task_accs:
        if "cell_acc_at_3" not in record:
            raise ValueError(f"{cell_path}: no task scores and no cell_acc_at_3")
        cell_acc = float(record["cell_acc_at_3"])
        cell_std = None if record.get("cell_std_at_3") is None else float(record["cell_std_at_3"])
    else:
        cell_acc = mean(task_accs)
        cell_std = mean(task_stds)

    return {
        "path": str(cell_path.relative_to(ROOT)),
        "cell_acc_at_3": cell_acc,
        "cell_std_at_3": cell_std,
        "tasks": task_rows,
        "notes": record.get("notes") or [],
        "excluded_attempts": record.get("excluded_attempts") or [],
    }


def pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 100:.2f}%"


def write_csv(mode: str, task_groups: list[dict], mode_data: dict) -> None:
    path = HEATMAP_DATA_DIR / f"{mode}_matrix.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source\\target", *[item["label"] for item in task_groups]])
        for source, row in zip(task_groups, mode_data["matrix"]):
            cells = []
            for target, value in zip(task_groups, row):
                cell_key = f"{source['id']}__to__{target['id']}"
                status = mode_data["cells"][cell_key]["status"]
                cells.append("not_run" if status == "not_required" else pct(value))
            writer.writerow([source["label"], *cells])


def build_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GDPevo Codex Skill Transfer Heatmaps</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --panel: #ffffff;
      --ink: #101828;
      --muted: #667085;
      --line: #d9e0ea;
      --green: #08745b;
      --green-soft: #dcefe9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: 1440px;
      margin: 0 auto;
      padding: 56px 64px 72px;
    }}
    .eyebrow {{
      color: var(--green);
      font-size: 15px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 10px 0 12px;
      font-size: 44px;
      line-height: 1.08;
      letter-spacing: 0;
    }}
    .lead {{
      max-width: 1100px;
      margin: 0 0 28px;
      color: #475467;
      font-size: 20px;
      line-height: 1.65;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 28px;
      align-items: start;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 12px 32px rgba(16, 24, 40, 0.08);
      overflow: hidden;
    }}
    .panel header {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      padding: 24px 26px 18px;
      border-bottom: 1px solid var(--line);
    }}
    h2 {{
      margin: 0;
      font-size: 28px;
      line-height: 1.15;
    }}
    .meta {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
      text-align: right;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      border-right: 1px solid var(--line);
      text-align: center;
      vertical-align: middle;
    }}
    tr:last-child th, tr:last-child td {{ border-bottom: 0; }}
    th:last-child, td:last-child {{ border-right: 0; }}
    thead th {{
      height: 76px;
      color: #344054;
      background: #f8fafc;
      font-size: 15px;
      font-weight: 800;
    }}
    tbody th {{
      width: 126px;
      background: #f8fafc;
      color: #344054;
      font-size: 15px;
      font-weight: 800;
    }}
    td {{
      height: 136px;
      color: #06281f;
      font-size: 30px;
      font-weight: 850;
    }}
    td small {{
      display: block;
      margin-top: 8px;
      color: rgba(6, 40, 31, .72);
      font-size: 13px;
      font-weight: 750;
    }}
    .diag {{
      outline: 4px solid rgba(8, 116, 91, .22);
      outline-offset: -4px;
    }}
    .missing {{
      background: #f1f4f8;
      color: #98a2b3;
      font-size: 20px;
      font-weight: 800;
    }}
    .not-required {{
      background: repeating-linear-gradient(
        -45deg,
        #f8fafc,
        #f8fafc 10px,
        #eef2f7 10px,
        #eef2f7 20px
      );
      color: #667085;
      font-size: 19px;
      font-weight: 850;
    }}
    .legend {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 18px 26px 22px;
      color: var(--muted);
      font-size: 14px;
      border-top: 1px solid var(--line);
    }}
    .bar {{
      flex: 1;
      height: 12px;
      border-radius: 999px;
      background: linear-gradient(90deg, #edf4f1, #b8ded2, #64b99e, #08745b);
    }}
  </style>
</head>
<body>
<main>
  <div class="eyebrow">GDPevo transfer analysis</div>
  <h1>Codex skill 跨任务迁移热力图</h1>
  <p class="lead">行表示既有 skill 的来源 task group，列表示测试目标 task group。每个单元格的 @3 来自同一个 source 的 3 个既有独立 skill；颜色和值均为 cell-level acc@3。</p>
  <section id="heatmaps" class="grid"></section>
</main>
<script>
const payload = {data_json};
const root = document.getElementById("heatmaps");
const labels = payload.task_groups.map(item => item.label);
const ids = payload.task_groups.map(item => item.id);
const allValues = Object.values(payload.modes)
  .flatMap(mode => mode.matrix.flat())
  .filter(value => value !== null && value !== undefined);
const min = allValues.length ? Math.min(...allValues) : 0;
const max = allValues.length ? Math.max(...allValues) : 1;
function color(value) {{
  if (value === null || value === undefined) return "";
  const t = max === min ? 0.65 : Math.max(0, Math.min(1, (value - min) / (max - min)));
  const light = 95 - t * 48;
  const sat = 38 + t * 24;
  return `hsl(162  ${{sat}}% ${{light}}%)`;
}}
function fmt(value) {{
  return value === null || value === undefined ? "n/a" : `${{(value * 100).toFixed(2)}}%`;
}}
function cellText(status, value) {{
  if (status === "not_required") return "不跑";
  if (status === "missing") return "缺失";
  return fmt(value);
}}
function renderCell(modeData, rowIndex, colIndex, value) {{
  const cellKey = `${{ids[rowIndex]}}__to__${{ids[colIndex]}}`;
  const status = modeData.cells[cellKey].status;
  const cls = status === "not_required" ? "not-required" : (status === "missing" ? "missing" : "");
  const style = status === "ok" ? `background:${{color(value)}}` : "";
  const std = modeData.std_matrix[rowIndex][colIndex];
  return `<td class="${{cls}} ${{rowIndex === colIndex ? "diag" : ""}}" style="${{style}}">
    ${{cellText(status, value)}}
    ${{std === null ? "" : `<small>std@3 ${{fmt(std)}}</small>`}}
  </td>`;
}}
for (const mode of payload.modes_order) {{
  const modeData = payload.modes[mode];
  const panel = document.createElement("article");
  panel.className = "panel";
  const rows = modeData.matrix.map((row, rowIndex) => `
    <tr>
      <th>${{labels[rowIndex]}}<br><span style="font-weight:650;color:#667085">${{ids[rowIndex].replace("task_group_", "TG")}}</span></th>
      ${{row.map((value, colIndex) => renderCell(modeData, rowIndex, colIndex, value)).join("")}}
    </tr>`).join("");
  panel.innerHTML = `
    <header>
      <div>
        <h2>${{mode}}</h2>
      </div>
      <div class="meta">Harness: Codex<br>Model: ${{payload.model}}, ${{payload.reasoning_effort}}</div>
    </header>
    <table aria-label="${{mode}} transfer heatmap">
      <thead>
        <tr>
          <th>source \\ target</th>
          ${{labels.map((label, index) => `<th>${{label}}<br><span style="font-weight:650;color:#667085">${{ids[index].replace("task_group_", "TG")}}</span></th>`).join("")}}
        </tr>
      </thead>
      <tbody>${{rows}}</tbody>
    </table>
    <div class="legend"><span>lower acc@3</span><div class="bar"></div><span>higher acc@3</span></div>
  `;
  root.appendChild(panel);
}}
</script>
</body>
</html>
"""


def main() -> int:
    scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    task_groups = scope["task_groups"]
    modes = scope["modes"]
    output = {
        "harness": scope.get("harness", "codex"),
        "model": scope.get("model"),
        "reasoning_effort": scope.get("reasoning_effort"),
        "task_groups": task_groups,
        "modes_order": modes,
        "modes": {},
    }

    missing: list[str] = []
    for mode in modes:
        matrix: list[list[float | None]] = []
        std_matrix: list[list[float | None]] = []
        cells = {}
        for source in task_groups:
            row: list[float | None] = []
            std_row: list[float | None] = []
            for target in task_groups:
                cell_key = f"{source['id']}__to__{target['id']}"
                if source["id"] == target["id"]:
                    row.append(None)
                    std_row.append(None)
                    cells[cell_key] = {"status": "not_required", "reason": "diagonal cell is not run"}
                    continue
                cell_path = CELL_ROOT / mode / f"{cell_key}.yaml"
                if not cell_path.exists():
                    row.append(None)
                    std_row.append(None)
                    missing.append(str(cell_path.relative_to(ROOT)))
                    cells[cell_key] = {"status": "missing"}
                    continue
                cell = compute_cell(cell_path)
                row.append(cell["cell_acc_at_3"])
                std_row.append(cell["cell_std_at_3"])
                cells[cell_key] = {"status": "ok", **cell}
            matrix.append(row)
            std_matrix.append(std_row)
        output["modes"][mode] = {
            "matrix": matrix,
            "std_matrix": std_matrix,
            "cells": cells,
        }

    HEATMAP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)

    REPORT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_YAML.write_text(yaml.safe_dump(output, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (HEATMAP_DATA_DIR / "matrices.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for mode in modes:
        write_csv(mode, task_groups, output["modes"][mode])
    HEATMAP_HTML.write_text(build_html(output), encoding="utf-8")

    if missing:
        print("Built heatmap assets with missing cells:")
        for item in missing:
            print(f"- {item}")
    else:
        print("Built complete heatmap assets.")
    print(f"- {REPORT_YAML.relative_to(ROOT)}")
    print(f"- {HEATMAP_HTML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
