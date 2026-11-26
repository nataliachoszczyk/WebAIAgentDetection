"""Smoke test: check the repository clone, the internet, Playwright and headless Chromium."""
import json
import platform
import subprocess
import sys

REPO = "https://github.com/nataliachoszczyk/WebAIAgentDetection.git"
BRANCH = "main"
CLONE = "/tmp/repo"  # Not in /kaggle/working, so the clone is not an output.

subprocess.run(["git", "clone", "--depth", "1", "--branch", BRANCH, REPO, CLONE], check=True)
commit = subprocess.run(["git", "-C", CLONE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
print("commit", commit)

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright"], check=True)
subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True)

from playwright.sync_api import sync_playwright

# A local page, so that the test sends no browser to an external site.
html = "<html><body><button id='b' onclick=\"this.textContent='clicked'\">click</button></body></html>"
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html)
    page.click("#b")
    result = {
        "python": platform.python_version(),
        "commit": commit,
        "chromium": browser.version,
        "click_ok": page.text_content("#b") == "clicked",
        "webdriver_flag": page.evaluate("navigator.webdriver"),
        "user_agent": page.evaluate("navigator.userAgent"),
    }
    browser.close()

print(json.dumps(result, indent=2))
with open("/kaggle/working/smoke.json", "w") as f:
    json.dump(result, f, indent=2)
