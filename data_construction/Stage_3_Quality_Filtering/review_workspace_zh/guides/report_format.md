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
| `environment_design_check` | `env/` 是否是共享公共数据与办公环境，且不是答案计算器或按 task 切分的数据包 |
| `transfer_design_check` | train/test 是否都是正式任务，test 是否能从 train 中迁移经验且不过度同质 |
| `difficulty_check` | 固定 prompt 的 Dockerized 校准是否有效，overall base `avg@3` 是否约为 `0.40-0.60`，fewshot gain 是否约为 `0.10-0.20`，并避免饱和 |
| `rubric_independence_check` | 每个 task 是否评估多个可以独立失败的业务问题或方面，selective perturbation 是否避免所有 points 一起变化，适合拆分的 point 是否实现确定性的 partial credit |
| `eval_design_check` | eval 是否围绕关键业务结果打分，避免碎片字段堆分、自由文本摩擦或 schema 摩擦 |
| `overall` | 最终质量审核结论 |

通过第三阶段审核需要同时满足：

- `script_check.pass: true`
- `review_votes.pass: true`
- `manual_review.overall.pass: true`
