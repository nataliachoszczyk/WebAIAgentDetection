"""The log store: one JSON Lines file for each session, one file with the session codes and one with the join links."""

import json
import secrets
import threading
import time
from pathlib import Path

from .logger.schema import FORMAT_VERSION


class Store:
    # After the last task, the page can still send the events of the last seconds.
    grace_ms = 60_000

    def __init__(self, data_dir):
        self.root = Path(data_dir)
        self.events_dir = self.root / "events"
        self.codes_file = self.root / "sessions.jsonl"
        self.joins_file = self.root / "joins.jsonl"
        self.events_dir.mkdir(parents=True, exist_ok=True)
        # Reentrant, because a join link makes a session while it holds the lock.
        self._lock = threading.RLock()
        self._cache = {}
        self._seen = {}

    def _write(self, path, record):
        with self._lock, path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _read(self, path, key):
        """Read a JSON Lines file into a dict by key. A later line of a key adds fields to its record."""
        if not path.exists():
            return {}
        # The command line adds lines while the server runs. Read a file again only when it changes.
        stat = path.stat()
        version = (stat.st_mtime_ns, stat.st_size)
        cached = self._cache.get(path)
        if cached is None or cached[0] != version:
            merged = {}
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        merged.setdefault(record[key], {}).update(record)
            cached = self._cache[path] = (version, merged)
        return cached[1]

    def new_session(self, label, model=None, note=None, join=None):
        """Make a session code. The label tells who operates: "human", "agent" or "bot"."""
        code = secrets.token_urlsafe(9)
        self._write(self.codes_file, {"session": code, "label": label, "model": model, "note": note,
                                      "join": join, "created": int(time.time() * 1000)})
        return code

    def sessions(self):
        # A later line of a session adds a state ("started", "ordered", "closed") to its record.
        return self._read(self.codes_file, "session")

    def new_join(self, label, max_sessions, until, model=None, note=None):
        """Make a join link. Each visit makes a new session, until the limit or the time `until` (Unix ms)."""
        secret = secrets.token_urlsafe(12)
        self._write(self.joins_file, {"join": secret, "label": label, "model": model, "note": note,
                                      "max": max_sessions, "until": until, "created": int(time.time() * 1000)})
        return secret

    def joins(self):
        return self._read(self.joins_file, "join")

    def join_sessions(self, secret):
        return [s for s in self.sessions().values() if s.get("join") == secret]

    def join_session(self, secret):
        """Make a session from a join link. Return (code, None), or (None, reason) if the link is not usable."""
        with self._lock:
            join = self.joins().get(secret)
            if join is None:
                return None, "missing"
            if time.time() * 1000 > join["until"]:
                return None, "expired"
            if len(self.join_sessions(secret)) >= join["max"]:
                return None, "full"
            return self.new_session(join["label"], join["model"], join["note"], join=secret), None

    def is_valid(self, code):
        return bool(code) and code in self.sessions()

    def state(self, code, name):
        """Return the time of a state of the session, or None."""
        return self.sessions().get(code, {}).get(name)

    def mark(self, code, name):
        """Record a state of the session once: "started", "ordered" or "closed"."""
        with self._lock:
            if self.state(code, name) is not None:
                return
            self._write(self.codes_file, {"session": code, name: int(time.time() * 1000)})

    def accepts_events(self, code):
        if not self.is_valid(code):
            return False
        closed = self.state(code, "closed")
        return closed is None or time.time() * 1000 <= closed + self.grace_ms

    def _seen_events(self, session, path):
        """Return the (page, seq) pairs in the file of the session. The logger can send an event two times."""
        seen = self._seen.get(session)
        if seen is None:
            seen = set()
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    for line in f:
                        record = json.loads(line)
                        if "page" in record and "seq" in record:
                            seen.add((record["page"], record["seq"]))
            self._seen[session] = seen
        return seen

    def append(self, session, events, source="client"):
        """Add the events to the file of the session. The server sets the session and the time."""
        received = int(time.time() * 1000)
        path = self.events_dir / f"{session}.jsonl"
        with self._lock:
            if source == "client":
                seen = self._seen_events(session, path)
                events = [e for e in events if (e.get("page"), e.get("seq")) not in seen]
                seen.update((e.get("page"), e.get("seq")) for e in events)
            lines = []
            for event in events:
                record = {"v": FORMAT_VERSION, "session": session, "src": source, "recv": received}
                if source == "server":
                    record["ts"] = received
                record.update(event)
                lines.append(json.dumps(record, ensure_ascii=False) + "\n")
            with path.open("a", encoding="utf-8") as f:
                f.writelines(lines)
        return len(events)


def load_events(data_dir):
    """Load all events into one pandas DataFrame, with the label and the model of each session."""
    import pandas as pd

    store = Store(data_dir)
    sessions = pd.DataFrame(store.sessions().values(),
                            columns=["session", "label", "model", "note", "join", "created", "started", "ordered", "closed"])
    frames = [pd.read_json(p, lines=True) for p in sorted(store.events_dir.glob("*.jsonl"))
              if p.stat().st_size > 0]
    if not frames:
        return pd.DataFrame()
    events = pd.concat(frames, ignore_index=True)
    return events.merge(sessions[["session", "label", "model"]], on="session", how="left")
