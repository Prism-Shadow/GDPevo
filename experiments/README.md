# Experiments

Languages: [English](README.md) | [Chinese](README.zh.md)

This directory contains released GDPevo evaluation results and report
artifacts. The primary released evaluations compare a stateless baseline
(`base`) with three evolution modes: `fewshot`, `self`, and `reflect-3`.
The separate skill-creator comparison fixes the Codex harness and GPT-5.5
xhigh while varying the creator used for the few-shot skill. Together, these
results can be used to study self-evolving agents, evolution-update
mechanisms, and end-to-end agent memory systems.

## Contents

| Path | Purpose |
| --- | --- |
| `EXPERIMENT_BOARD.md` | Primary four-model display board and structured-report coverage |
| `codex_gpt5_5_xhigh/` | Released Codex GPT-5.5 xhigh evaluation run |
| `codex_skill_creator_comparison_gpt5_5_xhigh/` | Released Codex GPT-5.5 xhigh comparison of Codex, CC, DeepAgents, OpenCode, and a minimal naive skill creator |
| `claude_code_opus_4_8_xhigh/` | Released Claude Code Opus 4.8 xhigh evaluation run |
| `claude_code_glm_5_2_max/` | Released Claude Code GLM-5.2 max evaluation run |
| `claude_code_deepseek_v4_pro_max/` | Released Claude Code DeepSeek V4 Pro Preview max evaluation run |

Each released experiment directory contains a `config.yaml`, structured report
YAML files, and any generated artifacts referenced by those reports.
Reusable evaluation workspaces live under
[`../evaluation/eval_workspace/`](../evaluation/eval_workspace/).
