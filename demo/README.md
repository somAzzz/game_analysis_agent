# Embedded Study in Germany demo

`study-in-germany/` is the canonical Godot reference demo used by campaign,
repair, dashboard, and real-game contract tests. It is
an exact materialization of upstream commit
`348b9fd5501e71ebc7142e10f9068fc1490b5124`, not a Git submodule and not the
maintainer's newer development checkout.

The owner approved this snapshot for public repository distribution.
`.playtest-forge-source.json` binds the embedded files to the
upstream commit, tree, archive hash, and content-tree hash. Generated Godot
imports, local editor state, historical reports, credentials, and the upstream
`.git` directory are not included.

The retained Codex candidate patch is intentionally **not** applied to this
canonical source. See `examples/build_week_2026/experiment-v1/patch.diff` and
the fixed/holdout evidence for the rejected experiment. Keeping the baseline
unchanged makes the distinction between source, candidate change, and final
decision auditable.

The repository is distributed under the top-level MIT license.
