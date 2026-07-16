# 审核报告格式

每个 task group 对应一份审核报告：

```text
../reports/<task_group_id>.yaml
```

报告只记录必要结论：脚本检查、6 票结果、质量审核项和总判断。

## YAML 格式

```yaml
task_group_id: <string>

script_check:
  pass: <bool>
  detail: <string>

review_votes:
  pass: <bool>
  pass_votes: <int>
  fail_votes: <int>
  detail: <string>

manual_review:
  leakage_check:
    pass: <bool>
    detail: <string>
  business_realism_check:
    pass: <bool>
    detail: <string>
  environment_design_check:
    pass: <bool>
    detail: <string>
  environment_lifecycle_check:
    pass: <bool>
    detail: <string>
  environment_capabilities_check:
    pass: <bool>
    detail: <string>
  transfer_design_check:
    pass: <bool>
    detail: <string>
  difficulty_check:
    pass: <bool>
    detail: <string>
  rubric_independence_check:
    pass: <bool>
    detail: <string>
  eval_design_check:
    pass: <bool>
    detail: <string>
  overall:
    pass: <bool>
    detail: <string>
```

## 字段说明

| 字段 | 含义 |
| --- | --- |
| `task_group_id` | 被审核的 task group ID |
| `script_check` | 脚本化结构检查结果 |
| `review_votes` | 6 个上下文干净 reviewer 的投票汇总；`pass_votes >= 5` 时通过 |
| `manual_review` | 主 agent 根据 6 个 reviewer 结论汇总出的质量检查 |
| `leakage_check` | 正式 task group 的 solver-visible prompt、payload、API、answer template 是否泄露答案、完整 SOP、评分点或解题步骤；`scratch/` 中的生产草稿、答案和校准记录不算泄露 |
| `business_realism_check` | task group 是否来自真实业务问题，而不是玩具数据或教学题 |
| `environment_design_check` | 环境镜像是否只从 `env/` 构建，agent 是否只通过保留模型 API 出站能力的非 `--internal` Docker network 访问环境，且没有映射宿主机端口或挂载 env、数据库与 truth |
| `environment_lifecycle_check` | `env.state_mode` 是否准确，read-only 环境是否只在同一权限阶段安全共享，mutable attempt 是否获得干净环境，包含 `<user_name>` 的运行时名称是否避免并发重名 |
| `environment_capabilities_check` | 每个阶段是否只开放允许的 endpoint，尤其是 `TASK_ENV_ENABLE_JUDGE=0` 时 `/api/judge` 是否不可访问 |
| `transfer_design_check` | train/test 是否都是正式任务，test 是否能从 train 中迁移经验且不过度同质 |
| `difficulty_check` | 固定 prompt 的 Dockerized 校准是否有效，overall base `avg@3` 是否约为 `0.40-0.60`，overall fewshot `avg@3` 是否大致低于 `0.80` 且 gain 约为 `0.10-0.30`，并避免大部分任务达到 `0.95` 以上或接近满分 |
| `rubric_independence_check` | 每个 task 是否评估至少 4 个语义上不同的业务结果；是否存在换一种说法却重复奖励同一个判断或答案事实的 points；每个 point 是否在完整满足要求时获得该点全部分值，否则得 `0` 分 |
| `eval_design_check` | eval 是否围绕关键业务结果打分，避免碎片字段堆分、自由文本摩擦或 schema 摩擦 |
| `overall` | 最终质量审核结论 |

通过第三阶段审核需要同时满足：

- `script_check.pass: true`
- `review_votes.pass: true`
- `manual_review.overall.pass: true`
