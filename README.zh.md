# GDPevo

语言：[English](README.md) | [中文](README.zh.md)

**GDPevo** 是一个公开基准，用来评估智能体在真实企业任务上的自进化能力。当前版本包含 120 个任务，覆盖客户关系管理（CRM）、企业资源计划（ERP）和金融三类业务，共 12 个任务组；每个任务组都有一个共享业务环境、5 个训练任务和 5 个保留测试任务。完整动机、构建流程和结果分析见[项目博客](https://prism-shadow.github.io/GDPevo/blog.html)。

## 评测结果

准确率使用 `acc@3`，并在 12 个任务组上取均值。费用以美元计。

| 评测框架 | 模型 | 思考强度 | `base` 准确率 | `demo` 准确率 | `reflect` 准确率 | 准确率提升 | 费用变化 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 48.35% | 65.99% | 67.13% | +18.21 个百分点 | -25.75% |
| Claude Code | Opus 4.8 | xhigh | 49.11% | 70.90% | 67.94% | +20.31 个百分点 | -8.69% |
| Panofy | Opus 4.6 | high | 50.17% | 68.24% | 67.98% | +17.94 个百分点 | +11.82% |

完整汇总见 [`experiments/EXPERIMENT_BOARD.zh.md`](experiments/EXPERIMENT_BOARD.zh.md)。

逐任务报告见：

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/panofy_claude_opus_4_6_high/`](experiments/panofy_claude_opus_4_6_high/)

## 目录结构

| 路径 | 内容 |
| --- | --- |
| [`data/`](data/) | 已发布的基准数据，包括任务组、共享环境、训练与测试任务、参考答案和基于规则的评测器。 |
| [`experiments/`](experiments/) | 已发布的评测结果、可复用评测工作区、报告文件和实验汇总表。 |
| [`site/`](site/) | 基准发布用的公开网站与博客。 |

## 如何使用这个仓库

- 基准数据：阅读 [`data/DATA_BOARD.zh.md`](data/DATA_BOARD.zh.md) 了解任务组概览，再查看 [`data/task_groups/`](data/task_groups/) 中的具体任务。
- 评测结果：在 [`experiments/EXPERIMENT_BOARD.zh.md`](experiments/EXPERIMENT_BOARD.zh.md) 查看汇总结果，再进入三个实验目录阅读逐任务报告。
- 评测工作区：如果要重新运行或改造评测流程，从 [`experiments/eval_workspace/`](experiments/eval_workspace/) 开始。每个工作区都包含说明文档、任务组输入、运行产物和报告目录。
- 本地预览公开网站：

```bash
cd site
npm ci
npm run build
npm run preview
```

## 引用

```bibtex
@misc{gdpevo2026,
  title  = {GDPevo: Measuring agent self-evolution on real business work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}
```
