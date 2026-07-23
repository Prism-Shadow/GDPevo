# Creator Bundles

Formal runs use four pinned creator bundles:

```text
codex
cc
deepagents
opencode
```

Each creator directory has this shape:

```text
creators/<creator>/
├── manifest.yaml
├── UPSTREAM_LICENSE.txt      # when the source license is outside the bundle root
└── upstream/
    ├── SKILL.md
    └── ... creator-linked scripts, references, agents, or assets
```

`upstream/` must contain a complete immutable copy of the creator bundle. Do not
copy only `SKILL.md` when it references other files. Do not install or update a
creator during a formal experiment.

The committed `.gitkeep` files are scaffolding only. Remove the matching
`.gitkeep` when populating an upstream bundle; it must not be included in the
formal creator digest or staged to a generator.

Before formal runs, update each manifest with:

- Exact source URI.
- Immutable commit, release, or content-addressed revision.
- SHA-256 for `SKILL.md`, a deterministic whole-bundle digest, and the file-mode
  digest.
- License identifier, license-file path and hash, and retrieval date.
- Verification that every referenced local file exists.

Use the following digest definition for every creator bundle. Formal bundles
must contain no symbolic links and no `.gitkeep`. From the bundle root
(`upstream/`), hash every regular file in bytewise-sorted relative-path order as
a NUL-delimited stream of GNU `sha256sum --zero` records, then hash that stream:

```bash
LC_ALL=C find . -type f -print0 \
  | LC_ALL=C sort -z \
  | xargs -0 -r sha256sum --zero -- \
  | sha256sum
```

Record the leading digest as `bundle_sha256` and record this algorithm as
`sorted_relative_file_sha256_v1`. Reject the bundle if `find . -type l` returns
anything. Directory mtimes, ownership, and permissions are deliberately not
part of that content digest; relative paths and file bytes are.

File execution modes are a separate required invariant because creator scripts
may depend on being executable. Git preserves the executable classification but
does not preserve group-write and other complete octal permission details across
different checkout umasks. Canonicalize every regular file to `755` when any
execute bit is set and to `644` otherwise, then hash a NUL-delimited stream of
sorted relative path and canonical mode pairs:

```bash
LC_ALL=C find . -type f -print0 \
  | LC_ALL=C sort -z \
  | while IFS= read -r -d '' path; do \
      raw_mode=$((8#$(stat -c '%a' -- "$path")))
      if (( raw_mode & 8#111 )); then
        canonical_mode=755
      else
        canonical_mode=644
      fi
      printf '%s\0%s\0' "$path" "$canonical_mode"; \
    done \
  | sha256sum
```

Record the leading digest as `file_modes_sha256` and the algorithm as
`git_executable_bit_v1`. Bundle copies must preserve executable classification,
and both the content digest and file-mode digest must match before every formal
staging. Formal agent containers use the fixed UID:GID recorded in
`configs/experiment.yaml`, so runtime access semantics do not drift across
creators.

When the source repository keeps its license outside the creator subdirectory,
store an unchanged copy as `creators/<creator>/UPSTREAM_LICENSE.txt`; do not add
it to `upstream/` or stage it to the generator. Every manifest records the
applicable license path and SHA-256. This preserves exact bundle parity while
keeping the redistributed source accompanied by its license notice.

## Selected Sources

- `codex`: OpenAI's `skill-creator` from `openai/skills`.
- `cc`: Anthropic's official Claude Code `skill-creator` plugin bundle from
  `anthropics/claude-plugins-official`.
- `deepagents`: the Deep Agents Code built-in `skill-creator` from
  `langchain-ai/deepagents`.
- `opencode`: the pinned third-party `antongulin/opencode-skill-creator`
  community adaptation. OpenCode documents and loads Agent Skills but does not
  ship an official skill-creator bundle, so the manifest records
  `official_implementation: false` rather than presenting it as an
  OpenCode-maintained implementation.

The manifests are the source of truth for exact repository paths, immutable
commits or releases, retrieval dates, licenses, and bundle hashes. The stable
branch ID `opencode` identifies the OpenCode-specific creator condition; it does
not imply official OpenCode maintenance or endorsement.

## Runtime Staging

For a generation run, copy the selected `upstream/` directory to `/work/creator/`
without changing its contents. Stage the common `COMMON_CONTRACT.md` as
`/work/creator_contract.md`. The generator reads both, with the common contract
controlling experiment boundaries and the upstream bundle controlling creator
strategy.

No creator-specific adapter prompt is allowed unless it is reviewed, frozen,
hashed, and reported as an additional experimental artifact.
