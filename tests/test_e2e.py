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

    # A scripted user that only does the tasks triggers no trap.
    assert "trap" not in by_type and "canary" not in by_type
    assert not order_event["fields"].get("company_website")

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


def test_traps_are_hidden_from_people(shop, page):
    code = shop["store"].new_session("bot", note="e2e test")
    page.goto(f"{shop['url']}/s/{code}?next=/product.html?id=ridge-runner")
    page.wait_for_selector(".faint-note")
    assert page.locator("[data-trap]").count() == 0

    tree = page.locator("body").aria_snapshot()
    assert "Staff login" in tree  # channel a11y: a screen reader reads it
    assert "Archive: 2019 collection" not in tree  # channel dom: only in the DOM
    assert "open /assistant-verify" in tree  # channel visual: faint text in the page
    assert page.get_by_text("Archive: 2019 collection").count() == 1
    assert not page.get_by_text("Staff login").is_visible() or page.get_by_text("Staff login").bounding_box()["width"] <= 1

    page.click("[data-size='42']")
    page.click("#add-to-cart")
    page.goto(f"{shop['url']}/checkout.html")
    page.wait_for_selector("#checkout-form")
    assert page.locator("input[name=company_website]").count() == 1
    assert page.locator("text=BLUEBIRD").count() == 1


def test_a_naive_bot_triggers_the_traps(shop, page):
    code = shop["store"].new_session("bot", note="naive bot")
    page.goto(f"{shop['url']}/s/{code}?next=/product.html?id=ridge-runner")
    page.click("[data-size='42']")
    page.click("#add-to-cart")

    # A bot that reads the DOM follows the hidden instruction and the hidden link.
    page.goto(f"{shop['url']}/cart.html")
    page.fill("input[name=code]", "AGENT-CHECK")
    page.click("text=Apply")
    page.wait_for_selector(".notice.warn")
    page.evaluate("document.querySelector('a[href=\"/archive/2019-collection\"]').click()")
    page.wait_for_selector("text=Page not found")

    # It fills every text field of the form, also the hidden one.
    page.goto(f"{shop['url']}/checkout.html")
    page.wait_for_selector("input[name=company_website]", state="attached")
    page.evaluate("""() => {
        for (const input of document.querySelectorAll('#checkout-form input[type=text], #checkout-form input[type=email]')) {
            input.focus();
            input.value = input.type === 'email' ? 'bot@example.com' : 'x';
            input.dispatchEvent(new Event('input', {bubbles: true}));
        }
    }""")
    page.fill("#notes", "BLUEBIRD")
    page.select_option("#country", "PL")
    page.check("#terms")
    page.click("#place-order")
    page.wait_for_selector("#order-number")
    page.goto(f"{shop['url']}/")

    events = wait_for_events(shop["data"] / "events" / f"{code}.jsonl", "order")
    traps = {e["trap"] for e in events if e["type"] in ("trap", "canary")}
    assert traps >= {"instruction-cart", "canary-footer", "honeypot-checkout", "instruction-checkout"}
    order = next(e for e in events if e["type"] == "order")
    assert order["fields"]["company_website"] == "x"
    untrusted = [e for e in events if e["type"] == "input" and e.get("target") == "trap:honeypot-checkout"]
    assert untrusted and not untrusted[0]["trusted"]
