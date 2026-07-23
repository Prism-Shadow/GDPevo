# Skill-Creator Conditions

This workspace has one shared `base` and four creator-specific `fewshot`
branches for each model profile.

## Shared Base

No skill is generated. The base solver sees only:

- The current test task `input/`.
- The container-visible task-environment entrypoint and allowed business
  endpoints.

The base solver must not see train tasks, generated skills, any creator bundle,
test answers, notes, evaluator files, environment source, previous runs, or
judge instructions.

Run base exactly once per model profile. Reuse that same aggregated base in all
four within-profile creator comparisons.

## Common Fewshot Evidence

Every creator generation attempt sees exactly:

- Official `input/` for `train_001` through `train_005`.
- Matching standard `answer.json` for those five train tasks.
- The container-visible task-environment entrypoint and the same allowed
  business endpoint names.
- The same `creators/COMMON_CONTRACT.md` staged as `creator_contract.md`.
- Exactly one pinned upstream creator bundle staged as `creator/`.

The generator must not see test tasks or answers, notes, evaluator files,
environment source, prior runs, another creator bundle, or judge instructions.

## Creator Branches

The branch IDs are stable report and directory keys:

```text
codex
cc
deepagents
opencode
```

For each branch, generate three independent packages:

```text
skills/<model_profile>/fewshot/<creator>/fewshot_attempt_01/SKILL.md
skills/<model_profile>/fewshot/<creator>/fewshot_attempt_02/SKILL.md
skills/<model_profile>/fewshot/<creator>/fewshot_attempt_03/SKILL.md
```

Each attempt starts from a new isolated runtime context and the same immutable
creator bundle. A generator must not inspect another attempt's output.

## Upstream Preservation

The creator's upstream directory is an experimental input. Verify and record
its immutable revision and content hashes before staging. Do not:

- Edit upstream creator files in place.
- Drop referenced scripts, references, agents, templates, or assets.
- Upgrade a creator partway through a model profile or task-group run.
- Resolve moving branches such as `main` during a formal run.
- Make creator-specific prompt additions that reveal domain rules.

If an upstream creator expects an interactive or native-harness workflow that
conflicts with the portable one-pass contract, the common contract wins. Record
the incompatibility in generation metadata; do not privately patch that creator
for the current attempt.

## Generated Skill Contract

Every valid generated package must:

- Be rooted at `skill/` during generation.
- Contain `skill/SKILL.md` with parseable YAML frontmatter and Markdown body.
- Keep all supporting files within `skill/` and use relative paths.
- Contain no symbolic links.
- Be consumable by the explicit Codex test-solver prompt.
- Contain reusable procedures rather than copied train answer records.
- Avoid test-time judge instructions and creator-only runtime requirements.

Static validation reports are observational. They may identify invalid
frontmatter, missing references, unsupported absolute paths, or unavailable
tool assumptions, but must not repair the package.

After validation, calculate the complete generated-package digest with the same
`sorted_relative_file_sha256_v1` algorithm defined in `creators/README.md`.
Also calculate its Git-stable executable-bit digest with
`git_executable_bit_v1`. Record both in generation metadata and solver metadata.
Recompute both immediately before and after every solver run; a mismatch
invalidates the run rather than permitting a repair.

## Solver Exposure

For creator `<creator>` and solver attempt `<nn>`, stage only:

- Current test task `input/`.
- The task-environment access file.
- The complete package from the same creator and attempt number as `skill/`.

The mapping is mandatory:

```text
fewshot/codex/attempt_02      -> codex skill attempt_02
fewshot/cc/attempt_02         -> cc skill attempt_02
fewshot/deepagents/attempt_02 -> deepagents skill attempt_02
fewshot/opencode/attempt_02   -> opencode skill attempt_02
```

Never use one creator's generated skill in another creator's branch.

## Quality Observations

In addition to downstream score, record for each generation attempt:

- Whether a complete package was produced.
- Whether `SKILL.md` and referenced local files validate.
- Generated file count and byte size.
- Any target-runtime portability warning.
- Any attempted interactive, installation, UI, subagent, or external-eval step
  blocked by the common one-pass contract.
- Generation tokens, cost, turns, tool calls, and duration when available.

These observations help explain score differences but do not replace task
evaluator scores.
