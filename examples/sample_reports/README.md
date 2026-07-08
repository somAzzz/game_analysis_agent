# Sample Reports

This directory contains a tiny sanitized report bundle for people who want to
inspect the dashboard without running Godot or an LLM.

Build the static dashboard from these samples:

```bash
uv run python tools/build_dashboard.py all --reports examples/sample_reports
```

Then open:

```text
examples/sample_reports/index.html
```

For a richer React demo, use the prebuilt sanitized dataset under
`frontend/public-demo/`.
