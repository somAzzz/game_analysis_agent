# Compressed JSONL report archives

Large JSONL evidence is archived losslessly with Zstandard as soon as its
producing cell is immutable and that cell's schema, provenance, completeness,
and evidence checks pass. Cohort aggregation, comparison, gates, dashboards,
and persona publication stream the cold representation directly. Never archive
a `running` or `finalizing` file, an open output file, or evidence that a
concurrent writer still owns.

The archive contract keeps both identities:

- `<name>.jsonl.zst` contains the exact JSONL bytes compressed with Zstandard;
- `<name>.jsonl.zst.manifest.json` records the raw and compressed SHA-256,
  byte counts, JSON record count, codec, level, and schema version.

Creation is atomic and `--replace` removes the source JSONL only after the
archive has decompressed, reparsed, and matched all raw identity fields.

The standard gameplay matrix seals every completed cell, the persona campaign
seals private cell traces after its public bundle passes, and the Build Week
repair verifier seals any remaining terminal JSONL. Their default is cold
`.jsonl.zst` evidence; pass `--keep-jsonl` only for temporary debugging or
compatibility. If archival fails, the command is non-success and keeps the
current raw source.

```bash
# Read-only inventory.
python tools/reports/archive_jsonl.py archive reports/repair-experiments

# Create archives but keep the JSONL sources.
python tools/reports/archive_jsonl.py archive reports/repair-experiments --apply

# Replace sources only after verified lossless archives exist.
python tools/reports/archive_jsonl.py archive reports/repair-experiments --apply --replace

# Audit cold evidence without restoring it.
python tools/reports/archive_jsonl.py verify reports/path/runs.jsonl.zst

# Restore the exact original file for existing readers and replay tools.
python tools/reports/archive_jsonl.py restore reports/path/runs.jsonl.zst --apply
```

Level 3 is the default because report JSON is highly repetitive and gains most
of the available compression at that level. Higher levels are suitable for
one-time cold archives but are not required for evidence correctness.

First-party analyzers, contracts, matrices, gates, dashboards, and persona
campaign readers accept a logical `.jsonl` path and transparently resolve its
adjacent `.jsonl.zst`. Restore only for an external or legacy reader without
compressed-input support. The accepted/rejected decision, aggregate summaries,
compact public evidence, and archive manifests remain uncompressed and directly
readable.
