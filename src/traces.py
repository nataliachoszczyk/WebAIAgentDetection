"""The sessions of the study (wad-011). See docs/traces.md."""

import json
from pathlib import Path


# Sessions that do not go into the analysis. Keep all exclusions here, with the reason.
EXCLUDED = {
    "_1QnFCzrsUVW": "link preview bots opened the link first, and the tunnel failed during the session",
}
# The first runs of small models came before the tools accepted their mistakes (see docs/agent.md).
EXCLUDED.update({code: "small model before the tool fixes of 2026-11-28" for code in (
    "SD8nICbv6Jrz", "liXfHzey-jOj", "sJPQbPSAVFAj", "ZXq8EvCIwncN", "3hJwzBr-qYs_", "pvN2J7vUYO6D")})
EXCLUDED.update({code: "the model API refused the first request (a wrong effort option)" for code in (
    "-p98yJyFSZw9", "iNiKITsujmAg", "EMeWLWmxxfHp", "W4td1KtTEn7R", "qrJOcKrfx9LI", "sbEYUF6oLXHq")})
# The versions of the agent (AGENT_VERSION in src/agent/agent.py) in the study. Older versions were tests.
STUDY_AGENT_VERSIONS = {"2"}
# Notes of sessions that only tested the setup.
TEST_NOTES = {"start-test", "dev", "e2e test", "test"}


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_note(note):
    """An agent note has the form `browser=plain motion=direct effort=medium run=wad-009`."""
    return dict(part.split("=", 1) for part in (note or "").split() if "=" in part)


def sessions(data_dir):
    """Return the sessions of the data folder, with the reason when a session is not in the study."""
    merged = {}
    for record in read_jsonl(Path(data_dir) / "sessions.jsonl"):
        merged.setdefault(record["session"], {}).update(record)
    result = []
    for code, s in merged.items():
        setup = parse_note(s.get("note"))
        run = setup.get("run", s.get("note"))
        reason = EXCLUDED.get(code)
        if reason is None and (run in TEST_NOTES or s.get("label") not in ("human", "agent")):
            reason = "test of the setup"
        if reason is None and s.get("label") == "agent" and setup.get("agent") not in STUDY_AGENT_VERSIONS:
            reason = "older version of the agent"
        if reason is None and not s.get("started"):
            reason = "never started"
        result.append({"session": code, "label": s.get("label"), "model": s.get("model"), "run": run,
                       "browser": setup.get("browser"), "motion": setup.get("motion"), "effort": setup.get("effort"),
                       "agent": setup.get("agent"),
                       "created": s.get("created"), "in_study": reason is None, "reason": reason})
    return result


def study_sessions(data_dir):
    """The sessions that the analysis uses."""
    return [s for s in sessions(data_dir) if s["in_study"]]
