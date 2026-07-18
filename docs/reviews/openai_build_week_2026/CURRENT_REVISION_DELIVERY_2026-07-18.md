# Current-revision delivery closeout — 2026-07-18

Status: **local linux/amd64 passed; current multi-architecture image not
published**

## Tested contract

- Working-tree platform contract: `ccddf31ac83b77d4683e4b35886dc1b14fdd78954ec1802ddffaf072d49c3bae`
- Local image: `playtest-forge-judge:submission-current`
- Local image identity: mutable local-only tag; no registry digest claimed
- Docker Engine: 29.6.0
- Architecture: linux/amd64
- Runtime user: `judge` (UID 10001)

## Results

- Host Ruff: passed.
- Host Python: 511 passed, 1 declared environment skip.
- Frontend: 28 passed; public production build passed.
- Host Judge Inspect: 206 artifacts and 9 public claims passed.
- Host Judge Replay: passed.
- Restricted container Inspect: passed with no network, read-only root,
  `/tmp` tmpfs, and all Linux capabilities dropped.
- Restricted container Replay: passed under the same restrictions.
- Restricted Dashboard/API: HTML returned 200; the experiment index contained
  signed Replay, OpenAI campaign, and deterministic correctness records. The
  OpenAI detail returned `OPENAI API`, `campaign_complete`, 6 cells, 114 weeks,
  and null decision/patch.

## Defect found and fixed

The first current-image Inspect failed because `Dockerfile.judge` did not copy
the frontend implementation and test artifacts newly listed by
`judge-manifest.json`. The Dockerfile now copies the exact manifest-required
files, `.dockerignore` explicitly permits the three required Python tests, and
`tests/test_judge_container.py` prevents regression. The rebuilt restricted
Inspect then passed.

## Publication boundary

The historical multi-architecture GHCR digest was built from an older platform
contract and is not claimed for the current submission revision. A final release
may either publish and verify a new amd64/arm64 digest or omit the immutable
image claim and use GitHub Pages plus repository `./judge` as the official
no-rebuild paths. This report proves only the current local linux/amd64 image.
