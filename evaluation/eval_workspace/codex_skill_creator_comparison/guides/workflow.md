# Evaluation Workflow

This workflow runs one model profile for one task group. Codex is both the
isolated skill-generation harness and isolated test-solver harness. The main
orchestrator stages files, launches Docker processes, calls evaluators,
preserves traces, and aggregates reports; it does not solve tasks.

The scored branches are:

```text
base
fewshot/codex
fewshot/cc
fewshot/deepagents
fewshot/opencode
```

## 1. Resolve The Run

Accept only `model_profile` and require exactly one directory under
`task_group/`. Load the selected profile and all fixed values from
`configs/experiment.yaml`.

Verify:

- The orchestrator has not read or searched outside the source boundary defined
  in `CODEX_ORCHESTRATOR.md`.
- The current workspace has a resolved uncommitted `.env` with an approved
  immutable `GDPEVO_AGENT_IMAGE`, exact auth bootstrap path, owner, task port,
  and uniform proxy policy.
- Generator and solver both use Codex and the same resolved profile.
- Provider, authentication, reasoning, and pricing fields are resolved.
- All four creator manifests and bundles pass hash and license checks.
- The task group contains 5 train tasks, 5 test tasks, environment files,
  standard answers, and evaluators.
- No formal output already occupies the selected model-profile paths.

A small helper authored under `scratch/` from the current guides may automate
staging and execution. Do not search for, read, copy, or adapt a runner from
another workspace or previous experiment. Record its hash and freeze its bytes
before the first formal slot. A later helper change requires an infrastructure
restart, not an in-place resume. The helper must invoke
`tools/codex_trace_metrics.py`; it must not contain another trace-metrics
implementation.

## 2. Prepare Docker

Build the task image once and use its immutable image ID throughout the profile.
Resolve only the explicitly configured local `GDPEVO_AGENT_IMAGE`; record its
supplied reference, immutable image ID, Codex CLI version, and host UID:GID. Do
not list old experiment images or select a fallback. In a disposable container,
confirm `/work` is empty and no authentication file, Codex runtime home or
session, task material, generated skill, or previous run output is baked into
the image.

Use the host UID:GID for every agent container. Use a clean container-local
`HOME` and `CODEX_HOME`, minimum read-only authentication bootstrap, and the
same sanitized provider/proxy setup for every creator and solver. Set
`PYTHONDONTWRITEBYTECODE=1` for every agent.

Run `PYTHONDONTWRITEBYTECODE=1 python3
tools/codex_trace_metrics.py --self-test` before writing the run manifest.
Record the tool hash and passing result. This deterministic check is ordinary
runtime validation; it is not a model invocation or scored slot.

Start task environments and networks according to `env.state_mode`. Use
`TASK_ENV_ENABLE_JUDGE=0`. Verify health from the same network before launching
agents.

After the ordinary executable, authentication, image, and environment checks
pass, write:

```text
scratch/run_manifest/<model_profile>.yaml
```

Record one sanitized manifest as described in `CODEX_ORCHESTRATOR.md`, then
proceed directly to the first formal generation slot.

## 3. Fixed Execution Order

Generation order is:

```text
codex/attempt_01
cc/attempt_01
deepagents/attempt_01
opencode/attempt_01
codex/attempt_02
cc/attempt_02
deepagents/attempt_02
opencode/attempt_02
codex/attempt_03
cc/attempt_03
deepagents/attempt_03
opencode/attempt_03
```

After all 12 generation slots are terminal, run solver slots in:

```text
attempt_01 -> test_001..test_005 -> base,codex,cc,deepagents,opencode
attempt_02 -> test_001..test_005 -> base,codex,cc,deepagents,opencode
attempt_03 -> test_001..test_005 -> base,codex,cc,deepagents,opencode
```

This is deterministic and interleaves creators without a random schedule or
seed. Do not change the order after observing outputs or scores.

## 4. Generate Skills

For each creator and attempt, stage:

```text
scratch/skill_generation/<model_profile>/<creator>/attempt_<nn>/
```

Stage only:

- The selected upstream bundle as `creator/`.
- `creators/COMMON_CONTRACT.md` as `creator_contract.md`.
- Complete official inputs for `train_001` through `train_005`, resolving each
  source path from `task_group.yaml` and staging it under
  `train_tasks/<task_id>/input/`.
- Matching standard answers as
  `train_answers/<task_id>/answer.json`, using each task's declared
  `answer_json` path.
- `environment_access.md` containing only the base URL, required credentials,
  and allowed business endpoint names.

Bind-mount each of those five input groups separately with `:ro` over the
attempt-owned writable `/work`. Hash each staged input before and after the
container. Only `skill/` and `contamination_report.txt` are writable generation
outputs. Use `sorted_relative_file_sha256_v1` and
`git_executable_bit_v1` for directory inputs and SHA-256 of exact bytes for
individual file inputs.

Source directory names need not equal task IDs. For example,
`train_tasks/001/input/` declared as `task_id: train_001` must become
`train_tasks/train_001/input/` in `/work`.

Run the fixed Fewshot Skill Generation prompt with a new opaque UUID. Do not
stage test material, notes, evaluators, environment source, old output, another
creator, or judge access.

After exit:

1. Extract and uniquely match the primary trace.
2. Invoke `tools/codex_trace_metrics.py` and record its cumulative token, turn,
   tool-call, model, source, and portability-warning fields. Never parse
   `last_token_usage`.
3. Verify every staged input hash is unchanged.
4. Check contamination and symbolic links.
5. Validate the package without editing it.
6. Calculate content and executable-bit digests.
7. Copy a valid complete package without modification to:

   ```text
   skills/<model_profile>/fewshot/<creator>/fewshot_attempt_<nn>/
   ```

No package, invalid `SKILL.md`, or refusal to finish the one-pass contract is a
logical creator result. Preserve it and do not retry it for quality.

Do not begin solver execution until all 12 generation slots are either valid,
logical failures, or resolved infrastructure failures.

## 5. Run Solvers

### Base

For each test and attempt:

```text
runs/<model_profile>/base/<test_id>/attempt_<nn>/
```

Stage only the current test `input/` and `environment_access.md`. Use the Base
Test Solver prompt. Resolve the source input and evaluator from the selected
entry in `task_group.yaml`, stage its input as `/work/input/`, and keep its
declared `task_id` as the canonical run key. There is one shared base branch,
not one base per creator. Mount both inputs with `:ro`; only `answer.json` and
`contamination_report.txt` are writable.

### Few-Shot Creators

For each creator, test, and attempt:

```text
runs/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/
```

Stage only the current test `input/`, `environment_access.md`, and the complete
matching package as read-only `skill/`. Verify:

```text
solver attempt_<nn> -> same creator's fewshot_attempt_<nn>
```

Mount all three inputs separately with `:ro`, hash them before and after the
attempt, and keep only `answer.json` and `contamination_report.txt` writable.

If that package is invalid or missing, record the solver slot as
`not_runnable`; do not substitute another skill or base. Continue base and
other runnable creator branches in the fixed order.

Every solver receives a new opaque UUID and the fixed prompt. It must not see
train material, creator bundles, other skills, answers, notes, evaluators,
environment source, reports, traces, or judge instructions.

After exit:

1. Preserve and uniquely match the primary trace.
2. Invoke `tools/codex_trace_metrics.py` and require complete cumulative
   metrics.
3. Verify every staged input hash is unchanged.
4. Check contamination.
5. Call the task evaluator from orchestrator context.
6. Write `answer.json`, `score.yaml`, and `run_metadata.yaml`.
7. Populate trace-derived usage and model identity.
8. Remove the agent container and temporary trace extraction directory.

## 6. Failure Handling

An infrastructure failure is a provider/network outage, container startup
failure, task-environment failure, or trace extraction/matching failure caused
by orchestration.

Before retrying the same logical slot:

1. Move its failed artifacts under
   `scratch/infrastructure_failures/<model_profile>/<logical_slot>/<uuid>/`.
2. Recreate the formal attempt directory from clean allowed inputs.
3. Use a new opaque UUID.
4. Keep creator, prompt, model, attempt number, evidence, and timeout unchanged.

Agent timeout, invalid output, refusal, or agent-originated forbidden access is
a logical result. Do not retry it merely to obtain a valid skill or answer.

If the orchestrator staged forbidden material, preserve the failed evidence,
fix only the staging defect, and retry with a new UUID. Never patch a creator or
generated skill during a formal profile.

## 7. Traces And Ownership

Copy exactly one matching primary Codex trace into the canonical
`original_traces/` path. When discovery requires a sessions subtree, use the
streaming `docker cp ... - | tar -x` pattern from
`CODEX_ORCHESTRATOR.md` so host files remain owned by the workspace user.

Do not use `sudo find`, copy a complete runtime home, or retain credentials,
plugins, caches, databases, logs, or stdout as formal traces.

## 8. Score And Report

Base is complete with 15 valid scores. A creator branch is complete with 3 valid
generation packages and 15 matching valid solver scores.

Always write:

```text
report/<model_profile>/<task_group_id>.yaml
```

Represent incomplete branches explicitly. Compute each branch independently,
then report creator lift over the one shared base and pairwise creator
differences when the required branches are complete.

Generation usage remains separate from solver efficiency. Do not include
infrastructure replacements, environment checks, evaluators, or orchestrator
work in scored efficiency.

## 9. Cross-Model Summary

After two separate model-profile reports are final, an optional side-by-side
summary may be written to:

```text
report/comparison/<task_group_id>.yaml
```

Do not pool attempts or claim provider/reasoning differences are caused only by
the model.
