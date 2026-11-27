"""Do the four study tasks in a real browser, as a simple scripted user."""

import json
import time

import pytest

playwright = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def page():
    with playwright.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 860})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        yield page
        browser.close()
        assert errors == []


def test_all_tasks(shop, page):
    code = shop["store"].new_session("bot", note="e2e test")
    page.goto(f"{shop['url']}/s/{code}")
    assert page.locator("#task-list li").count() == 4
    page.click("#start")

    page.fill(".search input", "ridge runner")
    page.press(".search input", "Enter")
    page.click(".product-card")
    page.click("[data-color=Moss]")
    page.click("[data-size='43']")
    page.click("#add-to-cart")
    page.wait_for_selector(".notice.ok")

    page.goto(f"{shop['url']}/?category=hiking#catalog")
    page.check("#filter-waterproof")
    page.select_option("#filter-size", "42")
    page.select_option("#sort", "price-asc")
    page.click(".product-card >> nth=0")
    assert page.inner_text("h1") == "Alder Trek WP"
    page.click("[data-size='42']")
    page.click("#add-to-cart")

    page.click(".cart-link")
    page.click("#checkout-link")
    for field, value in {"email": "alex.novak@example.com", "name": "Alex Novak", "street": "Lipowa 12",
                         "postcode": "80-001", "city": "Gdansk"}.items():
        page.fill(f"#{field}", value)
    page.select_option("#country", "PL")
    page.check("#terms")
    page.click("#place-order")
    order = page.inner_text("#order-number")

    page.goto(f"{shop['url']}/contact.html")
    page.fill("#c-name", "Alex Novak")
    page.fill("#c-email", "alex.novak@example.com")
    page.fill("#c-order", order)
    page.select_option("#c-topic", "returns")
    page.fill("#c-message", "Can I return the boots after 40 days?")
    page.click("text=Send message")
    page.wait_for_selector(".notice.ok")

    page.goto(f"{shop['url']}/")  # The page change sends the last events.
    events = wait_for_events(shop["data"] / "events" / f"{code}.jsonl", "contact")
    by_type = {}
    for event in events:
        by_type.setdefault(event["type"], []).append(event)

    order_event = by_type["order"][0]
    assert {i["product"] for i in order_event["items"]} == {"ridge-runner", "alder-trek"}
    assert order_event["fields"]["delivery"] == "standard"
    assert by_type["contact"][0]["fields"]["order"] == order

    # The logger records the behavior on all pages.
    for kind in ("page_view", "env", "pointer_move", "click", "key_down", "input", "change", "focus", "shop"):
        assert kind in by_type, kind
    assert by_type["env"][0]["env"]["webdriver"] is True
    assert all(e["trusted"] for e in by_type["click"])
    assert {e["action"] for e in by_type["shop"]} >= {"view_item", "add_to_cart", "search", "filter", "sort"}

    # The client events hold the length of a text, not the text.
    client_text = json.dumps([e for e in events if e["src"] == "client"])
    assert "Lipowa" not in client_text and "alex.novak" not in client_text
    assert {e["key"] for e in by_type["key_down"]} <= {"char", "digit", "space", "Enter", "Backspace", "Shift", "Tab"}


def wait_for_events(path, last_type, timeout=5.0):
    """Wait until the file has an event of last_type and its size stays the same."""
    end, size = time.time() + timeout, -1
    while time.time() < end:
        text = path.read_text() if path.exists() else ""
        if f'"type": "{last_type}"' in text and len(text) == size:
            break
        size = len(text)
        time.sleep(0.3)
    return [json.loads(line) for line in path.read_text().splitlines()]
