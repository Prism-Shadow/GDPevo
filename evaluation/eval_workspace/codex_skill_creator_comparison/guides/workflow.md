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

- Generator and solver both use Codex and the same resolved profile.
- Provider, authentication, reasoning, and pricing fields are resolved.
- All four creator manifests and bundles pass hash and license checks.
- The task group contains 5 train tasks, 5 test tasks, environment files,
  standard answers, and evaluators.
- No formal output already occupies the selected model-profile paths.

Run the short startup check from `README.md`, then write:

```text
scratch/run_manifest/<model_profile>.yaml
```

Record one sanitized manifest as described in `CODEX_ORCHESTRATOR.md`. A small
helper under `scratch/` may automate staging and execution, but the experiment
does not require building or freezing a separate runner before it starts.

## 2. Prepare Docker

Build the task image once and use its immutable image ID throughout the profile.
Resolve and record the agent image ID, Codex CLI version, and host UID:GID.

Use the host UID:GID for every agent container. Use a clean container-local
`HOME` and `CODEX_HOME`, minimum read-only authentication bootstrap, and the
same sanitized provider/proxy setup for every creator and solver.

Start task environments and networks according to `env.state_mode`. Use
`TASK_ENV_ENABLE_JUDGE=0`. Verify health from the same network before launching
agents.

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
- Complete official inputs for `train_001` through `train_005`.
- Matching standard answers as
  `train_answers/train_<nnn>/answer.json`.
- `environment_access.md` containing only the base URL, required credentials,
  and allowed business endpoint names.

Run the fixed Fewshot Skill Generation prompt with a new opaque UUID. Do not
stage test material, notes, evaluators, environment source, old output, another
creator, or judge access.

After exit:

1. Extract and uniquely match the primary trace.
2. Record tokens, cost, turns, tool calls, duration, model identity, and status.
3. Check contamination and symbolic links.
4. Validate the package without editing it.
5. Calculate content and executable-bit digests.
6. Copy a valid complete package without modification to:

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
Test Solver prompt. There is one shared base branch, not one base per creator.

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

If that package is invalid or missing, record the solver slot as
`not_runnable`; do not substitute another skill or base. Continue base and
other runnable creator branches in the fixed order.

Every solver receives a new opaque UUID and the fixed prompt. It must not see
train material, creator bundles, other skills, answers, notes, evaluators,
environment source, reports, traces, or judge instructions.

After exit:

1. Preserve and uniquely match the primary trace.
2. Check contamination.
3. Call the task evaluator from orchestrator context.
4. Write `answer.json`, `score.yaml`, and `run_metadata.yaml`.
5. Populate trace-derived usage and model identity.
6. Remove the agent container and temporary trace extraction directory.

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

Generation usage remains separate from solver efficiency. Do not include the
startup check, infrastructure replacements, environment checks, evaluators, or
orchestrator work in scored efficiency.

## 9. Cross-Model Summary

After two separate model-profile reports are final, an optional side-by-side
summary may be written to:

```text
report/comparison/<task_group_id>.yaml
```

Do not pool attempts or claim provider/reasoning differences are caused only by
the model.
