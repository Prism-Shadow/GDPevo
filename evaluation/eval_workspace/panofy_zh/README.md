# Evaluation Workspace — Panofy

本 workspace 在 **Panofy agent 平台**上评估**一个 task group**，在四种条件下使用 `acc`、population `std` 和 SDK 返回的效率元数据：`base`、`fewshot`、`self`、`reflect-3`。

你是**主评估 agent**。你通过**直接调用 Panofy SDK**（`train`、`predict`）并运行每个 task 自带的官方 `eval/eval.sh` 来完成评估——没有固定的 driver 程序可调。需要时把临时的 SDK / 聚合脚本写在 `scratch/` 下；正式产出是 run 记录和报告。

solver 是**通过 SDK 访问的、训练好的 agent**。agent 在**训练时根据 train task 进行 evolve**——训练 instruction 让它从这些任务上学习、在这一类任务上变得更强;**不导出任何东西**。因此每个条件就是同一套输入/输出契约下的一种不同**训练配置**,测试时的调用是 `predict()`。

训练好的 agent 运行在远端、**可以发起外网 HTTP 请求**，所以任务环境部署在一个**运行时给出的远程 URL** 上；你把这个 URL 放进每次 `predict()` 输入的 `api_base_url`，agent 就像本地 solver 一样实时拉取它。

## 目录

| 路径 | 用途 |
| --- | --- |
| `guides/` | 评估流程、四种条件、指标/打分、报告格式 |
| `task_group/` | 当前正在评估的单个正式 task group |
| `agents/` | 每个条件/attempt 训练出的 agent id 的记录 / 小型 registry |
| `runs/` | 每种条件 / 每个 test task / 每次 attempt：`func_input.json`、`answer.json`、`score.yaml`、`run_metadata.yaml` |
| `report/` | 最终的 `report/<task_group_id>.yaml` |
| `scratch/` | 你 staging 的训练材料 + 任意临时 SDK / 聚合脚本 |

## 指南

开始评估前按顺序阅读：

1. `guides/workflow.md` —— 你驱动的 train → predict → score → aggregate 全流程
2. `guides/evolve_modes.md` —— 四种条件（经训练实现）与信息边界
3. `guides/metric_and_scoring.md` —— `acc`、population `std`、用 `eval/eval.sh` 打分、Panofy token / run metadata 计量
4. `guides/report_format.md` —— 最终报告 YAML

## 连接输入（`.env`）

Panofy 服务和任务环境都在远端。把它们的地址放进 `.env` 文件——复制 `.env.example` 为 `.env` 并填写：

- `PANOFY_BASE_URL` —— Panofy SDK base URL（例如一个 Railway 地址）
- `PANOFY_API_KEY` —— Panofy API key（`da_...`）
- `PANOFY_ENV_BASE_URL` —— agent 实时拉取的远程任务环境 API endpoint
- `PANOFY_JUDGE_PATH` —— train-only judge endpoint path，默认 `/api/judge`
- `PANOFY_MODEL_ID` —— 可选，`PANOFY_PRO`（默认）或 `PANOFY_AIR`

`.env` 已被 gitignore——**绝不提交真实 key**；某次运行的具体值来自启动 prompt。运行脚本前先加载，例如 `set -a && source .env && set +a`。

## 环境准备

每个工作区各自装一份环境。用 `uv` 管理（panofy SDK 需要 Python ≥ 3.10）。SDK **从 GitHub 安装** —— 那份带修好的适配，**不要用 PyPI 上的包**：

```bash
uv venv --python 3.12
uv pip install "git+https://github.com/Prism-Shadow/panofy.git#subdirectory=python" pyyaml
```

在 `scratch/` 下写的脚本用 `uv run python scratch/<script>.py` 运行。

## 启动 Prompt

```text
Evaluate task_group/<task_group_id> on Panofy using README.md and guides/.
Panofy base URL: <url>   API key: <da_...>   Env API URL: <url>
Run all four conditions with acc/std, record Panofy agent/run ids and SDK token usage, and write report/<task_group_id>.yaml.
```

## 边界

- 你可以读取完整 task group 以 staging 训练材料、打分和聚合——但 **test** 的 `FUNC_INPUT` 只能携带 `task_id`、`prompt`、`api_base_url`、`answer_template`，**绝不**包含标准答案、task notes 或 evaluator。
- 训练材料遵循 `guides/evolve_modes.md`：`fewshot` 可以包含 train 标准答案；`self` 不可以；`reflect-3` 只能在训练期间使用 train inputs 和 train-only judge feedback。test-time material 绝不能包含任何 test task、test 答案、note、evaluator 源码或 judge API 调用说明。
- 模式允许的训练阶段暴露不算污染：例如 fewshot 训练可以使用 train 标准答案。污染检查关注的是禁止材料泄漏到 test-time inputs、instructions、responses 或 run artifacts。
- 远端 agent 只看到**远程** env URL。确认该 URL 暴露的是与 `task_group/env` 相同的**公开投影**——不要暴露隐藏字段。
- 每次 test call 都写入全新的 `runs/<condition>/<task_id>/attempt_<nn>/`
  目录。如果 test agent 的回复或 run artifact 显示 `FUNC_INPUT` 泄漏了禁止材料，
  或 test-time agent 看到了 test 答案、note、evaluator、env 源码、judge 调用说明、
  当前模式/阶段不允许的 train 材料或其它 run files，必须及时报告，标记该 attempt
  为污染，排除出聚合，并用修正后的 input 在新的干净 run 目录中重跑受影响任务。
