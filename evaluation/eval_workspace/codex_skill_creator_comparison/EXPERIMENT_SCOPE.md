# Experiment Scope

## Formal Run Interface

A formal invocation supplies exactly one runtime parameter:

```text
model_profile: gpt5_5_xhigh | deepseek_v4_max_preview
```

The selected ID must already exist under `configs/models/`. Infer the task group
from the exactly one directory under `task_group/`. Read the complete creator
set, modes, harness, attempt counts, prompts, execution policy, and reporting
policy from `configs/experiment.yaml`; none may be filtered or overridden at
launch. In particular, every formal invocation runs one shared `base` plus all
four configured creator branches. Running both model profiles requires two
separate formal invocations.

Provider endpoint/authentication values needed to resolve a committed profile
are preflight setup inputs, not additional formal-run parameters. They must be
resolved and frozen before the first scheduled attempt.

## Fixed Factors

Within one model-profile report, keep these factors fixed:

- Harness: `codex` for both skill generation and test solving.
- Model profile: the same profile for generator and solver.
- Reasoning configuration.
- Task group and all five test tasks.
- Five few-shot train inputs and five matching standard answers.
- Task environment, endpoint exposure, evaluators, solver prompt, and attempt
  count.
- Docker isolation, runtime permissions, and trace collection rules.
- Wall-clock limits, retry policy, and model-side output limit semantics.

## Experimental Factor

The only factor changed across the four few-shot branches is:

```text
skill_creator: codex | cc | deepagents | opencode
```

The four creators receive the same staged train material and the same common
creator contract. Each creator receives its own pinned upstream bundle.

The creator name is orchestration metadata only. Do not expose it in the
generation or solver prompt, run token, environment variables, or staged paths.
Within one model profile, the few-shot prompt bytes are identical across creator
branches apart from a fresh opaque UUID. The selected creator bundle is the only
creator-specific staged input.

## Scored Branches

For each model profile:

```text
base
fewshot/codex
fewshot/cc
fewshot/deepagents
fewshot/opencode
```

`base` has no creator and generates no skill. It is one shared control for all
four creator comparisons under that model profile.

## Model Profiles

The workspace contains two intended profiles:

```text
gpt5_5_xhigh
deepseek_v4_max_preview
```

Treat model profiles as separate strata. Rank and compare creators within a
profile. A cross-model report may show results side by side, but must not claim
that model differences are caused only by the model when provider, protocol,
authentication, or reasoning semantics also differ.

Store generator and solver fields separately in metadata even when they are
equal:

```yaml
generator_harness: codex
solver_harness: codex
generator_model: <resolved model id>
solver_model: <resolved model id>
```

## Portable One-Pass Creator Policy

This experiment tests creator instruction bundles as portable one-pass recipes
inside Codex. The generation process may inspect its pinned creator bundle and
run bundled deterministic validation scripts, but it must not:

- Ask or wait for human feedback.
- Spawn any subagent or make any secondary model call, including creator-side
  benchmark, grader, comparator, or baseline agents.
- Use test tasks or evaluators as creator eval data.
- Start an HTML review server or require UI review.
- Optimize activation descriptions through repeated model calls.
- Install the generated skill into a user or project skill registry.
- Revise the skill after the isolated generation run ends.

These restrictions intentionally exclude native full-workflow behavior from
some creator ecosystems. The report must describe the experiment as a portable
one-pass comparison, not a native-harness best-case comparison.

## Creator Adaptation Boundary

Keep the upstream creator bundle byte-preserved under its creator directory.
Apply compatibility through the same `creators/COMMON_CONTRACT.md` staged for
every creator. Do not add creator-specific task hints.

Allowed mechanical adaptation:

- Point the generator to the staged creator bundle.
- Require output at `/work/skill/` with `/work/skill/SKILL.md` as entrypoint.
- State that the target consumer is a Codex test solver.
- Replace unavailable installation or UI expectations with the common one-pass
  output contract.
- Permit the creator to use its bundled local scripts and references.

Forbidden adaptation:

- Add domain rules learned from the train answers to one creator only.
- Rewrite or improve the generated skill after the creator run.
- Remove inconvenient creator output before scoring without recording it.
- Give different train evidence, endpoints, token budget, or execution tools to
  different creators.

## Attempt Mapping

For each creator, generate three independent skills:

```text
fewshot_attempt_01
fewshot_attempt_02
fewshot_attempt_03
```

The solver mapping is fixed:

```text
solver attempt_01 uses creator skill attempt_01
solver attempt_02 uses creator skill attempt_02
solver attempt_03 uses creator skill attempt_03
```

This `@3` design measures end-to-end creator-plus-solver pipeline variation. It
does not separately identify between-skill and within-solver variance. A future
nested design may rerun each generated skill multiple times, but those results
must use a different metric name and report schema.

## Execution Order And Limits

Use the limits and retry policy in `configs/experiment.yaml` unchanged for every
creator within a model profile. `codex_profile_default` means no creator-specific
output-token override is added; the resolved Codex/model-profile default must be
captured during preflight. Apply the wall timeout outside `codex exec` and record
the observed duration and timeout status for every physical run.

Before execution, create a seeded randomized schedule that interleaves the 12
creator-generation runs. Also precompute one solver schedule interleaving all 15
shared-base runs and all 60 creator-specific few-shot runs. After generation,
execute every runnable solver entry in that fixed 75-entry order; entries for an
incomplete creator are marked not runnable rather than silently removed. Save
the seed and both fully expanded orders in the resolved run manifest. This
reduces confounding from provider drift or preview-model changes. Do not change
the schedule in response to intermediate scores.

Only verified infrastructure failures may receive a replacement physical run.
A confirmed staging/isolation leak is infrastructure; an agent-originated access
violation with correct staging is logical. Logical creator or solver failures
remain experimental outcomes, make the affected branch incomplete, and must not
be retried merely to obtain a valid output.

## Formal Versus Smoke Runs

A formal run uses all five test tasks and all three attempts. A smoke run may
use fewer attempts only to verify provider, creator, Docker, and trace
compatibility. Smoke artifacts must be isolated under `scratch/smoke/` and must
not enter formal reports.
