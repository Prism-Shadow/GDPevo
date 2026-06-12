# Experiments

Languages: [English](README.md) | [Chinese](README.zh.md)

This directory contains released GDPevo evaluation methods and result artifacts.
The evaluation compares a stateless baseline with two skill-creation methods:
`demonstration_skill` and `reflection_skill`. It can be used to study
self-evolving agents, skill creators, and end-to-end agent memory systems.

## Contents

| Path | Purpose |
| --- | --- |
| `EXPERIMENT_BOARD.md` | Summary table for released evaluation results |
| `eval_workspace/` | Reusable evaluation workspace and guides |
| `eval_workspace_zh/` | Chinese mirror of the reusable evaluation workspace and guides |
| `codex_gpt5_5_xhigh/` | Released Codex GPT-5.5 xhigh evaluation run |

Each released experiment directory contains a `config.yaml`, structured report
YAML files, and the generated skill packages referenced by those reports.

In the released Codex GPT-5.5 xhigh run, skill-based evolution improves
accuracy by 18.21 percentage points on average and reduces token cost by 25.75%
on average. The reusable evaluation workspace shows how Codex can automate the
full flow: skill generation, solver execution, evaluator calls, metric
aggregation, and final report writing.
