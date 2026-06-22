# GDPevo: Evaluating Agent Self-Evolution on Real Business Tasks

Languages: [English](README.md) | [Chinese](README.zh.md)

[![Blog](https://img.shields.io/badge/Blog-Read%20the%20blog-0f7b5f?style=flat&logo=readthedocs&logoColor=white)](https://prism-shadow.github.io/GDPevo/blog.html)

**GDPevo** is a public benchmark for evaluating agent self-evolution on real business work. The release contains 120 tasks across 12 task groups in customer relationship management (CRM), enterprise resource planning (ERP), and Finance; each group has one shared business environment, 5 train tasks, and 5 held-out test tasks. For the full motivation, construction pipeline, and findings, read the [project blog](https://prism-shadow.github.io/GDPevo/blog.html).

## Evaluation Results

Accuracy is reported as `acc@3`, averaged over 12 task groups. Cost is reported in USD.

| Harness | Model | Thinking level | `base` acc@3 | `fewshot` acc@3 | `reflect` acc@3 | Accuracy lift | Cost change |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 48.35% | 65.99% | 67.13% | +18.21 pp | -25.75% |
| Claude Code | Opus 4.8 | xhigh | 49.11% | 70.90% | 67.94% | +20.31 pp | -8.69% |
| Panofy | Opus 4.6 | high | 50.17% | 68.24% | 67.98% | +17.94 pp | +11.82% |

See the full experiment board in [`experiments/EXPERIMENT_BOARD.md`](experiments/EXPERIMENT_BOARD.md).

Per-task reports are under:

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/panofy_claude_opus_4_6_high/`](experiments/panofy_claude_opus_4_6_high/)

## Repository Layout

| Path | Purpose |
| --- | --- |
| [`data/`](data/) | Released benchmark data, including task groups, shared environments, train/test tasks, reference answers, and rule-based evaluators. |
| [`data_construction/`](data_construction/) | Four-stage construction and evaluation workspaces, from scenario discovery through score evaluation. |
| [`experiments/`](experiments/) | Released evaluation results, report YAMLs, and the aggregate experiment board. |
| [`site/`](site/) | Public website and blog for the benchmark release. |

## How To Use This Repo

- Benchmark data: read the summary in [`data/DATA_BOARD.md`](data/DATA_BOARD.md), then inspect task groups under [`data/task_groups/`](data/task_groups/).
- Evaluation results: read [`experiments/EXPERIMENT_BOARD.md`](experiments/EXPERIMENT_BOARD.md), then open the per-task reports under the three experiment directories.
- Construction and evaluation workspaces: use the four-stage workflow under [`data_construction/`](data_construction/). Each workspace has its own README and guides.
- Stages 1-3 are written for Codex workflows. Other agent frameworks can reuse the same structure, but may need light adaptation.

## Workspace Usage Guide

These workspaces are agent-ready folders for building, reviewing, and evaluating GDPevo. To use one, open the corresponding folder with an agent, place the input data required by that stage, then send the prompt to trigger the workflow.

- **Scenario Discovery**: [`data_construction/Stage_1_Scenario_Discovery/`](data_construction/Stage_1_Scenario_Discovery/)

  - **Purpose**: Collect raw source-dataset data items that fit a given business scenario.
  - **Input data**: a target business scenario (`<target_scenario>`) and raw source benchmark data to search.
  - **Prompt**: `Read README.md, search raw data in source benchmark datasets according to <target_scenario>, and write scenario data under scenario/<scenario_id>/.`

- **Task Group Synthesis**: [`data_construction/Stage_2_Task_Group_Synthesis/task_factory/`](data_construction/Stage_2_Task_Group_Synthesis/task_factory/)

  - **Purpose**: Build one full task group from one scenario. The Chinese mirror is [`task_factory_zh/`](data_construction/Stage_2_Task_Group_Synthesis/task_factory_zh/).
  - **Input data**: one Stage 1 scenario copied into `seed_scenario/`, including `scenario.yaml`, notes, and attachments.
  - **Prompt**: `Read README.md and guides/, then build task_group/<task_group_id>/ for one complete task group.`

- **Quality Filtering**: [`data_construction/Stage_3_Quality_Filtering/review_workspace/`](data_construction/Stage_3_Quality_Filtering/review_workspace/)

  - **Purpose**: Review one completed task group with script checks and independent reviewer-agent votes. The Chinese mirror is [`review_workspace_zh/`](data_construction/Stage_3_Quality_Filtering/review_workspace_zh/).
  - **Input data**: one completed task group copied into `task_group/`, plus the matching Stage 2 scratch material in `scratch/`.
  - **Prompt**: `Read README.md and guides/, review one task_group/ with scratch/, collect 6 votes, and write ../reports/<task_group_id>.yaml.`

- **Score Evaluation**: [`data_construction/Stage_4_Score_Evaluation/eval_workspace/`](data_construction/Stage_4_Score_Evaluation/eval_workspace/)

  - **Purpose**: Run formal `acc@3`, token, and cost evaluation for one released task group. It includes Codex, Claude Code, Panofy, and Chinese mirror workspaces.
  - **Input data**: one released task group copied into the selected evaluator workspace, plus the credentials or config required by that workspace.
  - **Prompt**: `Read README.md and guides/, run score evaluation for the staged task group, and write report/<task_group_id>.yaml.`

## Citation

```bibtex
@misc{gdpevo2026,
  title  = {GDPevo: Measuring agent self-evolution on real business work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}
```
