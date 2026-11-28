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


def test_store_sees_codes_from_another_process(tmp_path):
    server_store, cli_store = Store(tmp_path), Store(tmp_path)
    assert not server_store.is_valid("x")
    code = cli_store.new_session("human")
    assert server_store.is_valid(code)


def test_server_events_get_a_time(tmp_path):
    store = Store(tmp_path)
    code = store.new_session("human")
    store.append(code, [{"type": "order", "order": "PS-1"}], source="server")
    line = json.loads((tmp_path / "events" / f"{code}.jsonl").read_text())
    assert line["ts"] == line["recv"]


def test_store_ignores_an_event_that_arrives_again(tmp_path):
    # The logger sends an unconfirmed event again. The file must keep it once, also after a restart of the server.
    code = Store(tmp_path).new_session("human")
    event = {"type": "click", "page": "p1", "seq": 0, "t": 1, "ts": 1, "path": "/"}
    assert Store(tmp_path).append(code, [event]) == 1
    store = Store(tmp_path)
    assert store.append(code, [event, {**event, "seq": 1}]) == 1
    assert store.append(code, [{**event, "page": "p2"}]) == 1
    lines = (tmp_path / "events" / f"{code}.jsonl").read_text().splitlines()
    assert [(json.loads(x)["page"], json.loads(x)["seq"]) for x in lines] == [("p1", 0), ("p1", 1), ("p2", 0)]


def test_join_link_has_a_limit_and_an_end(tmp_path):
    import time
    store = Store(tmp_path)
    secret = store.new_join("human", 2, until=int(time.time() * 1000) + 60_000, note="friends")
    first, _ = store.join_session(secret)
    second, _ = store.join_session(secret)
    assert first != second
    assert store.join_session(secret) == (None, "full")
    assert store.sessions()[first]["label"] == "human" and store.sessions()[first]["join"] == secret
    assert store.join_session("unknown") == (None, "missing")
    old = store.new_join("human", 5, until=int(time.time() * 1000) - 1)
    assert store.join_session(old) == (None, "expired")


def test_join_link_keeps_the_limit_under_parallel_visits(tmp_path):
    import threading
    import time
    store = Store(tmp_path)
    secret = store.new_join("human", 5, until=int(time.time() * 1000) + 60_000)
    codes = []
    threads = [threading.Thread(target=lambda: codes.append(store.join_session(secret)[0])) for _ in range(30)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len([c for c in codes if c]) == 5
    assert len(store.join_sessions(secret)) == 5


def test_command_line(tmp_path):
    import subprocess
    import sys
    run = lambda *args: subprocess.run([sys.executable, "-m", "src.shop", *args, "--data-dir", str(tmp_path)],
                                       check=True, capture_output=True, text=True).stdout
    link = run("new-join", "--label", "human", "--max", "3", "--until", "2099-12-31", "--base-url", "https://x.example")
    assert link.startswith("https://x.example/join/") and "until 2099-12-31 23:59" in link
    sessions = run("new-session", "--label", "agent", "--model", "m1", "--count", "2").split()
    assert len(sessions) == 2 and all("/s/" in s for s in sessions)
    report = run("status")
    assert "agent           2" in report and "human: 0/3 used" in report and "(open)" in report
