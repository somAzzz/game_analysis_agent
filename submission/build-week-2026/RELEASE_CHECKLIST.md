# Release closeout

The Build Week submission gate is complete. Optional evidence that was not
produced is explicitly marked `not_claimed` and must not be used in public
time-saved, independent-review, current-image, or current cross-platform claims.

- [x] Open draft PR #5 and retain successful full platform run 29531033847 plus artifacts.
- [x] Run hardened Docker dashboard/Replay on Linux amd64 and native Linux arm64; update the platform ledger.
- [x] Verify pinned Godot 4.4 on macOS and Linux amd64 and run both fresh-game acceptance rows.
- [x] Run a bounded server-side OpenAI six-persona campaign; retain its
  sanitized public bundle and replayable view.
- [x] Keep the historical amd64/arm64 digest out of current-revision claims;
  retain it only as truthfully labeled historical metadata.
- [x] Mark the unmeasured manual-versus-Forge comparison `not_claimed`; publish
  no time-saved claim.
- [x] Mark the unrun non-builder clean-room study `not_claimed`; publish no
  independent-review claim.
- [x] Update and pass `tools/review_build_week_g4.py` while keeping every
  claimed capability fail-closed.
- [x] Replace the YouTube placeholder in the Devpost draft.
- [x] Record the public 2:55 video and verify signed-out access, audio, duration,
  and the no-secret review disposition. Captions remain optional.
- [x] Confirm repository access and add MIT licensing plus attribution for judges.
- [x] Run final G5 secret, privacy, link, hash, test, image-disposition, and
  video review.

Machine-readable records are complete or explicitly `not_claimed`, without estimates:

- `release-metadata.json`
- `manual-comparison.json`
- `clean-room-review.json`
- `video-review.json`

Final local gate (expected: `passed`):

```bash
uv run python tools/review_build_week_g5.py --json
```

Never add token/cost/time-saved, platform-support, live-provider, or repair-
success language unless its pending claim has acquired a dated artifact and the
claim ledger reviewer accepts it.
