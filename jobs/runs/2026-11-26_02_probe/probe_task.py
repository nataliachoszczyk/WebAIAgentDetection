import base64
import json
import os
import platform
import subprocess
import sys
import time

import kaggle_benchmarks as kbench

HTML = "<html><body><h1>Login</h1><button id='b' style='background:green;color:white' onclick=\"this.textContent='clicked'\">SUBMIT</button></body></html>"


@kbench.task(name="wad-probe", description="Check Playwright, Chromium and the model proxy in one Kaggle session.")
def wad_probe(llm) -> None:
    info = {"python": platform.python_version(), "proxy_env": sorted(k for k in os.environ if "PROXY" in k or k.startswith("LLM"))}
    t = time.time()
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright", "openai"], capture_output=True, text=True)
    info["pip_ok"] = r.returncode == 0
    r = subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], capture_output=True, text=True)
    info["chromium_install_ok"] = r.returncode == 0
    info["chromium_install_err"] = r.stderr[-300:]
    info["install_s"] = round(time.time() - t, 1)

    from concurrent.futures import ThreadPoolExecutor
    from playwright.sync_api import sync_playwright

    # The task runs in a Jupyter kernel with an asyncio loop; the sync API needs its own thread.
    def browse():
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 400, "height": 200})
            page.set_content(HTML)
            shot = page.screenshot()
            flag = page.evaluate("navigator.webdriver")
            browser.close()
            return shot, flag

    with ThreadPoolExecutor(1) as ex:
        png, info["webdriver_flag"] = ex.submit(browse).result()

    info["kbench_text"] = llm.prompt("Answer with one word: what colour is grass?")[:50]

    from openai import OpenAI
    from kaggle_benchmarks import utils as kb_utils
    url = os.environ["MODEL_PROXY_URL"].rstrip("/")
    url = url if url.endswith("/openapi") else url + "/openapi"
    client = OpenAI(base_url=url, api_key=os.environ["MODEL_PROXY_API_KEY"], http_client=kb_utils.build_httpx_client("model_proxy"))
    tool = [{"type": "function", "function": {"name": "click", "description": "Click an element", "parameters": {"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]}}}]
    msgs = [{"role": "user", "content": [
        {"type": "text", "text": "You control a browser. Click the button on this screenshot with the click tool."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}},
    ]}]
    resp = client.chat.completions.create(model="google/gemini-3.1-flash-lite-preview", messages=msgs, tools=tool, max_tokens=200)
    calls = resp.choices[0].message.tool_calls or []
    info["vision_tool_call"] = [(c.function.name, c.function.arguments) for c in calls]

    print("WAD_PROBE", json.dumps(info))
    with open("/kaggle/working/probe.json", "w") as f:
        json.dump(info, f, indent=2)
    kbench.assertions.assert_true(bool(calls), expectation="the model calls the click tool from a screenshot")


wad_probe.run(kbench.llm)
