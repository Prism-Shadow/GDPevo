# Experiment Scope

## Formal Invocation

A formal invocation supplies one value:

```text
model_profile: gpt5_5_xhigh | deepseek_v4_max_preview
```

Infer the task group from the exactly one directory under `task_group/`. Load
the harness, modes, creator set, attempt counts, prompts, limits, and reporting
rules from `configs/experiment.yaml`. Do not accept per-run overrides.

## Fixed Factors

Within one model-profile report, keep fixed:

- Codex as both generator and solver harness.
- The resolved model, provider, and reasoning configuration.
- The task group, five train examples, and five test tasks.
- Task environment, endpoint exposure, evaluators, prompts, and timeouts.
- Docker isolation, authentication method, agent image, and task image.
- Attempt counts and fixed round-robin execution order.

## Experimental Factor

Only the generation-time creator bundle changes:

```text
codex
cc
deepagents
opencode
```

Each generation attempt receives the same train inputs, train answers, common
contract, task-environment access, prompt, model settings, and runtime limits.
It receives exactly one pinned creator bundle at `/work/creator/`.

Keep creator identity in orchestrator metadata. Do not add creator-specific
domain hints or expose another bundle inside `/work`.

## Scored Branches

```text
base
fewshot/codex
fewshot/cc
fewshot/deepagents
fewshot/opencode
```

`base` has no creator and no generated skill. It is shared by all four
within-profile comparisons.

## Portable One-Pass Policy

The generator uses the selected creator as a portable one-pass recipe inside
Codex. It may read bundled files and run deterministic local validation scripts.
It must not:

- Ask or wait for human feedback.
- Spawn creator-side subagents or make secondary model calls.
- Run external benchmarks, graders, comparators, or activation optimization.
- Use test tasks, test answers, notes, or evaluators.
- Start review servers or install the generated skill.
- Revise the generated package after the isolated process ends.

The unchanged `creators/COMMON_CONTRACT.md` applies equally to all four bundles.
If a creator's native workflow conflicts with that contract, record the
friction as an experiment observation; do not patch only that creator.

## Attempt Mapping

Generate three independent packages per creator:

```text
fewshot_attempt_01
fewshot_attempt_02
fewshot_attempt_03
```

Mapping is fixed:

```text
solver attempt_01 -> creator skill attempt_01
solver attempt_02 -> creator skill attempt_02
solver attempt_03 -> creator skill attempt_03
```

Never substitute base, another creator, or another attempt when a package is
invalid or missing.

## Fixed Order

Run generation round by round:

```text
codex/01, cc/01, deepagents/01, opencode/01
codex/02, cc/02, deepagents/02, opencode/02
codex/03, cc/03, deepagents/03, opencode/03
```

After all 12 generation slots reach a terminal state, run solver slots in fixed
`attempt -> test -> branch` order. Within each test and attempt, use:

```text
base, codex, cc, deepagents, opencode
```

A missing creator package makes only its matching few-shot solver slot
`not_runnable`. Base and other runnable branches continue.

## Failures

Retry only verified infrastructure failures such as provider/network
unavailability, container startup failure, or trace extraction failure. Before
retrying, move the failed artifacts to:

```text
scratch/infrastructure_failures/<model_profile>/<logical_slot>/<agent_run_id>/
```

Then create a clean formal attempt directory and use a new opaque UUID. Do not
change its creator, prompt, model, evidence, or timeout.

No package, invalid output, timeout consumed by the agent, refusal to follow the
common contract, or agent-originated boundary violation is a logical result and
is not retried merely to obtain success.

## Model Separation

Compute metrics within one resolved model profile. A later report may display
the two profiles side by side but must not pool their attempts, pricing, or token
accounting.
