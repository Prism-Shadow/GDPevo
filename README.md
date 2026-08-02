# GDPevo: Evaluating Agent Self-Evolution on Real Business Tasks

Languages: [English](README.md) | [Chinese](README.zh.md)

[![Blog](https://img.shields.io/badge/Blog-Read%20the%20blog-0f7b5f?style=flat&logo=readthedocs&logoColor=white)](https://prism-shadow.github.io/GDPevo/blog.html)

**GDPevo** is a public benchmark for evaluating agent self-evolution on real business work. The data release contains 240 tasks across 24 task groups spanning CRM, ERP, finance, healthcare, legal, data analysis, and engineering operations; each group has one shared business environment, 5 train tasks, and 5 held-out test tasks. For the full motivation, construction pipeline, and findings, read the [project blog](https://prism-shadow.github.io/GDPevo/blog.html).

## Evaluation Results

Each experiment is run 3 times. Values in parentheses are standard deviations; all other values are means. Accuracy is reported as `acc`. `rounds` reports the average number of solver model-response rounds per attempt, and `tool calls` reports the average number of solver tool-call requests per attempt. Cost is reported in USD; lift and cost change are relative to `base`.

The released runs compare four modes:

- **base**: run the test tasks directly, without any evolution step.
- **self**: evolve its own working strategy from train inputs and the environment, without train answers.
- **fewshot**: learn from train inputs plus gold answers as demonstrations.
- **reflect-3**: iterate with train-only judge feedback, then consolidate the evolved workflow.

The primary leaderboard uses task groups 001–024.

| Harness | Model | Thinking | `base` acc | `fewshot` acc | `self` acc | `reflect-3` acc | `base` rounds | `base` tool calls | `fewshot` rounds | `fewshot` tool calls | `self` rounds | `self` tool calls | `reflect-3` rounds | `reflect-3` tool calls | `fewshot` cost change | `self` cost change | `reflect-3` cost change | `fewshot` lift | `self` lift | `reflect-3` lift |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 49.37% (±5.51%) | 64.51% (±6.31%) | 55.80% (±7.63%) | 57.82% (±7.38%) | 14.96 | 36.19 | 12.04 | 28.02 | 11.45 | 26.77 | 11.85 | 27.88 | -20.88% | -22.87% | -17.23% | +15.14 pp | +6.42 pp | +8.45 pp |
| Claude Code | Opus 4.8 | xhigh | 50.63% (±5.37%) | 67.07% (±6.22%) | 55.05% (±6.96%) | 59.27% (±7.01%) | 17.06 | 19.30 | 14.46 | 18.16 | 15.57 | 19.33 | 15.58 | 19.43 | -0.57% | +9.06% | +4.77% | +16.44 pp | +4.42 pp | +8.64 pp |
| Claude Code | GLM-5.2 | max | 46.12% (±5.82%) | 60.09% (±7.90%) | 50.96% (±8.32%) | 55.49% (±8.28%) | 22.94 | 30.60 | 22.63 | 31.26 | 21.93 | 30.84 | 20.65 | 28.67 | +5.74% | -0.92% | -7.07% | +13.97 pp | +4.84 pp | +9.37 pp |
| Claude Code | DeepSeek V4 Pro Preview | max | 43.58% (±7.77%) | 48.79% (±9.05%) | 46.17% (±7.89%) | 47.15% (±8.18%) | 15.65 | 27.31 | 14.73 | 25.35 | 14.29 | 24.45 | 12.68 | 21.90 | +2.58% | +2.52% | -4.77% | +5.21 pp | +2.59 pp | +3.57 pp |

See the full experiment board in [`experiments/EXPERIMENT_BOARD.md`](experiments/EXPERIMENT_BOARD.md).

Per-task reports are under:

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/claude_code_glm_5_2_max/`](experiments/claude_code_glm_5_2_max/)
- [`experiments/claude_code_deepseek_v4_pro_max/`](experiments/claude_code_deepseek_v4_pro_max/)

## Repository Layout

| Path | Purpose |
| --- | --- |
| [`data/`](data/) | Released benchmark data, including task groups, shared environments, train/test tasks, reference answers, and rule-based evaluators. |
| [`data_construction/`](data_construction/) | Construction workspaces for scenario discovery, task group synthesis, and quality filtering. |
| [`evaluation/`](evaluation/) | Reusable score evaluation workspaces for released task groups. |
| [`experiments/`](experiments/) | Released evaluation results, report YAMLs, and the aggregate experiment board. |
| [`site/`](site/) | Public website and blog for the benchmark release. |

## How To Use This Repo

- Benchmark data: read the summary in [`data/DATA_BOARD.md`](data/DATA_BOARD.md), then inspect task groups under [`data/task_groups/`](data/task_groups/).
- Evaluation results: read [`experiments/EXPERIMENT_BOARD.md`](experiments/EXPERIMENT_BOARD.md), then open the per-task reports under the released experiment directories.
- Construction workspaces: use the three-stage workflow under [`data_construction/`](data_construction/).
- Score evaluation workspaces: use [`evaluation/eval_workspace/`](evaluation/eval_workspace/).
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

- **Score Evaluation**: [`evaluation/eval_workspace/`](evaluation/eval_workspace/)

  - **Purpose**: Run formal `acc`, population `std`, turn-count, token, and cost evaluation for one released task group. It includes Codex, Claude Code, and Chinese mirror workspaces.
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
