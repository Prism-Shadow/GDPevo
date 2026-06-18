# GDPevo

Languages: [English](README.md) | [Chinese](README.zh.md)

**GDPevo** is a public benchmark for measuring agent self-evolution on real
business work.

The question is not only: *can the agent solve this task?*

It is: **can the agent learn from related tasks and get better on held-out
tasks from the same business world?**

The first public release contains **120 GDP-worthy tasks** across **12 task
groups** in CRM, ERP, and Finance. Each task group contains one shared business
environment, **5 train tasks**, and **5 held-out test tasks**. Train tasks are
the experience source; test tasks measure whether what the agent learned
transfers to later work it has not seen.

## What GDPevo Measures

Most agent benchmarks measure stateless task completion. GDPevo measures a
stateful loop:

1. An agent works through related train tasks.
2. It turns that experience into reusable procedures, memory, or operating rules.
3. It is evaluated on held-out tasks from the same business environment.

This makes GDPevo useful for evaluating:

- self-evolving or continual-learning agents;
- experience distillation and self-improvement mechanisms;
- end-to-end agent memory systems;
- whether experience improves both **accuracy** and **cost**.

The benchmark is built around real company interfaces: CRM, ERP, finance,
procurement, support, lending, investment, HR, and reporting workflows. Task
groups are seeded from real-job sources such as GDPval and SOP-Bench, then
expanded into shared environments with lookalike records, hidden operational
rules, and deterministic rule-based graders.

## Evaluation Setup

Released runs compare three modes:

| Mode | Meaning |
| --- | --- |
| `base` | The agent solves the held-out test tasks cold, with no prior exposure to train tasks. |
| `demo` | The agent reads train tasks with gold answers, distills reusable procedures, then takes the test. |
| `reflect` | The agent attempts train tasks without answers, receives graded feedback, updates its procedure from mistakes, then takes the test. |

Scores use `avg@3`: mean held-out accuracy over 3 attempts per task.

Cost is reported in **USD** from raw token metrics in the report YAML files.
The released boards show token counts in thousands (`k`) and cost rounded to
two decimals.

## Released Results

Across all three harnesses, the same pattern holds: experience improves
held-out accuracy by roughly **+17 to +22 percentage points**.

| Harness | Model | Thinking level | `base` avg@3 | `demo` avg@3 | `reflect` avg@3 | Accuracy lift | Cost change |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 48.35% | 65.99% | 67.13% | +18.21 pp | -25.75% |
| Claude Code | Opus 4.8 | xhigh | 49.11% | 70.90% | 67.94% | +20.31 pp | -8.69% |
| Panofy | Opus 4.6 | high | 50.17% | 68.24% | 67.98% | +17.94 pp | +11.82% |

Full per-task reports are under:

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/panofy_claude_opus_4_6_high/`](experiments/panofy_claude_opus_4_6_high/)

The aggregate board is
[`experiments/EXPERIMENT_BOARD.md`](experiments/EXPERIMENT_BOARD.md).

## Data

Each task group contains:

- one shared business environment;
- 5 train tasks;
- 5 held-out test tasks;
- answer files and deterministic evaluators;
- notes describing the data and grading setup.

Released task groups are summarized in
[`data/DATA_BOARD.md`](data/DATA_BOARD.md). See
[`data/README.md`](data/README.md) for the data layout and task group format.

## Evaluation Workspaces

Reusable evaluation workspaces live under
[`experiments/eval_workspace/`](experiments/eval_workspace/):

| Workspace | Purpose |
| --- | --- |
| `codex/` | Codex evaluation workflow and guides |
| `claude_code/` | Claude Code evaluation workflow and guides |
| `panofy/` | Panofy evaluation workflow and guides |
| `codex_zh/`, `claude_code_zh/`, `panofy_zh/` | Chinese mirrors |

Each workspace describes how to load its guides, run the full evaluation for a
task group, generate mode-specific artifacts when needed, aggregate `avg@3`, record
token/cost metrics, and write `report/<task_group_id>.yaml`.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `data/` | Released task group data, data board, shared environments, train/test tasks, answers, evaluators, and notes. |
| `experiments/` | Released evaluation protocols, reusable workspaces, report YAMLs, generated artifacts, and experiment board. |
| `site/` | React/Vite public site and GitHub Pages build pipeline. |
| `assets/` | Figures, logos, and visual assets used by released materials. |

## Public Site

The public landing page and blog live in [`site/`](site/). The site is built
with React/Vite and deployed to GitHub Pages.

Local preview:

```bash
cd site
npm ci
npm run build
npm run preview
```
