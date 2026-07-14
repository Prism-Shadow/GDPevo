# 主 Agent 与 Subagent 协作流程

## 角色分工

第二阶段构造可以使用主 agent 与多个 subagents 协作。

本工作区要求使用 subagents 完成环境和 task 构造。用户要求在本工作区构造 task group 时，应视为允许使用这些构造 subagents。难度校准使用不同机制：不能使用主控系统的 subagent 进行校准，每次校准都必须按照 `calibration_runtime.md` 启动隔离的 Dockerized `codex exec` 进程。

主 agent 负责整体一致性：

- 读取 seed scenario 和 examples。
- 编写 `scratch/task_group_design.md`。
- 编写 env blueprint，说明需要的业务系统、公开入口、数据契约、随机种子和生成数据预期。
- 将 env 实现交给上下文干净的 coding subagent。
- 分配 train/test 子任务给 subagents。
- 集成 env 实现和其他 subagent 产物。
- 检查路径、schema、notes、answer、eval 和校准结果。
- 维护最终 `task_group.yaml`。

env-builder coding subagent 负责环境实现：

- 基于 env blueprint 工作，而不是读取完整构造上下文。
- 实现整个 task group 共用的 `env/` 基础设施，包括 setup 脚本、Web/API/数据库服务、生成的业务数据、随机种子和输出清单。
- 保证环境可被 train/test 共同复用，而不是只服务单个 task。
- 将已实现的 endpoints、tables、生成文件、seeds 和 setup 步骤反馈给主 agent。
- 不设计 task answers、notes、rubrics 或 solver-facing prompts。

task-builder subagents 负责局部任务生产：

- 总共应有 10 个 task-builder subagents：5 个 train tasks 和 5 个 test tasks 各 1 个。
- 只处理分配给自己的 train 或 test task。
- 基于主 agent 提供的 task group design、env 入口和数据约束创建 `input/`、`notes/`、`output/` 和 `eval/`。
- 可以通过主 agent 提出需要新增的环境能力或数据，但不直接各自实现独立 env。
- 不应修改其他 subagent 的任务。

Dockerized Codex 进程负责难度校准：

- 3 个相互隔离的 fewshot skill-generation 进程分别读取全部 5 个 train inputs 和对应标准答案，生成 3 个独立 skill package。
- base：每个 test task 运行 3 个隔离进程，5 个 test tasks 共 15 个进程。
- fewshot：每个 test task 运行 3 个隔离进程，attempt 01/02/03 分别使用对应的 skill package，5 个 test tasks 共 15 个进程。
- 每个进程都有新建的 staged `/work`、专属 `CODEX_HOME`、固定 prompt，且只能看到该运行允许的文件。
- 保留完整 Codex session trace；不能访问 notes、evaluator、环境源码、构造草稿或其他 runs。

reviewer subagent 负责独立审查：

- 检查结构、可解释性、数据生成、env 复杂度、prompt 泄漏、迁移设计、评测有效性、rubric 多维度和 partial-credit 行为。

## 阶段概览

构造应按以下阶段推进。不要从读取 seed scenario 直接跳到生成最终 task group。

| 阶段 | 负责人 | 主要产物 | 进入下一阶段前的检查 |
| --- | --- | --- | --- |
| 1. 理解场景 | 主 agent | 来源 example 难度审计和场景理解 | 主 agent 能说明来源 examples 的真实工作流、数据表面和难度来源 |
| 2. Task group 设计 | 主 agent | 只写 `scratch/task_group_design.md` | 5 个 train、5 个 test、迁移计划、diversity 计划、scoring 计划和 task-builder 分派都已明确；本阶段不创建 task 文件、答案、evaluator 或 env 实现 |
| 3. Env blueprint | 主 agent | `scratch/env_blueprint.md` | 共享业务系统、公开入口、数据契约、生成种子、宿主机监听与端口、固定 host-gateway 访问、reset 行为和 manifest 要求都已说明 |
| 4. Env 实现 | 上下文干净的 env-builder coding subagent | `env/` | 环境服务于全部任务，按业务领域组织，能被独立 agent 容器访问，且没有接近答案的 per-task endpoint |
| 5. Task 构造 | 10 个 task-builder subagents | `train_tasks/` 和 `test_tasks/` 任务目录 | 每个任务都有 solver input、中英双语 notes、标准答案、evaluator 和 answer template |
| 6. 集成和 evaluator 自检 | 主 agent | 最终 `task_group.yaml`、路径/schema 修正、`scratch/rubric_validation.md`、evaluator 与 Judge API 自检记录 | 每个 evaluator 对标准答案打满分；selective perturbation 只损失对应分值；partial answer 能得到部分分；`/api/judge` 拒绝 test id 且不暴露隐藏细节 |
| 7. 难度校准 | Dockerized Codex 进程，主 agent 负责打分 | `scratch/difficulty_calibration.md`、traces、3 个独立 fewshot skill package、base/fewshot 结果 | 固定 prompt 运行彼此隔离；overall base 约为 `0.40-0.60`；fewshot gain 约为 `0.10-0.20`，且不过度饱和 |
| 8. 独立 review 和返工 | reviewer subagent 和主 agent | review findings、返工记录、必要时重跑校准 | 结构、环境、notes、评测、迁移和难度要求都通过 |

## 构造流程

1. 主 agent 编写 `scratch/task_group_design.md`，覆盖 10 个 task 的规划、task-builder 分派、任务 diversity、可迁移 SOP、train/test 角色、环境计划、数据生成计划和评测计划。这里只是设计文档阶段，不能创建 task 目录、prompt、notes、标准答案、evaluator 或 env 实现文件。
2. 主 agent 编写 `scratch/env_blueprint.md`，说明共享业务系统、公开接口、数据契约、生成种子、manifest 要求、`TASK_ENV_BIND`/`TASK_ENV_PORT`、固定 host-gateway 访问、reset 行为和预期环境行为。
3. 上下文干净的 env-builder coding subagent 根据 `scratch/env_blueprint.md` 实现 `env/`，包括 Web、API、PostgreSQL、数据生成脚本、生成数据、setup 脚本、manifest、health check 和由主 agent 控制的 reset/reseed 流程。
4. 主 agent review 并集成 env-builder 产物，再记录 task builders 可使用的环境入口。
5. 主 agent 启动 10 个 task-builder subagents，可以并行或分批运行：`train_001` 到 `train_005` 和 `test_001` 到 `test_005` 各 1 个。
6. Task-builder subagents 分别生成自己负责 task 的 `input/`、`notes/`、`output/` 和 `eval/`。
7. 主 agent 集成所有任务，统一修正路径、schema、notes 和 env 使用方式。
8. 主 agent 运行每个 evaluator 对照标准答案自检，创建 `scratch/rubric_validation.md`，并使用单方面错误和 partial answer probes 验证多维度、非二值打分。随后把 `env/judge_api.py` 接入服务，验证 `/api/judge` 对 train 标准答案打满分、保留 evaluator 的 partial score、拒绝 test task id，且不会返回隐藏 evaluator 或答案内容。
9. 难度校准前，主 agent 在宿主机以 `TASK_ENV_BIND=0.0.0.0` 启动环境，所有 agent 容器都带 `--add-host=host.docker.internal:host-gateway`，并从临时容器验证 `http://host.docker.internal:<TASK_ENV_PORT>` 的 health endpoint。
10. base calibration：使用固定 base prompt 启动 15 个独立 Dockerized `codex exec` runs，每个 test task 3 次。主 agent 在 Codex 进程外评分并记录 base `avg@3`。
11. 使用固定 fewshot skill-generation prompt 启动 3 个相互隔离的 Dockerized `codex exec` 进程。每个进程接收全部 5 个 train inputs、对应 train answers 和环境入口，并把完整 package 写到 `scratch/train_skill/fewshot_attempt_<nn>/`，其中 `SKILL.md` 是入口文件。
12. fewshot calibration：使用固定 fewshot prompt 启动 15 个独立 Dockerized `codex exec` runs，每个 test task 3 次；attempt 01/02/03 分别使用 `fewshot_attempt_01/02/03`。主 agent 在 Codex 进程外评分并记录 fewshot `avg@3`。
13. 上下文干净的 reviewer subagent 在生成、验证和校准后做独立 review。
14. 主 agent 根据校准和 review 返工，重跑受影响的 subagents 和校准尝试，直到结构、迁移设计、数据生成、评测和难度目标都通过。

## 禁止总 Builder 脚本

不要用一个 builder 脚本替代上面的多 agent 工作流。

如果 `scratch/build_task_group_001.py` 这类脚本从一个固定 specification 里直接创建以下大部分或全部产物，则不合格：

- `env/`
- 5 个 train task 和 5 个 test task 的全部目录
- solver 可见 prompts 和 payloads
- 隐藏 `notes/notes.md`
- `output/answer.json`
- `eval/`
- `task_group.yaml`
- `scratch/task_group_design.md`
- `scratch/env_blueprint.md`
- `scratch/difficulty_calibration.md`
- `scratch/train_skill/fewshot_attempt_01/SKILL.md`
- `scratch/train_skill/fewshot_attempt_02/SKILL.md`
- `scratch/train_skill/fewshot_attempt_03/SKILL.md`

允许的脚本必须有清晰、狭窄的归属和用途：

- env-builder 可以在 `env/` 下写共享环境数据生成、服务启动、数据库迁移和 manifest 脚本。
- task-builder 可以为自己负责的单个 task 写局部辅助脚本，例如 evaluator 或 task-local 数据转换。
- 主 agent 可以运行集成后的校验脚本，检查路径、schema、evaluator 可复现性和一致性。

设计文档必须先于实现产物形成，不能由同一个生成最终产物的脚本事后回填。每个 `SKILL.md` 必须由隔离的 fewshot skill-generation 进程根据 staged train inputs 和标准答案生成，不能从构造 specification 里预先写好。

## 协作约束

- 主 agent 拥有蓝图质量、task group 一致性和最终集成权。
- env-builder coding subagent 拥有 `env/` 实现和程序化造数代码。
- task-builder subagents 拥有 task 文件生成权。主 agent 不应直接用一个总 builder 脚本生成所有 task prompts、标准答案、notes 和 evaluators。
- 一个同时生成 env、全部任务文件、答案、notes、evaluators、scratch docs 和 skill 的总脚本不能替代 subagent 构造流程。
- 难度校准必须使用 Dockerized `codex exec`、专属 staged work 和 `CODEX_HOME` 目录、`calibration_runtime.md` 中的固定 prompts，并保留原始 traces。主控系统的 subagent runs 不能作为难度证据。
- subagents 的写入范围应清晰，避免互相覆盖。
- subagents 不应获得 notes、标准答案或 eval 以外泄到 solver-facing input 的形式。
- 所有临时设计、solver runs、skill 和 review 记录都放在 `scratch/`。
