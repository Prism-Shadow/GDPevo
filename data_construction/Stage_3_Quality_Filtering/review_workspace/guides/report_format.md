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

## Fields

| Field | Meaning |
| --- | --- |
| `task_group_id` | ID of the task group under review. |
| `script_check` | Scripted structure-check result. |
| `review_votes` | Summary of 6 clean-context reviewer votes; passes when `pass_votes >= 5`. |
| `manual_review` | Quality summary produced by the lead agent from the 6 reviewer conclusions. |
| `leakage_check` | Whether solver-visible prompts, payloads, APIs, answer templates, or public environment surfaces leak answers, full SOPs, scoring points, or solution steps. Drafts, answers, and calibration logs inside `scratch/` do not count as leakage. |
| `business_realism_check` | Whether the task group comes from real business work rather than toy or tutorial data. |
| `environment_design_check` | Whether `env/` is a shared public data and workspace environment, not an answer calculator or task-specific data package. |
| `transfer_design_check` | Whether train/test are both real tasks, and whether test tasks require transferable experience from train without being overly homogeneous. |
| `difficulty_check` | Whether Dockerized fixed-prompt calibration is valid, overall base `avg@3` is about `0.40-0.60`, fewshot gain is about `0.10-0.20`, and most tasks stay below `0.95` rather than approaching a perfect score. |
| `rubric_independence_check` | Whether each task scores at least 4 independently fail-able business questions/aspects, selective perturbations do not make all points move together, and meaningful within-point partial credit is implemented deterministically where appropriate. |
| `eval_design_check` | Whether evaluation scores key business outcomes and avoids point stuffing, free-text friction, or schema friction. |
| `overall` | Final quality review decision. |

Passing Stage 3 requires all of:

- `script_check.pass: true`
- `review_votes.pass: true`
- `manual_review.overall.pass: true`
