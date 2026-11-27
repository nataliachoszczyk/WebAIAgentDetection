"""The log store: one JSON Lines file for each session, and one file with the session codes."""

import json
import secrets
import threading
import time
from pathlib import Path

from .logger.schema import FORMAT_VERSION


class Store:
    def __init__(self, data_dir):
        self.root = Path(data_dir)
        self.events_dir = self.root / "events"
        self.codes_file = self.root / "sessions.jsonl"
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._sessions_cache = (None, {})

    def new_session(self, label, model=None, note=None):
        """Make a session code. The label tells who operates: "human", "agent" or "bot"."""
        code = secrets.token_urlsafe(9)
        record = {"session": code, "label": label, "model": model, "note": note,
                  "created": int(time.time() * 1000)}
        with self._lock, self.codes_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return code

    def sessions(self):
        if not self.codes_file.exists():
            return {}
        # The command line adds codes while the server runs. Read the file again only when it changes.
        stat = self.codes_file.stat()
        key = (stat.st_mtime_ns, stat.st_size)
        if self._sessions_cache[0] != key:
            with self.codes_file.open(encoding="utf-8") as f:
                records = [json.loads(line) for line in f if line.strip()]
            self._sessions_cache = (key, {r["session"]: r for r in records})
        return self._sessions_cache[1]

    def is_valid(self, code):
        return bool(code) and code in self.sessions()

    def append(self, session, events, source="client"):
        """Add the events to the file of the session. The server sets the session and the time."""
        received = int(time.time() * 1000)
        lines = []
        for event in events:
            record = {"v": FORMAT_VERSION, "session": session, "src": source, "recv": received}
            if source == "server":
                record["ts"] = received
            record.update(event)
            lines.append(json.dumps(record, ensure_ascii=False) + "\n")
        path = self.events_dir / f"{session}.jsonl"
        with self._lock, path.open("a", encoding="utf-8") as f:
            f.writelines(lines)


def load_events(data_dir):
    """Load all events into one pandas DataFrame, with the label and the model of each session."""
    import pandas as pd

    store = Store(data_dir)
    sessions = pd.DataFrame(store.sessions().values(),
                            columns=["session", "label", "model", "note", "created"])
    frames = [pd.read_json(p, lines=True) for p in sorted(store.events_dir.glob("*.jsonl"))
              if p.stat().st_size > 0]
    if not frames:
        return pd.DataFrame()
    events = pd.concat(frames, ignore_index=True)
    return events.merge(sessions[["session", "label", "model"]], on="session", how="left")
