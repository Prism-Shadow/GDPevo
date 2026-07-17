# GDPevo: Evaluating Agent Self-Evolution on Real Business Tasks

Languages: [English](README.md) | [Chinese](README.zh.md)

[![Blog](https://img.shields.io/badge/Blog-Read%20the%20blog-0f7b5f?style=flat&logo=readthedocs&logoColor=white)](https://prism-shadow.github.io/GDPevo/blog.html)

**GDPevo** is a public benchmark for evaluating agent self-evolution on real business work. The data release contains 240 tasks across 24 task groups spanning CRM, ERP, finance, healthcare, legal, data analysis, and engineering operations; each group has one shared business environment, 5 train tasks, and 5 held-out test tasks. For the full motivation, construction pipeline, and findings, read the [project blog](https://prism-shadow.github.io/GDPevo/blog.html).

## Evaluation Results

Accuracy is reported as `acc`: each test task is run 3 times, then averaged over 12 task groups, with population `std` shown in parentheses. `rounds` reports the average number of solver model-response rounds per attempt, and `tool calls` reports the average number of solver tool-call requests per attempt. Cost is reported in USD; lift and cost change are relative to `base`.

The released runs compare four modes:

- **base**: run the test tasks directly, without any evolution step.
- **self**: evolve its own working strategy from train inputs and the environment, without train answers.
- **fewshot**: learn from train inputs plus gold answers as demonstrations.
- **reflect-3**: iterate with train-only judge feedback, then consolidate the evolved workflow.

| Harness | Model | Thinking level | `base` acc | `fewshot` acc | `self` acc | `reflect-3` acc | `base` rounds | `base` tool calls | `fewshot` rounds | `fewshot` tool calls | `self` rounds | `self` tool calls | `reflect-3` rounds | `reflect-3` tool calls | `fewshot` cost change | `self` cost change | `reflect-3` cost change | `fewshot` lift | `self` lift | `reflect-3` lift |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 46.72% (±5.13%) | 64.91% (±6.36%) | 54.99% (±8.73%) | 57.45% (±7.62%) | 14.91 | 35.89 | 11.58 | 26.70 | 9.71 | 22.74 | 10.83 | 24.42 | -29.24% | -32.18% | -25.74% | +18.19 pp | +8.27 pp | +10.73 pp |
| Claude Code | Opus 4.8 | xhigh | 49.11% (±5.25%) | 70.90% (±6.38%) | 57.37% (±6.79%) | 62.72% (±6.68%) | 14.62 | 17.17 | 11.10 | 15.02 | 11.78 | 15.84 | 12.15 | 16.26 | -9.61% | +0.53% | -0.34% | +21.79 pp | +8.26 pp | +13.62 pp |
| Panofy | Opus 4.6 | high | 50.40% (±6.99%) | 71.47% (±4.93%) | 58.39% (±5.74%) | 59.82% (±7.31%) | 15.16 | 19.53 | 13.48 | 16.84 | 12.51 | 16.32 | 14.37 | 17.79 | +8.27% | -6.00% | +1.99% | +21.07 pp | +7.99 pp | +9.41 pp |
| Claude Code | GLM-5.2 | max | 47.73% (±5.21%) | 69.55% (±8.85%) | 55.91% (±7.84%) | 63.35% (±7.51%) | 17.57 | 26.01 | 15.49 | 22.81 | 15.98 | 23.87 | 15.36 | 22.67 | -12.28% | -10.23% | -16.50% | +21.83 pp | +8.18 pp | +15.62 pp |
| Claude Code | Kimi K2.6 | enabled | 25.14% (±12.15%) | 30.48% (±13.22%) | 29.16% (±14.18%) | 32.68% (±14.25%) | 46.24 | 67.31 | 37.87 | 56.65 | 32.67 | 49.53 | 31.68 | 45.31 | -14.79% | -26.18% | -17.19% | +5.34 pp | +4.02 pp | +7.54 pp |
| Claude Code | DeepSeek V4 Pro | max | 46.06% (±6.90%) | 54.80% (±9.65%) | 48.69% (±8.75%) | 49.22% (±8.67%) | 13.22 | 24.51 | 11.46 | 21.02 | 10.53 | 19.21 | 10.26 | 19.13 | +2.15% | +1.19% | -1.91% | +8.74 pp | +2.63 pp | +3.16 pp |

See the full experiment board in [`experiments/EXPERIMENT_BOARD.md`](experiments/EXPERIMENT_BOARD.md).

Per-task reports are under:

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/panofy_claude_opus_4_6_high/`](experiments/panofy_claude_opus_4_6_high/)
- [`experiments/claude_code_glm_5_2_max/`](experiments/claude_code_glm_5_2_max/)
- [`experiments/claude_code_kimi2_6_enabled/`](experiments/claude_code_kimi2_6_enabled/)
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

  - **Purpose**: Run formal `acc`, population `std`, turn-count, token, and cost evaluation for one released task group. It includes Codex, Claude Code, Panofy, and Chinese mirror workspaces.
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
