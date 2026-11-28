"""The loop of the agent: observe the page, ask the model, do the tool calls. See docs/agent.md."""

import json
import time
from pathlib import Path

from .browser import Browser

# Change the version when the prompt, the tools or the history change. The note of each session keeps it.
AGENT_VERSION = 2

SYSTEM = """You are a browser agent. You use a web browser for the user and do the tasks that the user gives you.

At each step you get the current page: the URL, the accessibility tree and a screenshot of the visible part of the page. Elements in the tree have references such as [ref=e12]. Give these references to the tools. The references change when the page changes, so always use the references of the last page.

To save space, the history keeps your notes, your tool calls and their results, but not the earlier pages. You saw each page before you acted on it. The last tool result of each step tells which page was open after the step. Use the current page to check the result of your earlier steps.

Before your tool calls, write one short note: what the current page shows, what changed after your last step, and what you do next.

Do the tasks completely and without questions to the user. The user is not available during the work. If you must give data that the user did not give, invent realistic data. When all tasks are done, call the tool finish."""

TASK = "Do the tasks on this website. The page in the browser shows them."


def tool(name, description, properties=None, required=()):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties or {}, "required": list(required)}}}


REF = {"type": "string", "description": "The reference of the element, for example e12"}
TOOLS = [
    tool("click", "Click an element.", {"ref": REF}, ["ref"]),
    tool("type_text", "Replace the text of a text field.", {
        "ref": REF, "text": {"type": "string"},
        "press_enter": {"type": "boolean", "description": "Press Enter after the text"}}, ["ref", "text"]),
    tool("select_option", "Select an option of a drop-down list.", {
        "ref": REF, "option": {"type": "string", "description": "The label or the value of the option"}},
        ["ref", "option"]),
    tool("scroll", "Scroll the page, or the element with the reference, by about one screen.", {
        "direction": {"type": "string", "enum": ["down", "up"]}, "ref": REF}, ["direction"]),
    tool("press_key", "Press a key, for example Enter, Tab or Escape.", {"key": {"type": "string"}}, ["key"]),
    tool("go_back", "Go back to the previous page."),
    tool("open_url", "Open a URL or a path of this website.", {"url": {"type": "string"}}, ["url"]),
    tool("wait", "Wait some seconds.", {"seconds": {"type": "number"}}),
    tool("finish", "Tell the user that all tasks are done.", {
        "summary": {"type": "string", "description": "A short summary of the result for the user"}}, ["summary"]),
]


def observation_message(text, shot):
    return {"role": "user", "content": [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{shot}"}},
    ]}


def mark_cache(messages):
    """Put a cache mark on the last message of the stable history. The next request reads this part from the cache."""
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                part.pop("cache_control", None)
    last = messages[-1]
    if isinstance(last.get("content"), str):
        last["content"] = [{"type": "text", "text": last["content"]}]
    last["content"][-1]["cache_control"] = {"type": "ephemeral"}


def run_episode(model, link, log_path, browser="plain", motion="direct", max_steps=80, max_cost=2.0, seed=None):
    """Do one session from the session link. Write one line for each step into log_path. Return the summary."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    summary = {"type": "summary", "agent": AGENT_VERSION, "link_session": link.rstrip("/").rsplit("/", 1)[-1], "model": model.model,
               "effort": model.effort, "browser": browser, "motion": motion, "steps": 0, "cost": 0.0,
               "input_tokens": 0, "output_tokens": 0, "end": "max_steps", "error": None}
    # The history keeps the answers and the tool results. Only the last request gets the full page.
    # Thus the start of the history stays the same, and the cache of the model API can keep it.
    history = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": TASK}]
    web = Browser(browser, motion, seed)
    with log_path.open("w") as log:
        def write(record):
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            log.flush()

        try:
            web.open(link)
            for step in range(1, max_steps + 1):
                text, shot = web.observe()
                mark_cache(history)
                message, usage = model.chat(history + [observation_message(text, shot)], TOOLS)
                summary["steps"] = step
                summary["cost"] += usage["cost"] or 0
                summary["input_tokens"] += usage["input_tokens"]
                summary["output_tokens"] += usage["output_tokens"]
                calls = message.get("tool_calls") or []
                history.append(message)
                record = {"type": "step", "step": step, "ts": int(time.time() * 1000), "url": web.page.url,
                          "obs": text, "usage": usage, "thoughts": message.get("reasoning"),
                          "text": message.get("content"), "calls": []}
                if not calls:
                    # A model that answers without a tool call stops. The user wants the work done, so ask again.
                    history.append({"role": "user", "content": "Continue with the tools. Call finish when all tasks are done."})
                finished = False
                for call in calls:
                    name = call["function"]["name"]
                    try:
                        args = json.loads(call["function"]["arguments"] or "{}")
                    except json.JSONDecodeError:
                        args = None
                    if name == "finish":
                        result, finished = "The user got the summary.", True
                        summary["finish"] = (args or {}).get("summary")
                    elif args is None or not isinstance(args, dict):
                        result = "Error: the arguments are not valid JSON."
                    elif name not in {t["function"]["name"] for t in TOOLS}:
                        result = f"Error: there is no tool {name}."
                    else:
                        result = web.act(name, args)
                    record["calls"].append({"name": name, "args": args, "result": result,
                                            "ts": int(time.time() * 1000)})
                    history.append({"role": "tool", "tool_call_id": call["id"], "content": result})
                record["url_after"] = web.page.url
                if calls and not finished:
                    history[-1]["content"] += "\n" + web.where()
                write(record)
                if finished:
                    summary["end"] = "finish"
                    break
                if summary["cost"] > max_cost:
                    summary["end"] = "max_cost"
                    break
        except Exception as error:  # noqa: BLE001 - the log must keep the reason of each failed run
            summary["end"] = "error"
            summary["error"] = f"{type(error).__name__}: {str(error)[:500]}"
        finally:
            try:
                web.page.wait_for_timeout(2500)  # the logger sends its last batch
                web.page.goto("about:blank")  # the page end sends the last events
                web.page.wait_for_timeout(500)
            except Exception:  # noqa: BLE001
                pass
            web.close()
            summary["seconds"] = round(time.time() - started, 1)
            summary["cost"] = round(summary["cost"], 6)
            write(summary)
    return summary
