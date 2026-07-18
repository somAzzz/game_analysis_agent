# Release blockers

The submission is not authorized while G4 is failed. Complete in order:

- [x] Open draft PR #5 and retain successful full platform run 29531033847 plus artifacts.
- [x] Run hardened Docker dashboard/Replay on Linux amd64 and native Linux arm64; update the platform ledger.
- [x] Verify pinned Godot 4.4 on macOS and Linux amd64 and run both fresh-game acceptance rows.
- [x] Run a bounded server-side OpenAI six-persona campaign; retain its
  sanitized public bundle and replayable view.
- [ ] Rebuild/publish the current-revision amd64/arm64 Judge image, or keep the
  historical digest out of final claims.
- [ ] Run the manual-versus-Forge timed comparison with the same task and stopping rule.
- [ ] Have a non-builder complete the twelve-minute clean-room judge simulation.
- [ ] Update and pass `tools/review_build_week_g4.py` without weakening required checks.
- [ ] Replace the remaining YouTube placeholder in the Devpost draft.
- [ ] Record video, verify duration below 3:00, captions/audio, and signed-out YouTube access.
- [x] Confirm repository access and add MIT licensing plus attribution for judges.
- [ ] Run final G5 secret, privacy, link, hash, test, clean-clone, image, and video review.

Machine-readable records to complete without estimates:

- `release-metadata.json`
- `manual-comparison.json`
- `clean-room-review.json`
- `video-review.json`

Final local gate:

```bash
uv run python tools/review_build_week_g5.py --json
```

Never add token/cost/time-saved, platform-support, live-provider, or repair-
success language unless its pending claim has acquired a dated artifact and the
claim ledger reviewer accepts it.
