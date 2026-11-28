"""Tests of the session replay: the same log must give the same video."""

import hashlib
import time

import pytest

from src.replay import Replay, factor_pair, load_session, patch_captcha

playwright = pytest.importorskip("playwright.sync_api")


def test_factor_pair_is_in_the_captcha_range():
    assert factor_pair(640) == (16, 40)
    assert factor_pair(7) is None


def test_patch_captcha_shows_the_codes_of_the_session():
    source = ("  const reference = x;\n  const termsCode = y;\n  const a = 1;\n  const b = 2;\n"
              "  const TERMS = [\n")
    events = [
        {"type": "order", "order": "PS-1", "fields": {"check_reference": "abcd-efgh", "check_terms": "1234", "check_product": "640"}},
        {"type": "captcha", "captcha": "retype-code", "ok": True},
        {"type": "captcha", "captcha": "terms-code", "ok": True},
        {"type": "captcha", "captcha": "multiply", "ok": False},
    ]
    patched = patch_captcha(source, events)
    assert 'reference = "ABCD-EFGH";' in patched and 'termsCode = "1234";' in patched
    assert "a = 16" not in patched  # A wrong answer does not tell the numbers.


def test_same_log_gives_same_video(shop, tmp_path):
    store, url = shop["store"], shop["url"]
    code = store.new_session("bot", note="replay test")
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 1000, "height": 700}).new_page()
        page.goto(f"{url}/s/{code}?next=/product.html?id=ridge-runner")
        page.wait_for_load_state("networkidle")
        page.mouse.move(200, 200, steps=5)
        page.click("text=43")
        page.click("#add-to-cart")
        page.mouse.wheel(0, 400)
        page.wait_for_timeout(500)
        page.goto(url + "/contact.html")
        page.click("#c-message")
        page.keyboard.type("Hello", delay=50)
        page.goto(url + "/info.html")
        time.sleep(1)

        events = load_session(shop["data"] / "events" / f"{code}.jsonl")
        digests = []
        for run in range(2):
            out = tmp_path / f"run{run}.mp4"
            replay_code = store.new_session("bot", note="replay")
            frames = Replay(events, url, browser, fps=5, speed=1).run(replay_code, out)
            assert frames > 10
            digests.append(hashlib.md5(out.read_bytes()).hexdigest())
        browser.close()
    assert digests[0] == digests[1]
