import json
import re
from pathlib import Path

from src.shop.traps import canary_paths, load_traps
from tests.test_server import get, session_events

TRAPS_JS = Path("src/shop/traps/traps.js").read_text(encoding="utf-8")


def test_registry_and_script_agree():
    """traps.json (for the analysis) and traps.js (for the page) must describe the same traps."""
    js_ids = set(re.findall(r'id: "([a-z0-9-]+)"', TRAPS_JS))
    traps = load_traps()
    assert js_ids == {t["id"] for t in traps}
    for trap in traps:
        for key in ("text", "value", "path", "field"):
            if key in trap:
                assert trap[key] in TRAPS_JS, (trap["id"], key)
    assert {t["channel"] for t in traps} == {"dom", "a11y", "visual"}
    assert {t["kind"] for t in traps} == {"honeypot", "instruction", "canary"}


def test_canary_request_is_logged_and_looks_like_a_missing_page(shop):
    code = shop["store"].new_session("agent", model="m")
    for path, trap in canary_paths().items():
        response = get(shop["url"] + path, cookie=f"ps_sid={code}")
        assert response.status == 404
        assert b"Page not found" in response.read()
    logged = {e["trap"] for e in session_events(shop, code) if e["type"] == "canary"}
    assert logged == set(canary_paths().values())


def test_any_missing_page_gets_the_same_answer(shop):
    missing = get(shop["url"] + "/no-such-page")
    canary = get(shop["url"] + "/staff/login")
    assert missing.status == canary.status == 404
    assert missing.read() == canary.read()


def test_public_scripts_have_no_comments(shop):
    for path in ("/assets/js/widgets.js", "/assets/js/analytics.js"):
        source = get(shop["url"] + path).read().decode()
        assert "//" not in "\n".join(line.strip()[:2] for line in source.splitlines())
    assert "trap" not in json.dumps(get(shop["url"] + "/checkout.html").read().decode())
