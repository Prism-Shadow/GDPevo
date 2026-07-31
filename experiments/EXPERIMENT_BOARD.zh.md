# 实验看板

语言：[English](EXPERIMENT_BOARD.md) | [中文](EXPERIMENT_BOARD.zh.md)

本看板展示 GDPevo 在 task groups 001–024 上的四个主运行：Codex GPT-5.5、
Claude Code Opus 4.8、Claude Code GLM-5.2 和 Claude Code
DeepSeek V4 Pro Preview。Opus 4.8 当前已发布 001–012 报告；013–024 报告交付后再补全其汇总行。

## 汇总结果

`acc` 是各 task group 的 `overall_acc_at_3` 的算术平均。`±` 后的值是各
task group 的 `overall_std_at_3` 的算术平均，沿用此前的分层 population STD
口径。rounds、tool calls 和 cost 使用相同的 task-group 平均方式。费用变化和
准确率提升均相对于同一运行的 `base` 汇总值计算。

| 评测框架 | 模型 | 思考强度 | `base` acc | `fewshot` acc | `self` acc | `reflect-3` acc | `base` 轮次 | `base` 工具调用 | `fewshot` 轮次 | `fewshot` 工具调用 | `self` 轮次 | `self` 工具调用 | `reflect-3` 轮次 | `reflect-3` 工具调用 | `fewshot` 费用变化 | `self` 费用变化 | `reflect-3` 费用变化 | `fewshot` 提升 | `self` 提升 | `reflect-3` 提升 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 49.37% (±5.51%) | 64.51% (±6.31%) | 55.80% (±7.63%) | 57.82% (±7.38%) | 14.96 | 36.19 | 12.04 | 28.02 | 11.45 | 26.77 | 11.85 | 27.88 | -20.88% | -22.87% | -17.23% | +15.14 个百分点 | +6.42 个百分点 | +8.45 个百分点 |
| Claude Code | Opus 4.8 | xhigh | 013–024 待补 | 待补 | 待补 | 待补 | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Claude Code | GLM-5.2 | max | 46.12% (±5.82%) | 60.09% (±7.90%) | 50.96% (±8.32%) | 55.49% (±8.28%) | 22.94 | 30.60 | 22.63 | 31.26 | 21.93 | 30.84 | 20.65 | 28.67 | +5.74% | -0.92% | -7.07% | +13.97 个百分点 | +4.84 个百分点 | +9.37 个百分点 |
| Claude Code | DeepSeek V4 Pro Preview | max | 43.58% (±7.77%) | 48.79% (±9.05%) | 46.17% (±7.89%) | 47.15% (±8.18%) | 15.65 | 27.31 | 14.73 | 25.35 | 14.29 | 24.45 | 12.68 | 21.90 | +2.58% | +2.52% | -4.77% | +5.21 个百分点 | +2.59 个百分点 | +3.57 个百分点 |

## 结构化报告

| 运行 | 覆盖范围 | 报告 |
| --- | --- | --- |
| Codex / GPT-5.5 / xhigh | 001–024 | [`codex_gpt5_5_xhigh/reports/`](codex_gpt5_5_xhigh/reports/) |
| Claude Code / Opus 4.8 / xhigh | 001–012；013–024 待补 | [`claude_code_opus_4_8_xhigh/reports/`](claude_code_opus_4_8_xhigh/reports/) |
| Claude Code / GLM-5.2 / max | 001–024 | [`claude_code_glm_5_2_max/reports/`](claude_code_glm_5_2_max/reports/) |
| Claude Code / DeepSeek V4 Pro Preview / max | 001–024 | [`claude_code_deepseek_v4_pro_max/reports/`](claude_code_deepseek_v4_pro_max/reports/) |
