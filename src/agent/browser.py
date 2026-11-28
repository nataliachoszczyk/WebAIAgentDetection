"""The browser of the agent: what the model sees and what its tools do. See docs/agent.md."""

import base64
import inspect
import math
import os
import random
import re
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

SNAPSHOT_LIMIT = 40000  # characters; a shop page has about 15000
TOOL_TIMEOUT = 5000  # ms

# Browsers: `plain` is the default Playwright Chromium. `hidden` hides the webdriver flag and the
# headless mark, as the usual browser of a user does.
BROWSERS = ("plain", "hidden")
# Motions: `direct` uses the Playwright actions as an agent framework does (one jump of the mouse,
# fill without key presses). `human` moves the mouse in steps and types key by key with typos.
MOTIONS = ("direct", "human")

# Key names as models write them, and the names of Playwright.
KEYS = {"enter": "Enter", "return": "Enter", "tab": "Tab", "escape": "Escape", "esc": "Escape",
        "backspace": "Backspace", "space": "Space", "delete": "Delete", "arrowdown": "ArrowDown",
        "arrowup": "ArrowUp", "arrowleft": "ArrowLeft", "arrowright": "ArrowRight", "pagedown": "PageDown",
        "pageup": "PageUp", "home": "Home", "end": "End", "down": "ArrowDown", "up": "ArrowUp"}

# Neighbor keys for typos of the `human` motion.
ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]


class Browser:
    def __init__(self, browser="plain", motion="direct", seed=None):
        assert browser in BROWSERS and motion in MOTIONS
        self.kind, self.motion = browser, motion
        self.rng = random.Random(seed)
        self.pw = sync_playwright().start()
        if browser == "plain":
            self.browser = self.pw.chromium.launch()
            self.context = self.browser.new_context(viewport={"width": 1280, "height": 800})
        else:
            args = ["--disable-blink-features=AutomationControlled", "--window-size=1366,900"]
            headed = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
            self.browser = self.pw.chromium.launch(channel="chromium", headless=not headed, args=args)
            if headed:
                self.context = self.browser.new_context(no_viewport=True)
            else:
                # Without a display (for example on Kaggle), only the headless mark in the user agent can go.
                probe = self.browser.new_page()
                agent = probe.evaluate("navigator.userAgent").replace("HeadlessChrome", "Chrome")
                probe.close()
                self.context = self.browser.new_context(viewport={"width": 1366, "height": 768}, user_agent=agent)
        self.page = self.context.new_page()
        self.context.on("page", self._new_tab)
        self.mouse = (self.rng.randint(200, 900), self.rng.randint(150, 600))
        self.tree = ""

    def _new_tab(self, page):
        self.page = page

    def close(self):
        try:
            self.browser.close()
        finally:
            self.pw.stop()

    def open(self, url):
        self.page.goto(url)
        self.settle()

    def settle(self):
        """Wait until the page is ready after an action, as an agent framework does."""
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            self.page.wait_for_load_state("networkidle", timeout=3000)
        except PlaywrightError:
            pass
        self.page.wait_for_timeout(300)

    def observe(self):
        """Return the text of the observation and the screenshot (JPEG, base64)."""
        for _ in range(3):
            try:
                tree = self.page.aria_snapshot(mode="ai")
                break
            except PlaywrightError:
                self.page.wait_for_timeout(500)
        else:
            tree = "(the page has no accessibility tree yet)"
        self.tree = tree
        if len(tree) > SNAPSHOT_LIMIT:
            tree = tree[:SNAPSHOT_LIMIT] + "\n... (the rest of the tree is cut)"
        sx, sy = self.page.evaluate("[scrollX, scrollY]")
        tabs = self.context.pages
        lines = [f"URL: {self.page.url}", f"Title: {self.page.title()}", f"Scroll position: {sx}, {sy}"]
        if len(tabs) > 1:
            lines.append(f"Open tabs: {len(tabs)}. You see the last tab.")
        text = "\n".join(lines) + "\n\nAccessibility tree:\n" + tree
        shot = self.page.screenshot(type="jpeg", quality=70)
        return text, base64.b64encode(shot).decode()

    def where(self):
        """A short state of the browser for the history: the page after the last action."""
        try:
            title = self.page.title()
        except PlaywrightError:
            title = ""
        return f"Page after this step: {self.page.url} ({title})"

    def cart_count(self):
        try:
            return self.page.evaluate("document.querySelector('.cart-link')?.innerText || ''")
        except PlaywrightError:
            return ""

    def act(self, name, args):
        """Do one tool call. Return a short text result for the model."""
        method = getattr(self, "tool_" + name)
        # Small models add arguments that a tool does not have. An agent framework ignores them.
        known = inspect.signature(method).parameters
        args = {k: v for k, v in args.items() if k in known}
        try:
            result = method(**args)
        except (PlaywrightError, TypeError, ValueError) as error:
            first = str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__
            if "Invalid frame in aria-ref" in first:
                return f"Error: the reference {args.get('ref')} is from an earlier page. Use the references of the last page."
            if "options is not iterable" in first:
                return f"Error: {args.get('ref')} is not a drop-down list."
            return f"Error: {first[:300]}"
        self.settle()
        return result or "Done."

    def describe(self, ref):
        """The line of the element in the last tree, without references. It stays the same after a reload."""
        ref = self.full_ref(ref)
        for line in self.tree.splitlines():
            if f"[ref={ref}]" in line:
                return re.sub(r"\s*\[ref=\w+\]", "", line).strip(" -:")
        return ref

    def element(self, ref):
        return self.page.locator(f"aria-ref={self.full_ref(ref)}")

    def full_ref(self, ref):
        """Models sometimes change the frame part of a reference (e17 or e1e17 for f1e17).
        The element number at the end and the last tree give the full reference, as an agent framework does."""
        ref = str(ref).strip().strip("[]").removeprefix("ref=")
        if f"[ref={ref}]" in self.tree:
            return ref
        number = re.search(r"(e\d+)$", ref)
        if number:
            full = sorted(set(re.findall(rf"\[ref=((?:f\d+)?{number.group(1)})\]", self.tree)))
            if len(full) == 1:
                return full[0]
        return ref

    # Tools. The names and the arguments are the same as in TOOLS of src/agent/agent.py.

    def tool_click(self, ref):
        target = self.element(ref)
        if self.motion == "direct":
            target.click(timeout=TOOL_TIMEOUT)
        else:
            self.human_click(target)
        return f"Clicked {ref}."

    def tool_type_text(self, ref, text, press_enter=False):
        target = self.element(ref)
        if self.motion == "direct":
            target.fill(text, timeout=TOOL_TIMEOUT)
            if press_enter:
                target.press("Enter")
        else:
            self.human_click(target)
            if target.input_value(timeout=TOOL_TIMEOUT):
                self.page.keyboard.press("Control+A")
                self.pause(0.1, 0.3)
                self.page.keyboard.press("Backspace")
            self.human_type(text)
            if press_enter:
                self.pause(0.2, 0.6)
                self.page.keyboard.press("Enter")
        return f"Typed {len(text)} characters into {ref}."

    def tool_select_option(self, ref, option):
        target = self.element(ref)
        if self.motion == "human":
            # A person opens the list and selects with the keyboard. The events are then trusted.
            self.human_click(target)
            self.page.keyboard.type(option[:3], delay=self.rng.randint(90, 180))
            self.page.keyboard.press("Enter")
            labels = target.evaluate("e => [e.value, e.options[e.selectedIndex]?.label]")
            if option in labels:
                return f"Selected {option!r} in {ref}."
        selected = target.select_option(label=option, timeout=TOOL_TIMEOUT) if self.has_label(target, option) \
            else target.select_option(option, timeout=TOOL_TIMEOUT)
        return f"Selected {selected} in {ref}."

    def has_label(self, target, option):
        return target.evaluate("(e, o) => [...e.options].some(x => x.label === o)", option)

    def tool_scroll(self, direction="down", ref=None):
        sign = -1 if direction == "up" else 1
        if ref:
            box = self.element(ref).bounding_box(timeout=TOOL_TIMEOUT)
            if not box:
                return f"Error: {ref} is not visible."
            self.move_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        height = self.page.evaluate("innerHeight")
        if self.motion == "direct":
            self.page.mouse.wheel(0, sign * int(height * 0.8))
        else:
            for _ in range(self.rng.randint(5, 9)):
                self.page.mouse.wheel(0, sign * 100)
                self.pause(0.03, 0.12)
        self.page.wait_for_timeout(400)
        return f"Scrolled {direction}" + (f" in {ref}." if ref else ".")

    def tool_press_key(self, key):
        key = KEYS.get(str(key).strip().lower(), key)
        self.page.keyboard.press(key)
        return f"Pressed {key}."

    def tool_go_back(self):
        self.page.go_back()
        return "Went back."

    def tool_open_url(self, url):
        origin = "/".join(self.page.url.split("/", 3)[:3])
        if url.startswith("/"):
            url = origin + url
        # The study runs only on our own shop.
        if not url.startswith(origin + "/") and url != origin:
            return f"Error: this browser opens only pages of {origin}."
        self.page.goto(url)
        return f"Opened {url}."

    def tool_wait(self, seconds=2):
        self.page.wait_for_timeout(min(float(seconds), 10) * 1000)
        return f"Waited {seconds} s."

    # The `human` motion.

    def pause(self, low, high):
        time.sleep(self.rng.uniform(low, high))

    def move_to(self, x, y):
        """Move the mouse to (x, y) on a curve with a varied speed, as a hand does."""
        if self.motion == "direct":
            self.page.mouse.move(x, y)
            self.mouse = (x, y)
            return
        x0, y0 = self.mouse
        distance = math.hypot(x - x0, y - y0)
        steps = max(8, min(45, int(distance / 18)))
        bend = self.rng.uniform(-0.25, 0.25) * distance
        cx = (x0 + x) / 2 - bend * (y - y0) / (distance or 1)
        cy = (y0 + y) / 2 + bend * (x - x0) / (distance or 1)
        for i in range(1, steps + 1):
            s = i / steps
            s = s * s * (3 - 2 * s)  # slow at the start and at the end
            px = (1 - s) ** 2 * x0 + 2 * (1 - s) * s * cx + s * s * x + self.rng.gauss(0, 0.7)
            py = (1 - s) ** 2 * y0 + 2 * (1 - s) * s * cy + s * s * y + self.rng.gauss(0, 0.7)
            self.page.mouse.move(px, py)
            time.sleep(self.rng.uniform(0.008, 0.02))
        self.page.mouse.move(x, y)
        self.mouse = (x, y)

    def human_scroll_to(self, target):
        """Scroll with the wheel until the element is in the window."""
        for _ in range(30):
            box = target.bounding_box(timeout=TOOL_TIMEOUT)
            height = self.page.evaluate("innerHeight")
            if box is None or 0 <= box["y"] and box["y"] + box["height"] <= height:
                return box
            sign = 1 if box["y"] > 0 else -1
            self.page.mouse.wheel(0, sign * 100 * self.rng.randint(2, 4))
            self.pause(0.05, 0.2)
        return target.bounding_box(timeout=TOOL_TIMEOUT)

    def human_click(self, target):
        target.wait_for(state="visible", timeout=TOOL_TIMEOUT)
        box = self.human_scroll_to(target)
        if not box:
            raise ValueError("the element is not visible")
        x = box["x"] + box["width"] * self.rng.uniform(0.3, 0.7)
        y = box["y"] + box["height"] * self.rng.uniform(0.3, 0.7)
        self.move_to(x, y)
        self.pause(0.08, 0.25)
        self.page.mouse.down()
        self.pause(0.05, 0.13)
        self.page.mouse.up()

    def human_type(self, text):
        for char in text:
            low = char.lower()
            row = next((r for r in ROWS if low in r), None)
            if row and self.rng.random() < 0.04:
                i = row.index(low)
                wrong = row[min(len(row) - 1, i + 1)] if i == 0 or self.rng.random() < 0.5 else row[i - 1]
                self.page.keyboard.type(wrong)
                self.pause(0.15, 0.4)
                self.page.keyboard.press("Backspace")
                self.pause(0.08, 0.2)
            self.page.keyboard.type(char)
            self.pause(0.06, 0.22 if char != " " else 0.35)
