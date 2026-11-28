"""Tests of the event logger in real browsers. People, agents and scripts must give the correct events."""

import json
import time

import pytest

playwright = pytest.importorskip("playwright.sync_api")

BROWSERS = ["chromium", "firefox", "webkit"]
VIEWPORT = {"width": 1280, "height": 800}


@pytest.fixture(scope="module")
def pw():
    with playwright.sync_playwright() as p:
        yield p


@pytest.fixture(params=BROWSERS)
def browser(request, pw):
    try:
        browser = getattr(pw, request.param).launch()
    except Exception as error:
        pytest.skip(f"{request.param} cannot start: {str(error).splitlines()[0]}")
    yield browser
    browser.close()


class Session:
    """One study session in its own browser context."""

    def __init__(self, shop, browser, path="/", **options):
        self.shop = shop
        self.code = shop["store"].new_session("bot", note="logger test")
        self.context = browser.new_context(viewport=VIEWPORT, **options)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.open(f"/s/{self.code}?next={path}")

    def open(self, path, page=None):
        page = page or self.page
        page.goto(self.shop["url"] + path)
        page.wait_for_load_state("networkidle")

    def events(self, done=lambda found: True, timeout=10):
        """Wait until the log file has the expected events. A page change sends the last events."""
        path = self.shop["data"] / "events" / f"{self.code}.jsonl"
        deadline = time.time() + timeout
        found = []
        while time.time() < deadline:
            found = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
            if done(found):
                return found
            time.sleep(0.2)
        raise AssertionError(f"the events are not complete: {sorted({e['type'] for e in found})}")

    def leave_and_read(self, pages=1):
        """Go to a different page, then read the events of the pages that are closed."""
        self.open("/info.html")
        events = self.events(lambda found: count(found, "page_hide") >= pages)
        assert self.errors == []
        return events


def count(events, kind, **match):
    return len(of(events, kind, **match))


def of(events, kind, **match):
    return [e for e in events if e["type"] == kind and all(e.get(k) == v for k, v in match.items())]


def test_typing_with_a_correction(shop, browser):
    s = Session(shop, browser, "/contact.html")
    s.page.click("#c-message")
    s.page.keyboard.type("Hello wrld", delay=40)
    for _ in range(4):
        s.page.keyboard.press("Backspace", delay=30)
    s.page.keyboard.type("world", delay=40)
    events = s.leave_and_read()

    target = "textarea#c-message"
    keys = [e for e in of(events, "key_down", target=target) if e["key"] != "Shift"]
    assert len(keys) == 19
    assert [e["key"] for e in keys].count("Backspace") == 4
    assert count(events, "key_up", target=target) >= 19
    inputs = of(events, "input", target=target)
    values = [e["value"] for e in inputs]
    assert values[9] == "Hello wrld" and values[13] == "Hello " and values[-1] == "Hello world"
    assert {e["itype"] for e in inputs} == {"insertText", "deleteContentBackward"}
    assert all(e["trusted"] for e in keys + inputs)
    assert all(e["len"] == len(e["value"]) for e in inputs)


def test_fill_gives_text_without_key_events(shop, browser):
    s = Session(shop, browser, "/contact.html")
    s.page.fill("#c-name", "Alex Novak")
    s.page.fill("#c-message", "x" * 400)
    events = s.leave_and_read()

    assert count(events, "key_down", target="input#c-name") == 0
    name = of(events, "input", target="input#c-name")
    assert [e["value"] for e in name] == ["Alex Novak"]
    long_text = of(events, "input", target="textarea#c-message")[-1]
    assert long_text["len"] == 400 and long_text["value"] == "x" * 300


def test_events_from_a_script_are_not_trusted(shop, browser):
    s = Session(shop, browser, "/contact.html")
    s.page.evaluate("""() => {
        const field = document.querySelector('#c-order');
        field.value = 'PS-123456';
        field.dispatchEvent(new Event('input', { bubbles: true }));
        document.querySelector('#shopping-list button').click();
    }""")
    events = s.leave_and_read()

    change = of(events, "input", target="input#c-order")[0]
    assert change["value"] == "PS-123456" and change["itype"] == "" and change["trusted"] is False
    click = of(events, "click", text="Hide")[0]
    assert click["trusted"] is False
    assert count(events, "pointer_down") == 0


def test_copy_and_paste_with_the_keyboard(shop, browser):
    s = Session(shop, browser, "/contact.html")
    modifier = "ControlOrMeta"  # Meta on macOS, Control on Linux and Windows
    s.page.fill("#c-name", "PS-123456")
    s.page.click("#c-name")
    s.page.keyboard.press(f"{modifier}+A")
    s.page.keyboard.press(f"{modifier}+C")
    s.page.click("#c-order")
    s.page.keyboard.press(f"{modifier}+V")
    events = s.leave_and_read()

    assert of(events, "copy")[0]["len"] == 9
    paste = of(events, "paste", target="input#c-order")
    assert len(paste) == 1 and paste[0]["len"] == 9
    pasted = of(events, "input", target="input#c-order")[-1]
    assert pasted["value"] == "PS-123456" and pasted["itype"] == "insertFromPaste"


def test_mouse_wheel_and_resize(shop, browser):
    s = Session(shop, browser, "/")
    s.page.mouse.move(100, 100)
    s.page.mouse.move(800, 500, steps=60)
    s.page.mouse.wheel(0, 600)
    s.page.wait_for_function("scrollY > 0")
    time.sleep(0.3)
    final_scroll = s.page.evaluate("scrollY")
    s.page.set_viewport_size({"width": 1000, "height": 700})
    # WebKit sends the resize event with the next frame.
    s.page.wait_for_function("innerWidth === 1000")
    time.sleep(0.5)
    events = s.leave_and_read()

    moves = of(events, "pointer_move")
    assert len(moves) >= 3
    assert all(e["ptype"] == "mouse" for e in moves)
    assert all(0 <= e["x"] <= VIEWPORT["width"] and 0 <= e["y"] <= VIEWPORT["height"] for e in moves)
    assert max(e["x"] for e in moves) >= 600
    # The logger keeps one pointer_move in 50 ms and the last one of a series, in the order of time.
    times = [e["t"] for e in moves]
    assert times == sorted(times) and len(moves) <= 2 * (times[-1] - times[0]) / 50 + 2
    assert (moves[-1]["x"], moves[-1]["y"]) == (800, 500)
    assert of(events, "wheel")[0]["dy"] > 0
    assert of(events, "scroll")[-1]["sy"] == final_scroll
    assert {"w": 1000, "h": 700}.items() <= of(events, "resize")[-1].items()


def test_every_event_arrives(shop, browser):
    s = Session(shop, browser, "/contact.html")
    # More than 100 events on one page: the logger sends a batch before the page ends.
    s.page.click("#c-message")
    s.page.keyboard.type("a" * 120)
    for path in ("/product.html?id=ridge-runner", "/cart.html", "/checkout.html", "/"):
        s.open(path)
        s.page.mouse.move(300, 300)
        s.page.mouse.click(5, 300)
    events = s.leave_and_read(pages=5)

    by_page = {}
    for event in of_client(events):
        by_page.setdefault(event["page"], []).append(event)
    closed = [p for p, items in by_page.items() if any(e["type"] == "page_hide" for e in items)]
    assert len(closed) == 5
    for page_id in closed:
        items = sorted(by_page[page_id], key=lambda e: e["seq"])
        assert [e["seq"] for e in items] == list(range(len(items))), "an event is lost or doubled"
        assert items[0]["type"] == "page_view"
        assert all(a["t"] <= b["t"] for a, b in zip(items, items[1:]))
        assert len({e["path"] for e in items}) == 1
    assert count(events, "key_down", target="textarea#c-message") == 120


def test_failed_requests_lose_no_event(shop, browser):
    # Through a public tunnel, requests can fail for some seconds. The logger must send the events again.
    s = Session(shop, browser, "/contact.html")
    s.page.route("**/api/events", lambda route: route.abort())
    s.page.click("#c-message")
    s.page.keyboard.type("a" * 150)
    s.page.wait_for_timeout(2500)
    # The beacons of the page end also fail. The next page sends the events from sessionStorage.
    s.open("/cart.html")
    s.page.unroute("**/api/events")
    # WebKit reports each blocked request as a page error. Only the errors after the block count.
    s.errors.clear()
    s.events(lambda found: count(found, "key_down", target="textarea#c-message") == 150)
    events = s.leave_and_read(pages=2)

    by_page = {}
    for event in of_client(events):
        by_page.setdefault(event["page"], []).append(event)
    closed = [items for items in by_page.values() if any(e["type"] == "page_hide" for e in items)]
    assert len(closed) == 2
    for items in closed:
        seqs = sorted(e["seq"] for e in items)
        assert seqs == list(range(len(seqs))), "an event is lost or doubled"
    assert count(events, "key_down", target="textarea#c-message") == 150


def of_client(events):
    return [e for e in events if e["src"] == "client"]


def test_browser_fingerprint(shop, browser):
    s = Session(shop, browser, "/")
    events = s.leave_and_read()

    env = of(events, "env")[0]["env"]
    assert env["window"] == "1280x800"
    assert env["ua"] and env["languages"] and env["tz"] and env["screen"]
    assert env["webdriver"] in (True, False)
    view = of(events, "page_view")[0]
    assert view["path"] == "/" and "Pace & Sole" in view["title"]


def test_two_tabs_of_one_session(shop, browser):
    s = Session(shop, browser, "/")
    second = s.context.new_page()
    s.open("/contact.html", page=second)
    second.mouse.click(5, 300)
    s.open("/info.html", page=second)
    s.open("/info.html")
    # The open pages send their events every 2 s.
    events = s.events(lambda found: count(found, "page_view") >= 4 and count(found, "page_hide") >= 2)

    pages = {e["page"] for e in of(events, "page_view")}
    assert len(pages) == 4
    assert {e["path"] for e in of(events, "page_view")} >= {"/", "/contact.html", "/info.html"}


def test_touch_gives_touch_events(shop, browser):
    if browser.browser_type.name == "firefox":
        pytest.skip("Playwright has no touch screen for Firefox")
    s = Session(shop, browser, "/", has_touch=True)
    s.page.tap(".hero .btn")
    s.page.wait_for_load_state("networkidle")
    events = s.leave_and_read()

    down = of(events, "pointer_down")
    assert down and all(e["ptype"] == "touch" for e in down)
    if browser.browser_type.name == "chromium":  # Playwright sets maxTouchPoints only in Chromium.
        assert of(events, "env")[0]["env"]["touch"] > 0


def test_no_events_without_a_session(shop, browser):
    context = browser.new_context(viewport=VIEWPORT)
    page = context.new_page()
    sent = []
    page.on("request", lambda r: sent.append(r.url) if "/api/events" in r.url else None)
    for path in ("/", "/product.html?id=ridge-runner", "/contact.html"):
        page.goto(shop["url"] + path)
        page.wait_for_load_state("networkidle")
        page.mouse.move(200, 200)
        page.mouse.click(5, 300)
    page.fill("#c-name", "Somebody")
    page.goto(shop["url"] + "/")
    page.wait_for_load_state("networkidle")
    time.sleep(2.5)

    assert sent == []
    assert page.locator("#shopping-list").count() == 0
    assert page.evaluate("typeof window.psAnalytics.log") == "function"
    assert list((shop["data"] / "events").glob("*.jsonl")) == []
    context.close()


def test_logger_stops_after_the_end_of_the_session(shop, browser):
    s = Session(shop, browser, "/")
    shop["store"].mark(s.code, "ordered")
    shop["store"].mark(s.code, "closed")
    shop["store"].grace_ms = 0
    sent = []
    s.page.on("request", lambda r: sent.append(r.url) if "/api/events" in r.url else None)
    for x in range(10):
        s.page.mouse.move(100 + 50 * x, 300)
        time.sleep(0.7)
    assert len(sent) == 1  # The server refused the first batch, so the logger sent no more.


def test_fast_scroll_keeps_the_last_position(shop, browser):
    s = Session(shop, browser, "/")
    for _ in range(15):
        s.page.mouse.wheel(0, 90)
        time.sleep(0.02)
    s.page.wait_for_timeout(300)
    final = s.page.evaluate("scrollY")
    events = s.leave_and_read()

    scrolls = of(events, "scroll")
    assert final > 0 and scrolls[-1]["sy"] == final
    page_events = sorted((e for e in of_client(events) if e["page"] == scrolls[0]["page"]), key=lambda e: e["seq"])
    assert all(a["t"] <= b["t"] for a, b in zip(page_events, page_events[1:]))
