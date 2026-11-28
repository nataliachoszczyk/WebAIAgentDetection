import json

from src.traces import EXCLUDED, check, study_sessions


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))


def client(page, seq, kind, **fields):
    return {"v": 1, "session": "s", "src": "client", "recv": 1000 + seq, "page": page, "seq": seq, "t": seq,
            "ts": 1000 + seq, "type": kind, "path": "/", **fields}


def test_selection_and_check(tmp_path):
    excluded = next(iter(EXCLUDED))
    write(tmp_path / "sessions.jsonl", [
        {"session": "h1", "label": "human", "note": "group1", "created": 1}, {"session": "h1", "started": 2},
        {"session": excluded, "label": "human", "note": "group1", "created": 1}, {"session": excluded, "started": 2},
        {"session": "t1", "label": "human", "note": "start-test", "created": 1}, {"session": "t1", "started": 2},
        {"session": "a1", "label": "agent", "model": "m", "note": "browser=plain motion=direct effort=medium agent=2 run=wad-009",
         "created": 1}, {"session": "a1", "started": 2},
        {"session": "a0", "label": "agent", "model": "m", "note": "browser=plain run=wad-009", "created": 1},
        {"session": "a0", "started": 2},
        {"session": "n1", "label": "human", "note": "group1", "created": 1},
    ])
    items = [{"product": "ridge-runner", "color": "Moss", "size": 43}, {"product": "alder-trek", "color": "Tan", "size": 42}]
    write(tmp_path / "events" / "h1.jsonl", [
        client("p1", 0, "page_view", title="", referrer="", time_origin=0), client("p1", 1, "page_hide"),
        client("p2", 0, "page_view", title="", referrer="", time_origin=0), client("p2", 2, "page_hide", extra=1),
        {"v": 1, "session": "h1", "src": "server", "recv": 5, "ts": 5, "type": "order", "order": "PS-1",
         "items": items, "total": 1, "fields": {}},
    ])
    write(tmp_path / "agent" / "a1.jsonl", [{"type": "summary", "end": "finish", "steps": 3, "cost": 0.01}])

    assert [s["session"] for s in study_sessions(tmp_path)] == ["h1", "a1"]
    rows = {r["session"]: r for r in check(tmp_path, tmp_path / "agent")}
    assert rows[excluded]["reason"] == EXCLUDED[excluded]
    assert rows["a0"]["reason"] == "older version of the agent"
    assert rows["t1"]["reason"] == "test of the setup" and rows["n1"]["reason"] == "never started"
    assert rows["a1"]["browser"] == "plain" and rows["a1"]["run"] == "wad-009" and rows["a1"]["agent_end"] == "finish"
    h1 = rows["h1"]
    assert h1["pages"] == 2 and h1["seq_gaps"] == 1 and h1["pages_no_hide"] == 0
    assert h1["unknown_fields"] == "page_hide.extra=1"
    assert h1["task1_ok"] and h1["task2_ok"] and h1["ordered"] and not h1["contact"]
    assert h1["problems"] == "seq_gaps=1;unknown fields"
    assert rows["a1"]["problems"] == "no events"
