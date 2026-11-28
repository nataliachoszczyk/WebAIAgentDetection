import json

from src.traces import EXCLUDED, sessions, study_sessions


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))


def test_selection(tmp_path):
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
    assert [s["session"] for s in study_sessions(tmp_path)] == ["h1", "a1"]
    rows = {r["session"]: r for r in sessions(tmp_path)}
    assert rows[excluded]["reason"] == EXCLUDED[excluded]
    assert rows["a0"]["reason"] == "older version of the agent"
    assert rows["t1"]["reason"] == "test of the setup" and rows["n1"]["reason"] == "never started"
    assert rows["a1"]["browser"] == "plain" and rows["a1"]["run"] == "wad-009" and rows["a1"]["agent"] == "2"
