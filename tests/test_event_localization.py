from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "demo/study-in-germany/data/events/generated_events.json"
RUNTIME_SOURCES = tuple(
    ROOT / "demo/study-in-germany/data/events" / name
    for name in (
        "academic_events.json",
        "admin_events.json",
        "application_events.json",
        "life_events.json",
        "random_events.json",
        "relationship_events.json",
        "work_events.json",
    )
)
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
        assert {choice["text"] for choice in event["choices"]} <= {choice["zh"] for choice in localized["choices"]}
        english = [
            localized["title"]["en"],
            localized["body"]["en"],
            *(choice["en"] for choice in localized["choices"]),
        ]
        assert all(text.strip() and not CJK.search(text) for text in english)

    runtime_events = [
        event
        for source_path in RUNTIME_SOURCES
        for event in json.loads(source_path.read_text(encoding="utf-8"))["items"]
    ]
    assert {event["id"] for event in runtime_events} == set(catalog["events"])
    for event in runtime_events:
        localized = catalog["events"][event["id"]]
        assert {choice["zh"] for choice in localized["choices"]} == {
            choice["text"] for choice in event["choices"]
        }


def test_runtime_defaults_to_english_without_localizing_choice_identity() -> None:
    loader = (ROOT / "game-overlays/study-in-germany/scripts/data/DataLoader.gd").read_text(
        encoding="utf-8"
    )
    probe = (ROOT / "scripts/tools/RunInteractiveProbe.gd").read_text(encoding="utf-8")

    assert "event.title = event.title_en" in loader
    assert "event.body = event.body_en" in loader
    assert "choice.text = choice.text_zh" in loader
    assert 'choice.localized_text("en")' in probe
    assert 'choice.localized_text("zh")' in probe
    assert 'var safe_text := str(choice.localized_text("en")).to_lower()' in probe
