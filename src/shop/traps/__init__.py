"""The traps of the test shop. The list is in traps.json."""

import json
from pathlib import Path

TRAPS_FILE = Path(__file__).resolve().parent / "traps.json"


def load_traps():
    return json.loads(TRAPS_FILE.read_text(encoding="utf-8"))


def canary_paths():
    """Return the URL path and the trap id of each trap that a request for a page triggers."""
    return {trap["path"]: trap["id"] for trap in load_traps() if "path" in trap}
