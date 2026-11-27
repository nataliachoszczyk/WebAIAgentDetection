import json
import re
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


# Words that tell a visitor that the shop is a test. An agent that reads them can act in a different way.
STUDY_WORDS = re.compile(r"\b(study|studies|demo|universit\w*|research|experiment\w*|wad)\b", re.I)


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
    assert response.headers["Location"] == "/start.html"
    cookies = response.headers.get_all("Set-Cookie")
    assert any(c.startswith(f"ps_sid={code};") and "HttpOnly" in c for c in cookies)
    assert session_events(shop, code)[0]["type"] == "session_start"


def test_session_link_rejects_unknown_code_and_open_redirect(shop):
    assert get(shop["url"] + "/s/unknown").status == 404
    code = shop["store"].new_session("agent", model="m")
    assert get(f"{shop['url']}/s/{code}?next=//evil.example").headers["Location"] == "/start.html"
    assert get(f"{shop['url']}/s/{code}?next=/cart.html").headers["Location"] == "/cart.html"


def test_order_is_logged_only_for_a_valid_session(shop):
    order = {"items": [{"product": "ridge-runner", "size": 43, "color": "Moss", "qty": 1}], "total": 129,
             "fields": {"name": "Alex Novak"}}
    code = shop["store"].new_session("human")
    response = json.load(post(shop["url"] + "/api/order", order, cookie=f"ps_sid={code}"))
    assert response["order"].startswith("PS-")
    logged = [e for e in session_events(shop, code) if e["type"] == "order"]
    assert logged[0]["order"] == response["order"] and logged[0]["src"] == "server"

    post(shop["url"] + "/api/order", order, cookie="ps_sid=stranger")
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
    assert post(shop["url"] + "/api/events", batch, cookie="ps_sid=stranger").status == 403


def test_events_are_cleaned_and_stored(shop):
    code = shop["store"].new_session("human")
    batch = {"events": [
        {"type": "click", "page": "p", "seq": 0, "t": 1.0, "x": 5, "y": 6, "extra": "drop"},
        {"type": "order", "page": "p", "seq": 1, "t": 2.0},
        {"type": "key_down", "page": "p", "seq": 2, "t": 3.0, "key": "char"},
    ]}
    result = json.load(post(shop["url"] + "/api/events", batch, cookie=f"ps_sid={code}"))
    assert result == {"accepted": 2, "rejected": 1}
    events = session_events(shop, code)
    assert [e["type"] for e in events] == ["click", "key_down"]
    assert "extra" not in events[0] and events[0]["src"] == "client"


def test_too_large_batch_is_rejected(shop):
    code = shop["store"].new_session("human")
    batch = {"events": [{"type": "scroll", "seq": i, "t": i} for i in range(501)]}
    assert post(shop["url"] + "/api/events", batch, cookie=f"ps_sid={code}").status == 400


def test_bad_content_length_gives_400(shop):
    import http.client
    host, port = shop["url"].removeprefix("http://").split(":")
    connection = http.client.HTTPConnection(host, int(port))
    connection.putrequest("POST", "/api/order")
    connection.putheader("Content-Length", "abc")
    connection.endheaders()
    assert connection.getresponse().status == 400


def test_head_gives_the_headers_of_get(shop):
    import http.client
    host, port = shop["url"].removeprefix("http://").split(":")
    connection = http.client.HTTPConnection(host, int(port))
    connection.request("HEAD", "/index.html")
    response = connection.getresponse()
    assert response.status == 200
    assert int(response.getheader("Content-Length")) > 0
    assert response.read() == b""


def test_public_files_do_not_tell_about_the_study(shop):
    from src.shop.server import SCRIPTS, SITE_DIR, PUBLIC_SUFFIXES
    paths = ["/" + str(f.relative_to(SITE_DIR)) for f in SITE_DIR.rglob("*") if f.suffix in PUBLIC_SUFFIXES]
    paths += list(SCRIPTS) + ["/api/tasks"]
    for path in paths:
        text = get(shop["url"] + path).read().decode("utf-8")
        assert not STUDY_WORDS.search(text), (path, STUDY_WORDS.search(text))
    for cookie in get(shop["url"] + "/s/" + shop["store"].new_session("human")).headers.get_all("Set-Cookie"):
        assert not STUDY_WORDS.search(cookie.split("=")[0])


def test_session_continues_and_ends_after_the_contact_message(shop):
    store, url = shop["store"], shop["url"]
    code = store.new_session("human")
    cookie = f"ps_sid={code}"
    assert get(f"{url}/s/{code}").headers["Location"] == "/start.html"
    # A second open continues the session with the same cart.
    assert get(f"{url}/s/{code}", cookie=cookie).headers["Location"] == "/"
    starts = [e for e in session_events(shop, code) if e["type"] == "session_start"]
    assert [e["again"] for e in starts] == [False, True]

    post(url + "/api/contact", {"fields": {"message": "before the order"}}, cookie=cookie)
    assert store.state(code, "closed") is None  # The order comes first.
    post(url + "/api/order", {"items": [{"product": "ridge-runner"}]}, cookie=cookie)
    post(url + "/api/contact", {"fields": {"message": "after the order"}}, cookie=cookie)
    assert store.state(code, "ordered") and store.state(code, "closed")
    assert json.load(get(url + "/api/tasks", cookie=cookie))["done"] is True

    batch = {"events": [{"type": "scroll", "seq": 0, "t": 1, "sx": 0, "sy": 10}]}
    assert post(url + "/api/events", batch, cookie=cookie).status == 200  # the last seconds of the page
    store.grace_ms = 0
    assert post(url + "/api/events", batch, cookie=cookie).status == 403

    done = get(f"{url}/s/{code}", cookie=cookie)
    assert done.status == 200 and b"All tasks are done" in done.read()
    stranger = get(f"{url}/s/{code}")
    assert stranger.status == 410 and b"no longer active" in stranger.read()
    assert not any(c.startswith("ps_sid") for c in stranger.headers.get_all("Set-Cookie") or [])


def test_tasks_are_not_done_without_a_session(shop):
    assert json.load(get(shop["url"] + "/api/tasks"))["done"] is False


def test_join_link_gives_each_browser_its_own_session(shop):
    import time
    store, url = shop["store"], shop["url"]
    secret = store.new_join("human", 2, until=int(time.time() * 1000) + 60_000)

    first = get(f"{url}/join/{secret}")
    assert first.status == 302 and first.headers["Location"] == "/start.html"
    code = first.headers["Set-Cookie"].split("ps_sid=")[1].split(";")[0]
    assert store.sessions()[code]["join"] == secret and store.sessions()[code]["label"] == "human"
    # The same browser opens the link again: the same session, no second place of the limit.
    again = get(f"{url}/join/{secret}", cookie=f"ps_sid={code}")
    assert again.headers["Location"] == "/" and len(store.join_sessions(secret)) == 1

    second = get(f"{url}/join/{secret}")
    assert second.status == 302 and len(store.join_sessions(secret)) == 2
    full = get(f"{url}/join/{secret}")
    assert full.status == 410 and b"no longer active" in full.read()

    store.mark(code, "ordered")
    store.mark(code, "closed")
    assert b"All tasks are done" in get(f"{url}/join/{secret}", cookie=f"ps_sid={code}").read()
    assert get(f"{url}/join/unknown").status == 404


def test_expired_join_link_is_closed(shop):
    import time
    secret = shop["store"].new_join("human", 10, until=int(time.time() * 1000) - 1)
    assert get(f"{shop['url']}/join/{secret}").status == 410
