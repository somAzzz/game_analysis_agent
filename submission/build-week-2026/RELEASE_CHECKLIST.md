# Release blockers

The submission is not authorized while G4 is failed. Complete in order:

- [x] Open draft PR #5 and retain successful Linux amd64 Judge run 29523961052 plus artifact.
- [x] Run hardened Docker dashboard/Replay on Linux amd64 and native Linux arm64; update the platform ledger.
- [ ] Verify pinned Godot 4.4 on macOS and Linux amd64 and run both fresh-game acceptance rows.
- [ ] Run one bounded server-side OpenAI persona campaign; retain a redacted record.
- [x] Publish the amd64/arm64 Judge image and commit its index digest metadata.
- [ ] Run the manual-versus-Forge timed comparison with the same task and stopping rule.
- [ ] Have a non-builder complete the twelve-minute clean-room judge simulation.
- [ ] Update and pass `tools/review_build_week_g4.py` without weakening required checks.
- [ ] Replace repository, UI, image, and YouTube placeholders in the Devpost draft.
- [ ] Record video, verify duration below 3:00, captions/audio, and signed-out YouTube access.
- [ ] Confirm repository access/licensing for all judges.
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
