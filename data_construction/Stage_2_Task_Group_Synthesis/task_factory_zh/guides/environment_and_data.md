# 环境与数据

## Env 设计

`env/` 应根据整个 task group 的场景开发，而不是为单个 task 临时拼工具。

环境表示共享的公共数据与办公场景：业务系统、公开目录、CRM 类记录、数据库、文件、dashboard、API 和 Web 页面，可以被多个 task 使用。它应该像一个连贯的工作环境，而不是 API 后面挂着 10 个互相独立的 task 文件夹。

可以包含：

- Web 应用或页面。
- HTTP/API 服务。
- 通过带鉴权的网络查询服务开放给 solver 使用的 SQLite 数据库。不能使用 PostgreSQL 或其他服务端数据库引擎。
- 业务系统数据、生成脚本、初始化脚本和配置文件。
- 与任务相关但不直接给出答案的查询、筛选、状态检查或操作接口。

环境应体现真实生产系统的复杂性，包括足够多的对象、状态、历史记录、噪声数据、相似接口和无关但合理的干扰信息。不要创建一个可以直接返回答案的接口。

solver-facing env 不能按 task 切分。避免 per-task 数据包、per-task 数据库，或 `/api/tasks/<task_id>/data` 这类直接把某条 task 相关数据打包给 solver 的 endpoint。generator 可以保留给构造和 review 使用的隐藏元数据，但 solver-facing services 应暴露共享业务对象和正常办公接口，例如 `/events`、`/crm/accounts`、`/campaign-members`、`/exhibitors`、`/finance/invoices`、SQL tables 或共享文件。

`env/` 本身不是 solver 可见输入。solver、base 和 fewshot agents 只能通过暴露出来的环境入口访问环境，例如浏览器 URL、API base URL，或带鉴权信息的 SQLite 查询服务 URL。如果任务需要访问关系型数据，SQLite 数据库文件应留在主控宿主机上，由运行中的环境服务提供任务所需的 SQL 查询或写入能力。该服务可以通过 HTTP 接收 SQL，也可以提供等价的共享查询接口，但不能成为直接返回任务答案的接口。不能让 solver agents 直接查看或挂载 `env/` 文件、SQLite 数据库文件、schema 或 migration 脚本、生成数据文件、数据库 dump、seed、manifest 或 setup 脚本。

所有 endpoint 的完整清单保存在 `env/endpoints.txt`，每行只写
`METHOD /path`，不写接口介绍。校准或正式评估时，主 agent 将当前运行允许访问
的全部 endpoint 名称写入 `environment_access.md`，同时写入运行时 base URL 和
必要凭据。业务 endpoint 可以提供给 skill-generation 和 test agent；
`/api/judge` 只在 reflect skill generation 时提供；`/health` 和 reset/reseed
endpoint 只供主控使用。

在 solver 可见 task input 中，运行环境 base URL 只能写成
`<TASK_ENV_BASE_URL>`。真实 localhost 地址、私有 IP、公开 host、端口和
setup 命令都不应进入 `prompt.txt` 或 `input/payloads/`；这些值属于实际
运行时 evaluation workspace 的 `.env` 配置。

## 执行架构

环境固定作为 agent 容器之外的宿主机网络服务运行。主 agent 通过
`env/setup.sh` 启动服务，并设置 `TASK_ENV_BIND=0.0.0.0` 和
`TASK_ENV_PORT=<port>`。文件系统隔离保持严格：不能把 `env/`、数据库文件、
seed、manifest、源码或 setup 脚本 staging 或挂载进任何 agent 容器。

校准和正式评估统一使用这一种网络配置：

```text
宿主机环境：TASK_ENV_BIND=0.0.0.0, TASK_ENV_PORT=<port>
agent URL：  http://host.docker.internal:<port>
Docker 参数：--add-host=host.docker.internal:host-gateway
```

每一次 agent `docker run` 都必须带上该 `--add-host` 参数，包括在 Docker
Desktop 上运行时。不要改成某个 task 专用宿主机 IP，也不要再让评估 agent
自行选择 env 容器网络或其他转发方式。

agent 容器中的 `localhost` 或 `127.0.0.1` 指向 agent 容器本身，并不指向
宿主机上的环境 API。除非已明确验证 host-network 配置，否则不能把它当作
环境地址。

任何计分校准或评估开始前，都要用带相同 `--add-host` 参数的临时容器，
通过将要写入 `environment_access.md` 的同一个 URL 做 health check。端口、
实际 `TASK_ENV_BASE_URL` 和容器侧检查结果应记录到 `scratch/`。如果检查失败，
应先修复宿主机监听或转发，不能通过挂载环境文件绕过问题。

监听地址、端口和 agent-facing URL 应可配置，不能在 task 数据中写死具体 IP、
域名或端口。Solver 不负责启动服务；主 agent 负责启动和重置，solver 只收到
运行中的网络入口和必要测试凭据。

有状态环境还必须提供由主 agent 控制、结果确定的 reset 或 reseed 流程，避免
后续 attempt 继承前一次写入。该重置接口不能泄露答案，也不能作为正常业务接口
暴露给 solver。

## 仅限训练阶段的 Judge API

每个 task group 的环境都必须提供 `POST /api/judge`，用于评测 train task 的 candidate answer。请求体格式为 `{"task_id": "train_001", "answer": {...}}`。接口应调用对应 train task 的 evaluator，只返回 `[0, 1]` 范围内的 `score`、布尔值 `correct`，以及该接口仅限训练阶段使用的说明。接口必须拒绝所有 `test_*` task id，且不能返回标准答案、rubric 细节、evaluator 原始输出或其他隐藏材料。

通用实现放在 `env/judge_api.py`，接入 task group 现有的 HTTP 服务，并在 `task_group.yaml` 的 `env.files` 中声明。该接口必须能通过与业务服务相同的容器可访问 base URL 调用。Judge API 是评测控制接口，不是业务数据接口，不能通过它暴露按 task 切分的源数据。

## Env-Builder 对 env 的责任

主 agent 负责 env blueprint、task group 一致性和最终集成。实际 env 实现应由一个上下文干净的 env-builder coding subagent 根据 blueprint 完成。

blueprint 应在实现前写好，并放在：

```text
scratch/env_blueprint.md
```

blueprint 应说明业务系统、公开入口、数据契约、需要的表或 API、完整 endpoint 清单；使用数据库时还要说明 SQLite schema、查询服务协议和鉴权要求；此外还应说明随机种子、生成数据预期、setup 行为、manifest 要求、`TASK_ENV_BIND`/`TASK_ENV_PORT`、固定 host-gateway 路径、health check 和环境重置方式。

env-builder coding subagent 应实现：

- `env/setup.sh` 可以准备或启动需要的环境。
- 服务必须遵循 `TASK_ENV_BIND=0.0.0.0` 和 `TASK_ENV_PORT`；带有固定
  `--add-host=host.docker.internal:host-gateway` 参数的 agent 容器应能通过
  `http://host.docker.internal:<port>` 访问服务。
- 监听地址不能直接当成 agent-facing URL；网络配置完成后，由主 agent 提供
  `TASK_ENV_BASE_URL`。
- Web/API 服务和基于 SQLite 的数据服务于整个 task group。SQLite 查询服务应支持任务需要的读取和写入操作，同时确保 `.db` 文件只留在宿主机环境侧。
- 共享数据模型和公开接口应按业务领域组织，而不是按 task id 组织。
- train/test 使用同一套业务基础设施，形成可迁移的环境经验。
- solver 能通过公开入口访问必要能力，但不能直接看到标准答案、隐藏说明或 `env/` 实现文件。
- 程序化数据生成脚本、固定种子、生成数据和 manifest 都应保留在 `env/` 中。
- `env/endpoints.txt` 使用 `METHOD /path` 完整列出每个可访问 endpoint，不附接口介绍。
- 现有 HTTP 服务通过 `env/judge_api.py` 提供仅限训练阶段使用的 `POST /api/judge`。
- 部署与校准说明中应包含 health endpoint，以及不会暴露隐藏答案的确定性
  reset/reseed 方式。

task-builder subagents 可以通过主 agent 提出额外接口、表或数据需求，但不应各自实现独立 env。

## 程序化造数

大量数据必须通过程序和随机数生成，不应手写生产规模数据。

要求：

- 在 `env/` 中保留数据生成脚本，例如 `generate_data.py`。
- 使用固定随机种子，保证可复现。
- 输出数据应有清单或 manifest，说明生成了哪些文件、表或记录。
- 底层业务数据、大表、数据库、图谱、系统状态和 API 后端数据应放在 `env/` 中，通过环境接口访问。
- 生成数据可以包含供构造和 review 使用的 task-relevance metadata，但 solver-facing 数据应保持为共享办公环境，而不是 per-task slices。
- 数据应包含真实任务中常见的杂质，例如缺失字段、重复记录、过期导出、口径差异、相似实体、冲突状态或无关记录。

payload 中可以放 solver 可见的小型导出、邮件、表格、日志、模板或局部材料。不要把完整底层数据库、API 源码或大规模业务系统数据直接放入 `input/payloads/`。

数据生成脚本不能变成完整 task group builder。`env/` 脚本可以生成共享业务记录、manifest、数据库初始化文件或服务 fixtures，但不能同时生成所有 task prompts、隐藏 notes、标准答案、evaluators、`task_group.yaml`、scratch 设计文档或校准 skill。环境生成必须和任务构造分开。
