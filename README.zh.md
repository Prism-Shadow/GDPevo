# GDPevo

语言：[English](README.md) | [中文](README.zh.md)

**GDPevo** 是一个公开 benchmark，用来在真实业务工作上衡量 agent 的
self-evolution 能力。

我们不只问：*这个 agent 能不能解决这个任务？*

而是问：**它能不能从相关任务中学习，并在同一业务世界的 held-out 任务上变得更好？**

首个公开版本包含 **120 个 GDP-worthy tasks**，覆盖 CRM、ERP 和 Finance
的 **12 个 task group**。每个 task group 包含一个共享业务环境、**5 个
train tasks** 和 **5 个 held-out test tasks**。Train tasks 是经验来源；
test tasks 用来衡量 agent 学到的经验能否迁移到它没见过的后续任务。

## GDPevo 衡量什么

多数 agent benchmark 衡量的是无状态的单次任务完成。GDPevo 衡量的是一个
stateful loop：

1. Agent 先处理一组相关 train tasks。
2. 它把这些经验沉淀成可复用的流程、memory 或操作规则。
3. 它再在同一业务环境里的 held-out tasks 上接受评估。

因此，GDPevo 可以用于评估：

- self-evolving 或 continual-learning agents；
- 经验提炼与自我改进机制；
- 端到端 agent memory systems；
- 经验是否同时提升 **accuracy** 并降低 **cost**。

这个 benchmark 围绕真实公司 interface 构建，覆盖 CRM、ERP、finance、
procurement、support、lending、investment、HR 和 reporting 等工作流。
Task groups 由 GDPval 和 SOP-Bench 等真实工作来源 seed，再扩展成共享业务环境；
环境中包含 lookalike records、隐藏业务规则和 deterministic rule-based graders。

## 评估设置

已发布的 runs 比较三种 mode：

| Mode | 含义 |
| --- | --- |
| `base` | Agent 冷启动完成 held-out test tasks，不接触 train tasks。 |
| `demo` | Agent 阅读带 gold answers 的 train tasks，提炼可复用流程，再进入 test。 |
| `reflect` | Agent 先在没有答案的 train tasks 上尝试，收到 grading feedback，从错误中更新做法，再进入 test。 |

分数使用 `avg@3`：每个 task 的 held-out accuracy 在 3 次尝试上的平均值。

Cost 使用 report YAML 中的原始 token metrics 计算，并以 **USD** 汇报。公开看板中
token 数按千为单位 (`k`) 展示，cost 四舍五入到小数点后两位。

## 已发布结果

三个 harnesses 上都出现了相同趋势：经验能让 held-out accuracy 提升约
**+17 到 +22 个百分点**。

| Harness | 模型 | Thinking level | `base` avg@3 | `demo` avg@3 | `reflect` avg@3 | 准确率提升 | Cost 变化 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 48.35% | 65.99% | 67.13% | +18.21 pp | -25.75% |
| Claude Code | Opus 4.8 | xhigh | 49.11% | 70.90% | 67.94% | +20.31 pp | -8.69% |
| Panofy | Opus 4.6 | high | 50.17% | 68.24% | 67.98% | +17.94 pp | +11.82% |

完整 per-task reports 位于：

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/panofy_claude_opus_4_6_high/`](experiments/panofy_claude_opus_4_6_high/)

汇总看板见
[`experiments/EXPERIMENT_BOARD.zh.md`](experiments/EXPERIMENT_BOARD.zh.md)。

## 数据

每个 task group 包含：

- 一个共享业务环境；
- 5 个 train tasks；
- 5 个 held-out test tasks；
- 答案文件和 deterministic evaluators；
- 描述数据和 grading 设置的 notes。

已发布 task groups 汇总在
[`data/DATA_BOARD.zh.md`](data/DATA_BOARD.zh.md)。数据目录说明和 task group
格式见 [`data/README.zh.md`](data/README.zh.md)。

## Evaluation Workspaces

可复用的 evaluation workspaces 位于
[`experiments/eval_workspace/`](experiments/eval_workspace/)：

| Workspace | 用途 |
| --- | --- |
| `codex/` | Codex evaluation workflow 和 guides |
| `claude_code/` | Claude Code evaluation workflow 和 guides |
| `panofy/` | Panofy evaluation workflow 和 guides |
| `codex_zh/`, `claude_code_zh/`, `panofy_zh/` | 中文镜像 |

每个 workspace 都说明了如何加载 guides、为一个 task group 跑完整评估、在需要时生成
mode-specific artifacts、聚合 `avg@3`、记录 token/cost metrics，并写出
`report/<task_group_id>.yaml`。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `data/` | 已发布的 task group 数据、数据看板、共享环境、train/test tasks、答案、评测器和 notes。 |
| `experiments/` | 已发布的评估协议、可复用 workspaces、report YAMLs、生成 artifacts 和实验看板。 |
| `site/` | React/Vite public site 和 GitHub Pages build pipeline。 |
| `assets/` | 已发布材料使用的 figures、logos 和视觉资源。 |

## Public Site

公开 landing page 和 blog 位于 [`site/`](site/)。站点使用 React/Vite 构建，并部署到
GitHub Pages。

本地预览：

```bash
cd site
npm ci
npm run build
npm run preview
```
