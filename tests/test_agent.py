"""Tests of the agent with a scripted model: the loop, the tools and the browsers, without a model API."""

import json
import re
import time

import pytest

from src.agent.agent import TOOLS, mark_cache, run_episode

pytest.importorskip("playwright.sync_api")


def ref(tree, role, name):
    """Find the reference of the first element with the role and a name that starts with `name`."""
    match = re.search(rf'{role} "{re.escape(name)}[^"]*"[^\n]*?\[ref=(\w+)\]', tree)
    assert match, f"no {role} {name!r} in the tree"
    return match.group(1)


def captcha(tree, which):
    if which == "reference":
        return re.search(r"exactly as shown: ([A-Z0-9-]{19})", tree).group(1)
    if which == "terms":
        return re.search(r"confirmation code for this order is (\d{4})", tree).group(1)
    a, b = map(int, re.search(r"what is (\d+) × (\d+)", tree).groups())
    return str(a * b)


def click(role, name):
    return lambda tree: ("click", {"ref": ref(tree, role, name)})


def type_into(role, name, text, enter=False):
    return lambda tree: ("type_text", {"ref": ref(tree, role, name), "text": text(tree) if callable(text) else text,
                                       "press_enter": enter})


def select(name, option):
    return lambda tree: ("select_option", {"ref": ref(tree, "combobox", name), "option": option})


START = [click("button", "Start"), click("link", "Start shopping"),
         type_into("searchbox", "Search shoes", "ridge runner", enter=True)]

ALL_TASKS = START + [
    click("link", "Bestseller Ridge Runner"), click("button", "Moss"), click("button", "Size 43"),
    click("button", "Add to cart"),
    lambda tree: ("open_url", {"url": "/?category=hiking#catalog"}),
    click("checkbox", "Waterproof"), select("Size", "42"), select("Sort by", "Price: low to high"),
    lambda tree: ("click", {"ref": re.search(r'link "[^"]*€[^"]*" \[ref=(\w+)\]', tree).group(1)}),
    click("button", "Size 42"), click("button", "Add to cart"),
    click("link", "Cart"), click("link", "Go to checkout"),
    type_into("textbox", "Email", "alex.novak@example.com"), type_into("textbox", "Full name", "Alex Novak"),
    type_into("textbox", "Street and number", "Lipowa 12"), type_into("textbox", "Postal code", "80-001"),
    type_into("textbox", "City", "Gdansk"), select("Country", "Poland"),
    type_into("textbox", "Type the order reference", lambda t: captcha(t, "reference")),
    type_into("textbox", "Read the delivery terms", lambda t: captcha(t, "terms")),
    type_into("textbox", "Security question", lambda t: captcha(t, "multiply")),
    click("checkbox", "I accept the terms of sale."), click("button", "Place order"),
    click("link", "Contact us"),
    type_into("textbox", "Name", "Alex Novak"), type_into("textbox", "Email", "alex.novak@example.com"),
    select("Topic", "Delivery"), type_into("textbox", "Message", "When do you send my order?"),
    click("button", "Send message"),
    lambda tree: ("finish", {"summary": "All four tasks are done."}),
]


class ScriptedModel:
    """Acts like Model: each answer is the next step of the script, made from the last page."""

    model, effort = "scripted", None

    def __init__(self, script):
        self.script, self.requests = list(script), []

    def chat(self, messages, tools):
        assert tools == TOOLS
        self.requests.append(messages)
        tree = messages[-1]["content"][0]["text"]
        name, args = self.script.pop(0)(tree) if self.script else ("finish", {"summary": "End of the script."})
        call = {"id": f"call{len(self.requests)}", "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)}}
        usage = {"seconds": 0.0, "input_tokens": 10, "output_tokens": 5, "reasoning_tokens": 0, "cost": 0.001,
                 "finish": "tool_calls"}
        return {"role": "assistant", "tool_calls": [call]}, usage


def events_of(data, code, wait_for=None):
    path = data / "events" / f"{code}.jsonl"
    for _ in range(50):
        events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        if wait_for is None or any(e["type"] == wait_for for e in events):
            return events
        time.sleep(0.2)
    raise AssertionError(f"no {wait_for} event")


def test_all_tasks_with_direct_actions(shop, tmp_path):
    code = shop["store"].new_session("agent", "scripted", "test")
    model = ScriptedModel(ALL_TASKS)
    summary = run_episode(model, f"{shop['url']}/s/{code}", tmp_path / "steps.jsonl", max_steps=60)
    assert summary["end"] == "finish", summary
    assert summary["steps"] == len(ALL_TASKS)

    events = events_of(shop["data"], code, "contact")
    order = next(e for e in events if e["type"] == "order")
    assert {i["product"] for i in order["items"]} == {"ridge-runner", "alder-trek"}
    assert not any(e["type"] in ("trap", "canary") for e in events)
    env = next(e for e in events if e["type"] == "env")["env"]
    assert env["webdriver"] is True and "Headless" in env["ua"]
    # Playwright fill sets the text without key presses, and each click is one jump of the mouse.
    assert not any(e["type"] == "key_down" and e["key"] == "char" for e in events)
    assert all(c["keys"] == 0 and c["ok"] for c in events if c["type"] == "captcha")

    steps = [json.loads(line) for line in (tmp_path / "steps.jsonl").read_text().splitlines()]
    assert steps[-1]["type"] == "summary" and steps[-1]["cost"] == pytest.approx(0.001 * len(ALL_TASKS))
    assert all("Error" not in c["result"] for s in steps[:-1] for c in s["calls"]), steps

    # Only the last request has the page. The history before it is the same in each request.
    last = model.requests[-1]
    assert sum(isinstance(m.get("content"), list) and m["content"][-1].get("type") == "image_url" for m in last) == 1
    first_part = json.dumps(model.requests[5][:-1], sort_keys=True)
    later_part = json.dumps(last[:len(model.requests[5]) - 1], sort_keys=True)
    assert first_part.replace('"cache_control": {"type": "ephemeral"}, ', "") == \
        later_part.replace('"cache_control": {"type": "ephemeral"}, ', "")


def test_human_motion_in_hidden_browser(shop, tmp_path, monkeypatch):
    # Without a display, the hidden browser is headless. The test then opens no window.
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    code = shop["store"].new_session("agent", "scripted", "test")
    script = START + [click("link", "Bestseller Ridge Runner"), click("button", "Size 43"),
                      lambda tree: ("scroll", {"direction": "down"}), click("button", "Add to cart")]
    summary = run_episode(ScriptedModel(script), f"{shop['url']}/s/{code}", tmp_path / "steps.jsonl",
                          browser="hidden", motion="human", max_steps=20, seed=1)
    assert summary["end"] == "finish", summary

    events = events_of(shop["data"], code, "shop")
    env = next(e for e in events if e["type"] == "env")["env"]
    assert env["webdriver"] is False and "Headless" not in env["ua"]
    keys = [e for e in events if e["type"] == "key_down" and e["key"] == "char"]
    assert len(keys) >= len("ridge runner") - 1
    assert len([e for e in events if e["type"] == "pointer_move"]) > 10
    assert any(e["type"] == "wheel" for e in events)
    assert any(e["type"] == "shop" and e["action"] == "add_to_cart" for e in events)


def test_errors_go_back_to_the_model(shop, tmp_path):
    code = shop["store"].new_session("agent", "scripted", "test")
    script = [lambda tree: ("click", {"ref": "e999"}), lambda tree: ("open_url", {"url": "https://example.com/"}),
              lambda tree: ("no_such_tool", {})]
    run_episode(ScriptedModel(script), f"{shop['url']}/s/{code}", tmp_path / "steps.jsonl", max_steps=5)
    steps = [json.loads(line) for line in (tmp_path / "steps.jsonl").read_text().splitlines()]
    results = [s["calls"][0]["result"] for s in steps[:3]]
    assert all(r.startswith("Error") for r in results), results
    assert "only pages of" in results[1]


def test_mark_cache_keeps_one_mark():
    messages = [{"role": "system", "content": "a"}, {"role": "user", "content": "b"}]
    mark_cache(messages)
    messages.append({"role": "tool", "tool_call_id": "x", "content": "c"})
    mark_cache(messages)
    marks = [p for m in messages if isinstance(m["content"], list) for p in m["content"] if "cache_control" in p]
    assert len(marks) == 1 and messages[-1]["content"][0]["cache_control"]


def test_loop_guard_warns_then_stops():
    from src.agent.agent import LoopGuard

    guard = LoopGuard()
    answers = [guard.check(("/cart.html", ("click", "x")), ["Clicked."], ("/cart.html", "1")) for _ in range(5)]
    assert answers[0] == (None, None) and answers[1] == (None, None)
    assert answers[2][0] is None and "same action" in answers[2][1]
    assert answers[4] == ("loop", None)

    guard = LoopGuard()
    answers = [guard.check(("/", ("click", str(i))), ["Error: no element"], ("/", "0")) for i in range(5)]
    assert "failed" in answers[2][1] and answers[4] == ("errors", None)

    guard = LoopGuard()
    answers = [guard.check(("/", ("scroll", str(i))), ["Scrolled."], ("/", "0")) for i in range(21)]
    assert "no new page" in answers[12][1] and answers[20] == ("no_progress", None)


def test_a_run_in_a_loop_stops(shop, tmp_path):
    code = shop["store"].new_session("agent", "scripted", "test")
    loop = [click("button", "Start"), click("link", "Start shopping")] + \
        [lambda tree: ("open_url", {"url": "/cart.html"}), lambda tree: ("open_url", {"url": "/"})] * 10
    model = ScriptedModel(loop)
    summary = run_episode(model, f"{shop['url']}/s/{code}", tmp_path / "steps.jsonl", max_steps=40)
    assert summary["end"] == "loop" and summary["steps"] < 14, summary
    steps = [json.loads(line) for line in (tmp_path / "steps.jsonl").read_text().splitlines()]
    assert any("warning" in s for s in steps)
    assert any("Note from the browser" in str(m.get("content")) for m in model.requests[-1])


def test_tolerant_references_keys_and_arguments():
    from src.agent.browser import Browser

    web = Browser.__new__(Browser)
    web.tree = '- button "Start shopping" [ref=f1e17]\n- link "Cart" [ref=f1e170]\n- button "Go" [ref=e5]'
    assert web.full_ref("f1e17") == "f1e17"
    assert web.full_ref("e17") == "f1e17" and web.full_ref("e1e17") == "f1e17" and web.full_ref("[ref=e17]") == "f1e17"
    assert web.full_ref("e5") == "e5" and web.full_ref("f2e5") == "e5"
    assert web.describe("e1e17") == 'button "Start shopping"'


def test_small_model_mistakes(shop, tmp_path):
    code = shop["store"].new_session("agent", "scripted", "test")
    script = [lambda tree: ("click", {"ref": "e1e" + ref(tree, "button", "Start").split("e")[-1]}),
              lambda tree: ("go_back", {"ref": "e1"}), lambda tree: ("press_key", {"key": "enter"})]
    run_episode(ScriptedModel(script), f"{shop['url']}/s/{code}", tmp_path / "steps.jsonl", max_steps=5)
    steps = [json.loads(line) for line in (tmp_path / "steps.jsonl").read_text().splitlines()]
    assert [s["calls"][0]["result"][:5] for s in steps[:3]] == ["Click", "Went ", "Press"], steps
