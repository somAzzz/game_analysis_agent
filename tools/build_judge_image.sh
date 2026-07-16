#!/bin/sh
set -eu

: "${JUDGE_IMAGE_REF:?set JUDGE_IMAGE_REF, for example ghcr.io/owner/playtest-forge-judge}"
JUDGE_IMAGE_TAG="${JUDGE_IMAGE_TAG:-build-week-2026}"
OUTPUT="${JUDGE_IMAGE_METADATA:-judge-image-metadata.json}"

command -v docker >/dev/null 2>&1 || {
  echo "docker is required to build the multi-architecture Judge image" >&2
  exit 2
}

reference="${JUDGE_IMAGE_REF}:${JUDGE_IMAGE_TAG}"
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --provenance=mode=max \
  --sbom=true \
  --push \
  --tag "$reference" \
  --file Dockerfile.judge .

digest="$(docker buildx imagetools inspect "$reference" --format '{{json .Manifest.Digest}}' | tr -d '"')"
case "$digest" in
  sha256:????????????????????????????????????????????????????????????????) ;;
  *) echo "registry did not return a valid image-index digest" >&2; exit 3 ;;
esac

contract="$(python3 - <<'PY'
import pathlib
import sys

root = pathlib.Path.cwd()
sys.path.insert(0, str(root / "src"))
from game_analysis_agent.platform_delivery import platform_contract_fingerprint

print(platform_contract_fingerprint(root))
PY
)"

python3 - "$OUTPUT" "$reference" "$digest" "$contract" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = {
    "schema_version": "judge-image-metadata-v1",
    "reference": sys.argv[2],
    "index_digest": sys.argv[3],
    "platforms": ["linux/amd64", "linux/arm64"],
    "source_contract_sha256": sys.argv[4],
    "status": "built_and_pushed",
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "$reference@$digest"
