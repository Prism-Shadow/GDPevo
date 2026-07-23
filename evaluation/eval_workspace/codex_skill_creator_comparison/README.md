# Codex Skill-Creator Comparison Workspace

This workspace compares four skill-creator recipes while keeping the evaluation
harness, model profile, task group, few-shot evidence, solver prompt, task
environment, evaluators, and attempt counts fixed.

It supports two model profiles from one shared workflow:

```text
gpt5_5_xhigh
deepseek_v4_max_preview
```

One formal invocation accepts exactly one runtime parameter: `model_profile`.
It must be one of the two IDs above. The task group is inferred from the exactly
one directory staged under `task_group/`. Harness, modes, all four creators,
attempt counts, prompts, limits, scheduling, scoring, and reporting are fixed by
`configs/experiment.yaml` and cannot be overridden at launch.

For each model profile, run exactly five scored branches:

```text
base
fewshot/codex
fewshot/cc
fewshot/deepagents
fewshot/opencode
```

`base` is shared within a model profile. Do not duplicate or rerun it once per
creator. The four creator branches differ only in the creator bundle used by
the few-shot skill-generation process.

This workspace evaluates one task group at a time. Do not modify the task group
under evaluation. If it is invalid, record the risk and return it to an earlier
data stage.

## Experiment Question

For a fixed Codex harness and a fixed model profile, how does replacing only the
skill-creator recipe change the quality and efficiency of the generated
few-shot skill and the downstream solver score?

The primary experiment is a portable one-pass comparison. Each creator runs in
one isolated Codex generation process. Creator-side human review, subagent
benchmarks, activation-description optimization, installation, and iterative
eval loops are outside this experiment. This keeps the generation boundary and
compute shape comparable across creator recipes.

Creator names remain outside agent-visible prompts and paths. Within one model
profile, creator runs use the same common contract, prompt, execution limits,
retry policy, and seeded interleaved schedule; only the pinned creator bundle
changes.

## Formal Run Interface

The only valid formal invocation shape is:

```text
model_profile: <gpt5_5_xhigh|deepseek_v4_max_preview>
```

Do not accept a task-group selector, model string, creator filter, mode filter,
attempt override, or a request to run both profiles in one formal invocation.
Every invocation discovers the one staged task group, resolves the selected
profile, and runs the complete fixed branch set shown above. A cross-model file
is only a later side-by-side aggregation of two separately invoked reports.
Provider/authentication values used to resolve a profile are preflight setup,
not launch parameters; freeze them before the formal schedule starts.

## Directories

| Path | Purpose |
| --- | --- |
| `configs/` | Experiment scope and model profiles |
| `creators/` | Pinned upstream creator bundles, manifests, and the common adaptation contract |
| `guides/` | Workflow, creator rules, fixed prompts, metrics, and report format |
| `task_group/` | The single official task group under evaluation |
| `skills/` | Generated skills organized by model profile and creator |
| `runs/` | Shared base and creator-specific few-shot solver attempts |
| `original_traces/` | Copied primary Codex session JSONL files |
| `scratch/` | Staging, runtime manifests, temporary checks, and aggregation scripts |
| `report/` | Per-model reports and optional cross-model side-by-side summaries |

Canonical artifact paths are:

```text
skills/<model_profile>/fewshot/<creator>/fewshot_attempt_<nn>/SKILL.md

runs/<model_profile>/base/<test_id>/attempt_<nn>/
runs/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/

original_traces/<model_profile>/skill_generation/<creator>/attempt_<nn>/
original_traces/<model_profile>/base/<test_id>/attempt_<nn>/
original_traces/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/

report/<model_profile>/<task_group_id>.yaml
report/comparison/<task_group_id>.yaml
```

Each logical generation or solver attempt stores immutable physical runs under
`attempt_<nn>/physical_runs/<opaque_agent_run_id>/`. A `selected_run.yaml`
pointer identifies the sole physical run used in aggregation; failed
infrastructure runs are retained rather than overwritten.

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

## Launch Prompt

Run one model profile at a time. No other experiment option belongs in the
launch prompt:

```text
Please run the formal evaluation in this workspace.
Model profile: <gpt5_5_xhigh|deepseek_v4_max_preview>.
```

The orchestrator must reject extra runtime overrides rather than interpreting
them. To obtain both model results, invoke the workspace twice, once per profile,
then aggregate the two finalized reports without rerunning either experiment.

## Important Preconditions

- Every creator manifest must have a pinned immutable revision and verified
  bundle hash before formal runs.
- All four configured creators are mandatory; a subset is not a formal run.
- Every creator bundle must have `SKILL.md` at its bundle root.
- The selected model profile must have no unresolved values.
- The DeepSeek profile remains intentionally blocked until its exact model ID,
  Codex custom provider, Responses-compatible endpoint, authentication, and
  reasoning setting are confirmed.
- A formal run never downloads or updates creator bundles.
- Secrets belong only in ignored `.env` or minimum runtime bootstrap files;
  never commit them or stage them under `/work`.

## Attempt Counts

For one task group and one model profile:

- Shared base: 5 test tasks x 3 solver attempts = 15 solver runs.
- Each creator: 3 skill-generation runs and 5 test tasks x 3 solver attempts.
- Four creators: 12 skill-generation runs and 60 few-shot solver runs.
- Planned total: 87 selected logical agent runs per model profile. Verified
  infrastructure replacements may increase the retained physical-run count.

Do not reduce attempt counts for a formal report. Smaller smoke tests must be
marked `smoke_test` and must not be published as `acc@3` results.
