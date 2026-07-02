# Experiments

Languages: [English](README.md) | [Chinese](README.zh.md)

This directory contains released GDPevo evaluation results and report artifacts.
The released evaluations compare a stateless baseline (`base`) with three
evolution modes: `fewshot`, `self`, and `reflect-3`. They can be used to study
self-evolving agents, evolution-update mechanisms, and end-to-end agent memory
systems.

## Contents

| Path | Purpose |
| --- | --- |
| `EXPERIMENT_BOARD.md` | Summary table for released evaluation results |
| `codex_gpt5_5_xhigh/` | Released Codex GPT-5.5 xhigh evaluation run |
| `claude_code_opus_4_8_xhigh/` | Released Claude Code Opus 4.8 xhigh evaluation run |
| `panofy_claude_opus_4_6_high/` | Released Panofy Claude Opus 4.6 high evaluation run |
| `claude_code_glm_5_2_max/` | Released Claude Code GLM-5.2 max evaluation run |

Each released experiment directory contains a `config.yaml`, structured report
YAML files, and any generated artifacts referenced by those reports.
Reusable evaluation workspaces live under
[`../evaluation/eval_workspace/`](../evaluation/eval_workspace/).
