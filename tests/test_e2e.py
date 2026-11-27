"""Do the four study tasks in a real browser, as a simple scripted user."""

import json

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

    lines = (shop["data"] / "events" / f"{code}.jsonl").read_text().splitlines()
    events = {e["type"]: e for e in map(json.loads, lines)}
    assert {i["product"] for i in events["order"]["items"]} == {"ridge-runner", "alder-trek"}
    assert events["order"]["fields"]["delivery"] == "standard"
    assert events["contact"]["fields"]["order"] == order
