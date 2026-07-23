# Report Format

Write one formal YAML report per model profile:

```text
report/<model_profile>/<task_group_id>.yaml
```

## Per-Model YAML Shape

```yaml
experiment_id: codex_skill_creator_comparison
task_group_id: <task_group_id>
scenario_id: <scenario_id>
model_profile: <model_profile_id>
harness: codex
status: <complete|incomplete>

formal_run_interface:
  accepted_runtime_parameters:
    model_profile: <model_profile_id>
  task_group_source: exactly_one_staged_directory
  creator_set_source: frozen_experiment_config
  fixed_modes: [base, fewshot]
  fixed_creators: [codex, cc, deepagents, opencode]
  runtime_overrides_accepted: false

model_config:
  generator_harness: codex
  solver_harness: codex
  generator_model: <resolved model id>
  solver_model: <resolved model id>
  generator_reasoning_effort: <resolved value>
  solver_reasoning_effort: <resolved value>
  generator_provider_id: <resolved provider id>
  solver_provider_id: <resolved provider id>
  provider_wire_api: responses
  observed_model_identity: <trace/provider identity or null>
  identity_consistent_across_selected_runs: <bool>

pricing:
  basis: <source or contract>
  uncached_input_usd_per_million: <float or null>
  cached_input_usd_per_million: <float or null>
  output_usd_per_million: <float or null>

base:
  status: <complete|incomplete>
  incomplete_reason: <string or null>
  shared_across_creators: true
  overall_acc_at_3: <float or null>
  overall_std_at_3: <float or null>
  efficiency:
    input_tokens_avg_3: <float or null>
    cached_input_tokens_avg_3: <float or null>
    output_tokens_avg_3: <float or null>
    reasoning_output_tokens_avg_3: <float or null>
    cost_usd_avg_3: <float or null>
    rounds_avg_3: <float or null>
    tool_calls_avg_3: <float or null>
  tasks:
    test_001:
      status: <complete|incomplete>
      incomplete_reason: <string or null>
      scores: [<float or null>, <float or null>, <float or null>]
      acc_at_3: <float or null>
      std_at_3: <float or null>
      input_tokens_avg_3: <float or null>
      cached_input_tokens_avg_3: <float or null>
      output_tokens_avg_3: <float or null>
      reasoning_output_tokens_avg_3: <float or null>
      cost_usd_avg_3: <float or null>
      rounds_avg_3: <float or null>
      tool_calls_avg_3: <float or null>
    test_002: <same shape>
    test_003: <same shape>
    test_004: <same shape>
    test_005: <same shape>

fewshot:
  creators:
    codex:
      status: <complete|incomplete>
      incomplete_reason: <string or null>
      creator_source:
        revision: <immutable revision>
        skill_md_sha256: <sha256>
        bundle_sha256: <sha256>
        file_modes_digest_algorithm: git_executable_bit_v1
        file_modes_sha256: <sha256>
      skill_dirs:
        attempt_01: <path relative to this report file or null>
        attempt_02: <path relative to this report file or null>
        attempt_03: <path relative to this report file or null>
      generation:
        attempts:
          attempt_01:
            validation_status: <valid|invalid|missing|contaminated>
            skill_bundle_sha256: <sha256 or null>
            file_modes_digest_algorithm: git_executable_bit_v1
            file_modes_sha256: <sha256 or null>
            input_tokens: <int or null>
            cached_input_tokens: <int or null>
            output_tokens: <int or null>
            reasoning_output_tokens: <int or null>
            total_tokens: <int or null>
            cost_usd: <float or null>
            duration_seconds: <float or null>
            assistant_turns: <int or null>
            tool_calls: <int or null>
            file_count: <int or null>
            bytes: <int or null>
            portability_warnings: []
          attempt_02: <same shape>
          attempt_03: <same shape>
        summary:
          valid_generation_rate: <float>
          input_tokens_avg_3: <float or null>
          cached_input_tokens_avg_3: <float or null>
          output_tokens_avg_3: <float or null>
          reasoning_output_tokens_avg_3: <float or null>
          total_tokens_avg_3: <float or null>
          cost_usd_avg_3: <float or null>
          duration_seconds_avg_3: <float or null>
          rounds_avg_3: <float or null>
          tool_calls_avg_3: <float or null>
          file_count_avg_3: <float or null>
          bytes_avg_3: <float or null>
      overall_acc_at_3: <float or null>
      overall_std_at_3: <float or null>
      lift_status: <complete|unavailable>
      lift_unavailable_reason: <string or null>
      lift_over_shared_base: <float or null>
      efficiency: <same independent shape as base.efficiency, or null fields>
      tasks: <always expand the base.tasks shape, using null only for missing attempts>
    cc: <same independent shape as codex; never a YAML alias>
    deepagents: <same independent shape as codex; never a YAML alias>
    opencode: <same independent shape as codex; never a YAML alias>

creator_pairwise_deltas:
  codex_minus_cc:
    status: <complete|unavailable>
    unavailable_reason: <string or null>
    overall_delta: <float or null>
    tasks:
      test_001: <float or null>
      test_002: <float or null>
      test_003: <float or null>
      test_004: <float or null>
      test_005: <float or null>
  codex_minus_deepagents: <same independent shape as codex_minus_cc>
  codex_minus_opencode: <same independent shape as codex_minus_cc>
  cc_minus_deepagents: <same independent shape as codex_minus_cc>
  cc_minus_opencode: <same independent shape as codex_minus_cc>
  deepagents_minus_opencode: <same independent shape as codex_minus_cc>

excluded_attempts: []
notes: []
```

The example uses `<same independent shape as ...>` as documentation shorthand,
not as valid report data. A formal report must expand every creator and pair into
separate mappings with separately populated values. Never use YAML anchors or
aliases to copy branch data.

## Requirements

- Preserve all three raw scores for every test task and branch.
- `formal_run_interface` must contain exactly one accepted caller parameter,
  `model_profile`, and the fixed creator/mode sets shown above.
- Always expand every creator's five task mappings, including an incomplete
  creator. Preserve each completed raw score in its fixed attempt slot and use
  `null` only for a missing/unselected attempt; do not replace the whole tasks
  mapping with null.
- Use population standard deviation.
- Keep reasonable decimal precision; four to six decimal places is recommended.
- Every creator lift references the one shared base.
- If base is incomplete, its metrics and every creator lift are null, but
  complete creator scores and creator-to-creator deltas remain reportable.
- `skill_dirs` paths and solver attempts must agree by attempt number.
- `skill_dirs` are relative to the directory containing the per-model report,
  so a report under `report/<model_profile>/` normally reaches a package through
  `../../skills/<model_profile>/...`.
- Every selected solver's recorded generated-package digest must equal the
  matching generation-attempt digest.
- Creator revisions and hashes must match the preflight run manifest.
- Generation usage is separate from solver efficiency.
- Trace paths and detailed runtime metadata stay in workspace audit files rather
  than the formal report.
- Every selected formal attempt requires a uniquely matched primary trace. A
  trace-derived field may still be `null` only when that matched trace/provider
  does not expose the field; attempt metadata must explain it.
- An incomplete creator branch has `status: incomplete`, a reason, and null
  `acc@3`/`std@3`/lift fields. Every pair containing it is `unavailable` with
  null deltas; never publish fabricated values.
- Contaminated attempts are excluded and their replacements are documented
  under `excluded_attempts`.
- Pricing is model-profile-specific. Never apply one profile's rate card to the
  other profile.
- `identity_consistent_across_selected_runs` must be true for a complete profile;
  otherwise stop aggregation and report the identity change.

## Cross-Model Side-By-Side Report

After both model reports are finalized, with incomplete branches explicitly
represented when necessary, optionally write:

```text
report/comparison/<task_group_id>.yaml
```

Recommended shape:

```yaml
experiment_id: codex_skill_creator_comparison
task_group_id: <task_group_id>
comparison_policy: side_by_side_no_pooling
profiles:
  gpt5_5_xhigh:
    report: ../gpt5_5_xhigh/<task_group_id>.yaml
    status: <complete|incomplete>
    base_status: <complete|incomplete>
    base_acc_at_3: <float or null>
    creators:
      codex: {status: <complete|incomplete>, acc_at_3: <float or null>, lift: <float or null>}
      cc: {status: <complete|incomplete>, acc_at_3: <float or null>, lift: <float or null>}
      deepagents: {status: <complete|incomplete>, acc_at_3: <float or null>, lift: <float or null>}
      opencode: {status: <complete|incomplete>, acc_at_3: <float or null>, lift: <float or null>}
  deepseek_v4_max_preview:
    report: ../deepseek_v4_max_preview/<task_group_id>.yaml
    status: <complete|incomplete>
    base_status: <complete|incomplete>
    base_acc_at_3: <float or null>
    creators:
      codex: {status: <complete|incomplete>, acc_at_3: <float or null>, lift: <float or null>}
      cc: {status: <complete|incomplete>, acc_at_3: <float or null>, lift: <float or null>}
      deepagents: {status: <complete|incomplete>, acc_at_3: <float or null>, lift: <float or null>}
      opencode: {status: <complete|incomplete>, acc_at_3: <float or null>, lift: <float or null>}
notes:
  - Do not pool profiles with different providers or reasoning semantics.
```
