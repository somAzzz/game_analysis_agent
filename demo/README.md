# Embedded Study in Germany demo

`study-in-germany/` is the canonical Godot demo used by the Build Week
campaign, repair experiment, Judge Mode, and real-game contract tests. It is
an exact materialization of upstream commit
`348b9fd5501e71ebc7142e10f9068fc1490b5124`, not a Git submodule and not the
maintainer's newer development checkout.

The owner explicitly approved this snapshot for public competition
distribution. `.playtest-forge-source.json` binds the embedded files to the
upstream commit, tree, archive hash, and content-tree hash. Generated Godot
imports, local editor state, historical reports, credentials, and the upstream
`.git` directory are not included.

The retained Codex candidate patch is intentionally **not** applied to this
canonical source. See `examples/build_week_2026/experiment-v1/patch.diff` and
the fixed/holdout evidence for the rejected experiment. Keeping the baseline
unchanged makes the distinction between source, candidate change, and final
decision auditable.

Repository licensing is a final G5 release blocker until the maintainer adds
the selected top-level license; this file does not invent or imply one.
