# Review Report Format

Each task group gets one review report:

```text
../reports/<task_group_id>.yaml
```

The report records only the necessary conclusions: script check, 6-vote result, quality review items, and final decision.

## YAML Format

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
  eval_design_check:
    pass: <bool>
    detail: <string>
  overall:
    pass: <bool>
    detail: <string>
```

## Fields

| Field | Meaning |
| --- | --- |
| `task_group_id` | ID of the task group under review. |
| `script_check` | Scripted structure-check result. |
| `review_votes` | Summary of 6 clean-context reviewer votes; passes when `pass_votes >= 5`. |
| `manual_review` | Quality summary produced by the lead agent from the 6 reviewer conclusions. |
| `leakage_check` | Whether solver-visible prompts, payloads, APIs, answer templates, or public environment surfaces leak answers, full SOPs, scoring points, or solution steps. Drafts, answers, and calibration logs inside `scratch/` do not count as leakage. |
| `business_realism_check` | Whether the task group comes from real business work rather than toy or tutorial data. |
| `environment_design_check` | Whether the environment image builds from `env/` alone and agents reach it only over a scoped, non-`--internal` Docker network that preserves model-API egress, without host-port publishing or env/database/truth mounts. |
| `environment_lifecycle_check` | Whether `env.state_mode` is accurate, read-only sharing remains invariant within one capability stage, mutable attempts receive clean environment instances, and `<user_name>`-scoped runtime names cannot collide. |
| `environment_capabilities_check` | Whether each stage exposes only allowed endpoints and `/api/judge` is absent whenever `TASK_ENV_ENABLE_JUDGE=0`, especially during formal tests. |
| `transfer_design_check` | Whether train/test are both real tasks, and whether test tasks require transferable experience from train without being overly homogeneous. |
| `difficulty_check` | Whether Dockerized fixed-prompt calibration is valid, overall base `avg@3` is about `0.40-0.60`, overall fewshot `avg@3` remains roughly below `0.80` with a gain of about `0.10-0.30`, and most tasks stay below `0.95` rather than approaching a perfect score. |
| `eval_design_check` | Whether evaluation scores business outcomes and avoids free-text or schema friction. |
| `overall` | Final quality review decision. |

Passing Stage 3 requires all of:

- `script_check.pass: true`
- `review_votes.pass: true`
- `manual_review.overall.pass: true`
