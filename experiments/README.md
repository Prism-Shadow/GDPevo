# Experiments

Languages: [English](README.md) | [Chinese](README.zh.md)

This directory contains released GDPevo evaluation methods and result artifacts.
The evaluation compares a stateless baseline with two evolve methods:
`demo` and `reflect`. It can be used to study
self-evolving agents, skill creators, and end-to-end agent memory systems.

## Contents

| Path | Purpose |
| --- | --- |
| `EXPERIMENT_BOARD.md` | Summary table for released evaluation results |
| `eval_workspace/` | Reusable evaluation workspace and guides |
| `eval_workspace_zh/` | Chinese mirror of the reusable evaluation workspace and guides |
| `codex_gpt5_5_xhigh/` | Released Codex GPT-5.5 xhigh evaluation run |
| `claude_code_opus_4_8_xhigh/` | Released Claude Code Opus 4.8 xhigh evaluation run |
| `panofy_claude_opus_4_6_high/` | Released Panofy Claude Opus 4.6 high evaluation run |

Each released experiment directory contains a `config.yaml`, structured report
YAML files, and any generated skill packages referenced by those reports.
