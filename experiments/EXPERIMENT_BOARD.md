# Experiment Board

Languages: [English](EXPERIMENT_BOARD.md) | [Chinese](EXPERIMENT_BOARD.zh.md)

This board presents the four primary GDPevo runs on task groups 001–024:
Codex GPT-5.5, Claude Code Opus 4.8, Claude Code GLM-5.2, and Claude Code
DeepSeek V4 Pro Preview. Opus 4.8 currently has released reports for 001–012;
its aggregate row will be completed after reports 013–024 are delivered.

## Aggregate Results

`acc` is the arithmetic mean of the task-group-level `overall_acc_at_3` values.
The value after `±` is the arithmetic mean of task-group-level
`overall_std_at_3`, preserving the existing hierarchical population-STD
convention. Rounds, tool calls, and costs use the same task-group averaging
shape. Cost change and lift are relative to the same run's `base` aggregate.

| Harness | Model | Thinking | `base` acc | `fewshot` acc | `self` acc | `reflect-3` acc | `base` rounds | `base` tool calls | `fewshot` rounds | `fewshot` tool calls | `self` rounds | `self` tool calls | `reflect-3` rounds | `reflect-3` tool calls | `fewshot` cost change | `self` cost change | `reflect-3` cost change | `fewshot` lift | `self` lift | `reflect-3` lift |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 49.37% (±5.51%) | 64.51% (±6.31%) | 55.80% (±7.63%) | 57.82% (±7.38%) | 14.96 | 36.19 | 12.04 | 28.02 | 11.45 | 26.77 | 11.85 | 27.88 | -20.88% | -22.87% | -17.23% | +15.14 pp | +6.42 pp | +8.45 pp |
| Claude Code | Opus 4.8 | xhigh | pending TG013–024 | pending | pending | pending | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Claude Code | GLM-5.2 | max | 46.12% (±5.82%) | 60.09% (±7.90%) | 50.96% (±8.32%) | 55.49% (±8.28%) | 22.94 | 30.60 | 22.63 | 31.26 | 21.93 | 30.84 | 20.65 | 28.67 | +5.74% | -0.92% | -7.07% | +13.97 pp | +4.84 pp | +9.37 pp |
| Claude Code | DeepSeek V4 Pro Preview | max | 43.58% (±7.77%) | 48.79% (±9.05%) | 46.17% (±7.89%) | 47.15% (±8.18%) | 15.65 | 27.31 | 14.73 | 25.35 | 14.29 | 24.45 | 12.68 | 21.90 | +2.58% | +2.52% | -4.77% | +5.21 pp | +2.59 pp | +3.57 pp |

## Structured Reports

| Run | Coverage | Reports |
| --- | --- | --- |
| Codex / GPT-5.5 / xhigh | 001–024 | [`codex_gpt5_5_xhigh/reports/`](codex_gpt5_5_xhigh/reports/) |
| Claude Code / Opus 4.8 / xhigh | 001–012; 013–024 pending | [`claude_code_opus_4_8_xhigh/reports/`](claude_code_opus_4_8_xhigh/reports/) |
| Claude Code / GLM-5.2 / max | 001–024 | [`claude_code_glm_5_2_max/reports/`](claude_code_glm_5_2_max/reports/) |
| Claude Code / DeepSeek V4 Pro Preview / max | 001–024 | [`claude_code_deepseek_v4_pro_max/reports/`](claude_code_deepseek_v4_pro_max/reports/) |
