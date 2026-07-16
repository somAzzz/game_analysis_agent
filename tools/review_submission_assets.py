#!/usr/bin/env python3
"""Verify every draft submission claim against exact committed evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission/build-week-2026"


def _pointer(value: Any, pointer: str) -> Any:
    current = value
    if pointer == "":
        return current
    for raw in pointer.removeprefix("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def review() -> dict[str, Any]:
    ledger = json.loads((SUBMISSION / "claim-ledger.json").read_text(encoding="utf-8"))
    drafts = {
        "devpost": (SUBMISSION / "DEVPOST_DRAFT.md").read_text(encoding="utf-8"),
        "video": (SUBMISSION / "VIDEO_SCRIPT.md").read_text(encoding="utf-8"),
    }
    normalized_drafts = {
        name: re.sub(r"\s+", " ", content) for name, content in drafts.items()
    }
    checks: list[dict[str, Any]] = []
    for claim in ledger["claims"]:
        errors = []
        for evidence in claim["evidence"]:
            path = ROOT / evidence["path"]
            actual = _pointer(json.loads(path.read_text(encoding="utf-8")), evidence["json_pointer"])
            if actual != evidence["equals"]:
                errors.append(f"{evidence['path']}{evidence['json_pointer']} expected {evidence['equals']!r}, got {actual!r}")
        for draft in claim["used_in"]:
            approved = re.sub(r"\s+", " ", claim["approved_text"])
            if approved not in normalized_drafts[draft]:
                errors.append(f"approved text is absent from {draft}")
        checks.append({"id": claim["id"], "status": "passed" if not errors else "failed", "errors": errors})

    g4 = json.loads((ROOT / "docs/reviews/openai_build_week_2026/G4-evaluator.review.json").read_text(encoding="utf-8"))
    release_state_ok = ledger["status"] == "draft_blocked" and g4["status"] == "failed"
    checks.append({"id": "release_state", "status": "passed" if release_state_ok else "failed", "errors": [] if release_state_ok else ["draft/G4 state mismatch"]})
    placeholders = {"{{REPOSITORY_URL}}", "{{PUBLIC_UI_URL}}", "{{YOUTUBE_URL}}", "{{IMAGE_REFERENCE_AND_DIGEST}}"}
    checks.append({"id": "external_placeholders", "status": "passed" if all(item in drafts["devpost"] for item in placeholders) else "failed", "errors": []})
    combined = "\n".join(drafts.values())
    secret_pattern = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|hf_[A-Za-z0-9]{12,})")
    checks.append({"id": "secret_scan", "status": "failed" if secret_pattern.search(combined) else "passed", "errors": []})
    failures = [item["id"] for item in checks if item["status"] == "failed"]
    return {
        "schema_version": "build-week-submission-review-v1",
        "status": "passed" if not failures else "failed",
        "release_status": "blocked" if g4["status"] != "passed" else "eligible_for_g5",
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
    }


def main() -> int:
    result = review()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
