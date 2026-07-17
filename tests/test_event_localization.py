from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "demo/study-in-germany/data/events/generated_events.json"
CATALOG = ROOT / "game-overlays/study-in-germany/data/localization/events.json"
CJK = re.compile(r"[\u3400-\u9fff]")


def test_event_localization_covers_every_event_and_choice_without_mechanic_changes() -> None:
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes)["items"]
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    assert catalog["schema_version"] == "event-localization-v1"
    assert catalog["default_locale"] == "en"
    assert catalog["source"] == {
        "event_count": len(source),
        "path": "data/events/generated_events.json",
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
    }
    assert set(catalog["events"]) == {event["id"] for event in source}

    for event in source:
        localized = catalog["events"][event["id"]]
        assert localized["title"]["zh"] == event["title"]
        assert localized["body"]["zh"] == event["body"]
        assert [choice["zh"] for choice in localized["choices"]] == [
            choice["text"] for choice in event["choices"]
        ]
        english = [
            localized["title"]["en"],
            localized["body"]["en"],
            *(choice["en"] for choice in localized["choices"]),
        ]
        assert all(text.strip() and not CJK.search(text) for text in english)


def test_runtime_defaults_to_english_without_localizing_choice_identity() -> None:
    loader = (ROOT / "game-overlays/study-in-germany/scripts/data/DataLoader.gd").read_text(
        encoding="utf-8"
    )
    probe = (ROOT / "scripts/tools/RunInteractiveProbe.gd").read_text(encoding="utf-8")

    assert "event.title = event.title_en" in loader
    assert "event.body = event.body_en" in loader
    assert "choice.text = choice.text_en" in loader
    assert 'choice.localized_text("en")' in probe
    assert 'choice.localized_text("zh")' in probe
    assert 'var safe_text := str(choice.localized_text("en")).to_lower()' in probe
