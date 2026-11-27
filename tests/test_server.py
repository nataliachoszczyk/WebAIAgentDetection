import json
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get(url, cookie=None):
    request = urllib.request.Request(url, headers={"Cookie": cookie} if cookie else {})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        return opener.open(request)
    except urllib.error.HTTPError as error:
        return error


def post(url, body, cookie=None):
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        return urllib.request.urlopen(request)
    except urllib.error.HTTPError as error:
        return error


def session_events(shop, code):
    path = shop["data"] / "events" / f"{code}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_static_pages_and_traversal(shop):
    assert get(shop["url"] + "/").status == 200
    assert get(shop["url"] + "/product.html").status == 200
    assert get(shop["url"] + "/assets/data/products.json").status == 200
    assert get(shop["url"] + "/../server.py").status == 404
    assert get(shop["url"] + "/%2e%2e/server.py").status == 404
    assert get(shop["url"] + "/missing.html").status == 404


def test_tasks_hide_the_expected_answers(shop):
    tasks = json.load(get(shop["url"] + "/api/tasks"))
    assert len(tasks["tasks"]) == 4
    assert "expected" not in tasks


def test_session_link_sets_cookies(shop):
    code = shop["store"].new_session("human")
    response = get(f"{shop['url']}/s/{code}")
    assert response.status == 302
    assert response.headers["Location"] == "/study.html"
    cookies = response.headers.get_all("Set-Cookie")
    assert any(c.startswith(f"wad_sid={code};") and "HttpOnly" in c for c in cookies)
    assert session_events(shop, code)[0]["type"] == "session_start"


def test_session_link_rejects_unknown_code_and_open_redirect(shop):
    assert get(shop["url"] + "/s/unknown").status == 404
    code = shop["store"].new_session("agent", model="m")
    assert get(f"{shop['url']}/s/{code}?next=//evil.example").headers["Location"] == "/study.html"
    assert get(f"{shop['url']}/s/{code}?next=/cart.html").headers["Location"] == "/cart.html"


def test_order_is_logged_only_for_a_valid_session(shop):
    order = {"items": [{"product": "ridge-runner", "size": 43, "color": "Moss", "qty": 1}], "total": 129,
             "fields": {"name": "Alex Novak"}}
    code = shop["store"].new_session("human")
    response = json.load(post(shop["url"] + "/api/order", order, cookie=f"wad_sid={code}"))
    assert response["order"].startswith("PS-")
    logged = [e for e in session_events(shop, code) if e["type"] == "order"]
    assert logged[0]["order"] == response["order"] and logged[0]["src"] == "server"

    post(shop["url"] + "/api/order", order, cookie="wad_sid=stranger")
    assert not (shop["data"] / "events" / "stranger.jsonl").exists()


def test_bad_requests(shop):
    assert post(shop["url"] + "/api/order", {"items": []}).status == 400
    assert post(shop["url"] + "/api/unknown", {}).status == 404


def test_python_files_are_not_public(shop):
    assert get(shop["url"] + "/assets/js/analytics.js").status == 200
    for path in ("/logger/schema.py", "/logger/logger.js", "/server.py", "/tasks.json", "/traps/traps.json"):
        assert get(shop["url"] + path).status == 404, path


def test_events_need_a_session(shop):
    batch = {"events": [{"type": "click", "page": "p", "seq": 0, "t": 1.0}]}
    assert post(shop["url"] + "/api/events", batch).status == 403
    assert post(shop["url"] + "/api/events", batch, cookie="wad_sid=stranger").status == 403


def test_events_are_cleaned_and_stored(shop):
    code = shop["store"].new_session("human")
    batch = {"events": [
        {"type": "click", "page": "p", "seq": 0, "t": 1.0, "x": 5, "y": 6, "extra": "drop"},
        {"type": "order", "page": "p", "seq": 1, "t": 2.0},
        {"type": "key_down", "page": "p", "seq": 2, "t": 3.0, "key": "char"},
    ]}
    result = json.load(post(shop["url"] + "/api/events", batch, cookie=f"wad_sid={code}"))
    assert result == {"accepted": 2, "rejected": 1}
    events = session_events(shop, code)
    assert [e["type"] for e in events] == ["click", "key_down"]
    assert "extra" not in events[0] and events[0]["src"] == "client"


def test_too_large_batch_is_rejected(shop):
    code = shop["store"].new_session("human")
    batch = {"events": [{"type": "scroll", "seq": i, "t": i} for i in range(501)]}
    assert post(shop["url"] + "/api/events", batch, cookie=f"wad_sid={code}").status == 400
