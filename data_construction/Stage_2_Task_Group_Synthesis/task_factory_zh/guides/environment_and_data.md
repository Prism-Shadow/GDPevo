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

`env/` 本身不是 solver 可见输入。solver、base 和 fewshot agents 只能通过暴露出来的环境入口访问环境，例如浏览器 URL、API base URL，或带鉴权信息的 SQLite 查询服务 URL。如果任务需要访问关系型数据，SQLite 数据库文件应留在环境容器内部，由运行中的环境服务提供任务所需的 SQL 查询或写入能力。该服务可以通过 HTTP 接收 SQL，也可以提供等价的共享查询接口，但不能成为直接返回任务答案的接口。不能让 solver agents 直接查看或挂载 `env/` 文件、SQLite 数据库文件、schema 或 migration 脚本、生成数据文件、数据库 dump、seed、manifest 或 setup 脚本。

所有 endpoint 的完整清单保存在 `env/endpoints.txt`，每行只写
`METHOD /path`，不写接口介绍。校准或正式评估时，主 agent 将当前运行允许访问
的全部 endpoint 名称写入 `environment_access.md`，同时写入运行时 base URL 和
必要凭据。业务 endpoint 可以提供给 skill-generation 和 test agent；
`/api/judge` 只在 reflect skill generation 时提供；`/health` 和 reset/reseed
endpoint 只供主控使用。

在 solver 可见 task input 中，运行环境 base URL 只能写成
`<TASK_ENV_BASE_URL>`。真实 localhost 地址、私有 IP、公开 host、端口和
setup 命令都不应进入 `prompt.txt` 或 `input/payloads/`；这些值由实际运行时
主控根据 Docker network 写入 `environment_access.md`。

## 执行架构

环境通过 `env/Dockerfile` 构建，构建上下文只能是 `env/`。环境容器与每个
skill-generation、calibration 或 solver 容器都接入由主控创建的独立 Docker
bridge network，环境端口不映射到宿主机。环境源码、数据库、seed、manifest、
`.env` 和 setup 脚本只存在于环境镜像或仅供环境容器使用的挂载中，不能 staging、
复制或挂载进 agent 容器。

必须创建普通的 user-defined bridge network，不能使用 `--internal` network。
保留 Docker 默认的出站 NAT 和 DNS，使 agent 容器能够访问模型 API。实现这种
出站访问不需要、也不能通过把任务环境端口映射到宿主机来完成。

校准和正式评估统一使用以下容器内访问方式：

```text
端口规则：    9000 + task group 数字编号
环境监听：    TASK_ENV_BIND=0.0.0.0, TASK_ENV_PORT=<计算结果>
network 别名：task-env
agent URL：   http://task-env:<计算结果>/
宿主机端口：  不映射
```

Docker 只会在当前 network 内解析 `task-env`。因此，同一台 Docker 主机上的
不同用户、task group、阶段和 attempt 可以安全复用相同的别名和容器内端口。
agent 容器中的 `localhost` 仍然只指向它自己。正式运行不能使用
`host.docker.internal`、host network、公开宿主机地址或 `-p`/`ports`。

所有名称由可信主控生成，不能交给被测 agent 选择。主控从
`GDPEVO_RUN_OWNER` 或当前用户名生成 owner slug，并将其转成小写
`[a-z0-9_-]`；每个 project、network 和容器名称还必须包含 task group 编号、
权限阶段、必要时的 condition/task/attempt，以及 8 位随机 run suffix。例如：

```text
gdp-<user_name>-013-test-few-t001-a01-7f3a91c2-net
gdp-<user_name>-013-test-few-t001-a01-7f3a91c2-env
gdp-<user_name>-013-test-few-t001-a01-7f3a91c2-agent
```

环境容器的真实名称必须唯一；`task-env` 只能作为当前 network 内的别名，不能
写成全局固定的 `container_name`。

agent 启动前，主控必须用同一 network 上的临时容器，通过将要写入
`environment_access.md` 的 `http://task-env:<port>/` 做 health check，并在
`scratch/` 中记录 owner、run suffix、state mode、阶段、network、环境容器名、
容器内端口、base URL、镜像标识和检查结果。环境容器可以通过仅供自身使用的
环境变量、secret 或挂载获取私有配置；agent 只能收到 base URL、允许访问的
endpoint 名称和任务本身允许公开的凭据。

### 环境生命周期

`task_group.yaml` 必须把 `env.state_mode` 明确写成 `read_only` 或 `mutable`，
运行时不能猜测。

- `read_only`：同一个权限阶段的多个并发 attempt 可以共用一个环境容器；业务
  endpoint、session、cache、鉴权状态、日志、限流和 judge 记录都不能产生会被
  后续 attempt 观察到的变化。
- `mutable`：每个 attempt 都使用新的 network、环境容器和可写层。只要名称和
  network 唯一，多个 attempt 可以并发运行；不同 attempt 不能共享数据库 volume。

即使环境只读，不同权限阶段也必须分开。base、fewshot、self 和正式 test 使用
关闭 judge 的环境实例；reflect skill generation 使用单独的环境实例，并设置
`TASK_ENV_ENABLE_JUDGE=1`。正式 test 设置 `TASK_ENV_ENABLE_JUDGE=0`，此时
`POST /api/judge` 必须没有注册或返回 not found。calibration 同样使用关闭 judge
的实例。只有确定共享当前阶段环境的所有 agent 都结束后，主控才能删除 network。

## 仅限训练阶段的 Judge API

每个 task group 的环境都必须提供 `POST /api/judge`，用于评测 train task 的 candidate answer。请求体格式为 `{"task_id": "train_001", "answer": {...}}`。接口应调用对应 train task 的 evaluator，只返回 `[0, 1]` 范围内的 `score`、布尔值 `correct`，以及该接口仅限训练阶段使用的说明。接口必须拒绝所有 `test_*` task id，且不能返回标准答案、rubric 细节、evaluator 原始输出或其他隐藏材料。

通用实现放在 `env/judge_api.py`，接入 task group 现有的 HTTP 服务，并在 `task_group.yaml` 的 `env.files` 中声明。该接口必须能通过与业务服务相同的容器可访问 base URL 调用。Judge API 是评测控制接口，不是业务数据接口，不能通过它暴露按 task 切分的源数据。

## Env-Builder 对 env 的责任

主 agent 负责 env blueprint、task group 一致性和最终集成。实际 env 实现应由一个上下文干净的 env-builder coding subagent 根据 blueprint 完成。

blueprint 应在实现前写好，并放在：

```text
scratch/env_blueprint.md
```

blueprint 应说明业务系统、公开入口、数据契约、需要的表或 API、完整 endpoint 清单；使用数据库时还要说明 SQLite schema、查询服务协议和鉴权要求；此外还应说明随机种子、生成数据预期、setup 行为、manifest 要求、`TASK_ENV_BIND`/`TASK_ENV_PORT`、`env.state_mode`、环境镜像、仅限 Docker network 的访问路径、health check 和环境重置方式。

env-builder coding subagent 应实现：

- `env/Dockerfile` 只能以 `env/` 为上下文构建完整环境镜像，`env/setup.sh`
  负责在镜像内准备或启动需要的环境。
- 服务必须遵循 `TASK_ENV_BIND=0.0.0.0` 和 `TASK_ENV_PORT`；环境容器与 agent
  容器接入主控创建的 network 后，agent 应能通过
  `http://task-env:<port>/` 访问服务。
- 监听地址不能直接当成 agent-facing URL；网络配置完成后，由主 agent 提供
  `TASK_ENV_BASE_URL`。
- Web/API 服务和基于 SQLite 的数据服务于整个 task group。SQLite 查询服务应
  支持任务需要的读取和写入操作，同时确保 `.db` 文件只存在于环境容器内部，
  不进入任何 agent 挂载。
- 共享数据模型和公开接口应按业务领域组织，而不是按 task id 组织。
- train/test 使用同一套业务基础设施，形成可迁移的环境经验。
- solver 能通过公开入口访问必要能力，但不能直接看到标准答案、隐藏说明或 `env/` 实现文件。
- 程序化数据生成脚本、固定种子、生成数据和 manifest 都应保留在 `env/` 中。
- `env/endpoints.txt` 使用 `METHOD /path` 完整列出每个可访问 endpoint，不附接口介绍。
- 现有 HTTP 服务通过 `env/judge_api.py` 提供仅限训练阶段使用的 `POST /api/judge`。
- 服务必须遵循 `TASK_ENV_ENABLE_JUDGE`：只有值为 `1` 时才注册
  `/api/judge`；judge 关闭的 calibration 和 test 实例不能暴露该路径。
- `task_group.yaml` 必须正确声明 `env.state_mode`；mutable 环境在每个新容器中
  初始化干净且确定的状态，read-only 环境在并发请求下保持不变。
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
