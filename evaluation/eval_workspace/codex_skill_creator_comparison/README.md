# Codex Skill-Creator Comparison Workspace

This workspace compares four skill-creator recipes while keeping the Codex
harness, model profile, task group, few-shot evidence, solver prompt, task
environment, evaluators, and attempt counts fixed.

One formal invocation runs one model profile:

```text
gpt5_5_xhigh
deepseek_v4_max_preview
```

The only runtime parameter is `model_profile`. The task group is inferred from
the exactly one directory under `task_group/`. Harness, modes, all four
creators, attempt counts, prompts, limits, scoring, and reporting come from
`configs/experiment.yaml` and are not launch-time options.

For the selected model profile, run these five scored branches:

```text
base
fewshot/codex
fewshot/cc
fewshot/deepagents
fewshot/opencode
```

`base` is one shared control. The four few-shot branches differ only in the
pinned creator bundle staged during skill generation.

## Experiment Question

For a fixed Codex harness and model profile, how does changing only the
skill-creator recipe affect the generated skill and downstream solver score?

This is a portable one-pass comparison. Each creator runs once per generation
attempt inside an isolated Codex process. Interactive review, creator-side
subagents, external eval loops, installation, and post-generation editing are
outside the experiment.

## Formal Run Interface

Use exactly:

```text
model_profile: <gpt5_5_xhigh|deepseek_v4_max_preview>
```

Do not add a task-group selector, raw model string, creator filter, mode filter,
attempt override, or second model profile. Run the two profiles separately.

Provider credentials, endpoint values, and proxy settings are machine runtime
setup. Apply them uniformly to every agent under the selected profile and record
sanitized values in run metadata; do not hard-code them in this reusable
workspace.

## Directories

| Path | Purpose |
| --- | --- |
| `configs/` | Fixed experiment and model profiles |
| `creators/` | Pinned creator bundles, manifests, and the common contract |
| `guides/` | Workflow, prompts, metrics, and report format |
| `task_group/` | The single official task group under evaluation |
| `skills/` | Generated skills by model profile and creator |
| `runs/` | Base and creator-specific solver attempts |
| `original_traces/` | Selected primary Codex session traces |
| `scratch/` | Temporary staging, infrastructure failures, and helper scripts |
| `report/` | Per-model reports and optional side-by-side summaries |

Canonical paths:

```text
skills/<model_profile>/fewshot/<creator>/fewshot_attempt_<nn>/

runs/<model_profile>/base/<test_id>/attempt_<nn>/
runs/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/

original_traces/<model_profile>/skill_generation/<creator>/attempt_<nn>/
original_traces/<model_profile>/base/<test_id>/attempt_<nn>/
original_traces/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/

report/<model_profile>/<task_group_id>.yaml
```

Infrastructure failures are retained under `scratch/infrastructure_failures/`
before the same logical slot is retried with a new opaque UUID. Formal paths
contain only the selected run for each slot.

## Read First

Read these files in order:

1. `EXPERIMENT_SCOPE.md`
2. `CODEX_ORCHESTRATOR.md`
3. `configs/experiment.yaml`
4. The selected file under `configs/models/`
5. `creators/README.md`
6. `creators/COMMON_CONTRACT.md`
7. `guides/workflow.md`
8. `guides/skill_creators.md`
9. `guides/agent_prompts.md`
10. `guides/metric_and_scoring.md`
11. `guides/report_format.md`

## Runtime Setup

Before the first formal attempt, perform the same ordinary setup checks used by
the other evaluation workspaces:

- Resolve the selected profile without placeholders.
- Resolve and record the immutable agent and task image IDs.
- Verify container-local authentication with `codex login status`.
- Verify task-environment health from the agent network.

These checks do not launch a separate model process or require a separate
trace. After they pass, start the first formal generation slot:
`codex/attempt_01`. If a formal attempt later encounters a verified
infrastructure failure, preserve and replace it according to the normal failure
policy.

## Execution Order

Use this fixed round-robin order.

Generation:

```text
attempt_01: codex, cc, deepagents, opencode
attempt_02: codex, cc, deepagents, opencode
attempt_03: codex, cc, deepagents, opencode
```

Solver runs use the same fixed branch order within each attempt and test:

```text
base, fewshot/codex, fewshot/cc, fewshot/deepagents, fewshot/opencode
```

Skip only a few-shot slot whose matching generated skill is invalid or missing,
and record it as `not_runnable`. Do not reorder work in response to scores.

## Attempt Counts

For one task group and one model profile:

- Shared base: 5 test tasks x 3 solver attempts = 15 runs.
- Four creators: 4 x 3 skill-generation attempts = 12 runs.
- Four creator branches: 4 x 5 test tasks x 3 solver attempts = 60 runs.
- Planned total: 87 logical agent runs.

Do not reduce attempt counts in a formal report.

## Preconditions

- All four creator manifests must be pinned, complete, and hash-verified.
- The selected model profile must resolve without placeholders.
- The same model profile is used for generation and solving.
- The task group must contain 5 train tasks and 5 test tasks.
- A formal run never downloads or updates a creator bundle.
- Secrets never enter `/work`, generated skills, traces, or reports.
- The DeepSeek profile remains blocked until its exact model, provider,
  Responses-compatible endpoint, authentication, reasoning setting, and pricing
  are resolved.
