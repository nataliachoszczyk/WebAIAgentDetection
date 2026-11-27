import json

import pytest

from src.shop.logger.schema import InvalidEvent, clean_client_event
from src.shop.store import Store, load_events


def test_clean_event_keeps_only_known_fields():
    raw = {"type": "click", "page": "p1", "seq": 3, "t": 12.5, "ts": 1, "path": "/",
           "x": 10, "y": 20, "target": "button#buy", "secret": "drop me"}
    event = clean_client_event(raw)
    assert "secret" not in event
    assert event["target"] == "button#buy"


@pytest.mark.parametrize("raw", [
    {"type": "unknown", "seq": 0, "t": 0},
    {"type": "click", "seq": "0", "t": 0},
    {"type": "click", "seq": 0, "t": 0, "x": {"a": 1}},
    {"type": "order", "seq": 0, "t": 0},
    "not an object",
])
def test_clean_event_rejects_bad_input(raw):
    with pytest.raises(InvalidEvent):
        clean_client_event(raw)


def test_long_strings_are_cut():
    event = clean_client_event({"type": "click", "seq": 0, "t": 0, "text": "a" * 1000})
    assert len(event["text"]) == 300


def test_store_writes_and_loads_sessions(tmp_path):
    store = Store(tmp_path)
    human = store.new_session("human")
    agent = store.new_session("agent", model="google/gemini-3-flash-preview")
    assert store.is_valid(human) and not store.is_valid("wrong")

    store.append(human, [{"type": "click", "seq": 0, "t": 1.0}])
    store.append(agent, [{"type": "click", "seq": 0, "t": 2.0}, {"type": "scroll", "seq": 1, "t": 3.0}])

    line = json.loads((tmp_path / "events" / f"{human}.jsonl").read_text().splitlines()[0])
    assert line["v"] == 1 and line["session"] == human and line["src"] == "client"

    events = load_events(tmp_path)
    assert len(events) == 3
    assert set(events.loc[events.session == agent, "model"]) == {"google/gemini-3-flash-preview"}
    assert set(events.loc[events.session == human, "label"]) == {"human"}
