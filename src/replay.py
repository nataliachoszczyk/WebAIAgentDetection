"""Replay each session of the test shop as a video. The script uses only the event log.

Run: python -m src.replay <data folder> [--session CODE] [--out FOLDER]

The script opens the shop pages in headless Chromium with the window size of the person. It repeats the page
changes, the scroll, the clicks, the typed text and the mouse at the times of the log. The randomness of the
pages is fixed, so the same log gives the same video.
"""

import argparse
import json
from collections import Counter
import subprocess
import tempfile
import threading
from io import BytesIO
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from .shop.server import make_server

BAR = 40
CURSOR_SCALE = 1.7
CLICK_MS = 500
CAPTCHA_URL = "/assets/js/order-check.js"

# The same helpers in each page: fixed randomness, and the actions of the log on the element of the log.
INIT_SCRIPT = """
(() => {
  let s = 1;
  const next = () => (s = (s * 1103515245 + 12345) % 2147483648);
  Math.random = () => next() / 2147483648;
  crypto.getRandomValues = (a) => { for (let i = 0; i < a.length; i++) a[i] = next(); return a; };

  // The same description of an element as the logger gives.
  const describe = (el) => {
    if (!(el instanceof Element)) return "document";
    const tag = el.tagName.toLowerCase();
    if (el.id) return `${tag}#${el.id}`;
    const name = el.getAttribute("name");
    if (name) return `${tag}[name=${name}]`;
    const cls = el.classList[0];
    return cls ? `${tag}.${cls}` : tag;
  };
  const all = (desc) => { try { return [...document.querySelectorAll(desc)]; } catch { return []; } };
  // The element under the point with the logged description. Else the nearest element with this description.
  const find = (desc, x, y) => {
    if (!desc || desc === "document" || desc.startsWith("trap:")) return x == null ? null : document.elementFromPoint(x, y);
    if (x != null) {
      for (let n = document.elementFromPoint(x, y); n; n = n.parentElement) if (describe(n) === desc) return n;
    }
    let best = null, distance = Infinity;
    for (const el of all(desc)) {
      const r = el.getBoundingClientRect();
      const d = x == null ? 0 : Math.hypot(r.x + r.width / 2 - x, r.y + r.height / 2 - y);
      if (d < distance) { best = el; distance = d; }
      if (x == null) break;
    }
    return best;
  };
  const fire = (el, type) => el.dispatchEvent(new Event(type, { bubbles: true }));

  // A CSS transition depends on the time of the screenshot. Without transitions, each run gives the same pixels.
  addEventListener("DOMContentLoaded", () => {
    const style = document.createElement("style");
    style.textContent = "*, *::before, *::after { transition: none !important; animation: none !important; caret-color: transparent !important; }";
    document.head.append(style);
  });

  window.__settle = async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map((img) => img.complete ? null : new Promise((r) => { img.onload = img.onerror = r; })));
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  };

  window.__replay = ({ type, target, x, y, value, sx, sy }) => {
    if (type === "scroll") return window.scrollTo({ left: sx, top: sy, behavior: "instant" });
    if (type === "click") {
      const el = find(target, x, y);
      // Links and submit buttons do nothing here: the page_view and submit events of the log do their work.
      if (!el || el.closest("a[href]") || el.closest("button[type=submit], input[type=submit]")) return;
      return el.click();
    }
    if (type === "submit") {
      const form = find(target);
      if (form) form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      return;
    }
    if (type === "input") {
      const el = find(target);
      if (el) { el.value = value; fire(el, "input"); }
      return;
    }
    if (type === "change") {
      const el = find(target);
      if (!el) return;
      if (el.type === "radio") {
        const radio = all(`input[type=radio][name="${el.name}"]`).find((r) => r.value === value);
        if (radio && !radio.checked) { radio.checked = true; fire(radio, "change"); }
      } else if (el.type === "checkbox") {
        if (el.checked !== (value !== "")) { el.checked = value !== ""; fire(el, "change"); }
      } else if (el.value !== value) {
        el.value = value;
        fire(el, "change");
      }
      return;
    }
    if (type === "focus") find(target)?.focus?.({ preventScroll: true });
    if (type === "blur") document.activeElement?.blur?.();
  };
})();
"""

PAGE_ACTIONS = {"scroll", "click", "submit", "input", "change", "focus", "blur"}
# The state of a page that the replay can set again. Clicks and submits stay out: they can add to the cart again.
STATE_ACTIONS = {"scroll", "input", "change"}
POINTER = {"pointer_move", "pointer_down", "pointer_up", "click"}


def closing(event):
    return event["type"] == "page_hide" or (event["type"] == "visibility" and event["state"] == "hidden")


def load_session(path):
    events = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    events.sort(key=lambda e: (e["ts"], e.get("seq", 0)))
    return events


def factor_pair(product):
    """Two factors of the product in the range of the reverse CAPTCHA (12-49). The log keeps only the answer."""
    for a in range(12, 50):
        if product % a == 0 and 12 <= product // a <= 49:
            return a, product // a
    return None


def patch_captcha(source, events):
    """Show the codes of the session in the reverse CAPTCHA. The log has the answers, not the random codes."""
    order = next((e for e in events if e["type"] == "order"), None)
    fields = order["fields"] if order else {}
    ok = {e["captcha"]: e["ok"] for e in events if e["type"] == "captcha"}
    lines = []
    if ok.get("retype-code") and fields.get("check_reference"):
        lines.append(f"reference = {json.dumps(fields['check_reference'].strip().upper())};")
    if ok.get("terms-code") and fields.get("check_terms"):
        lines.append(f"termsCode = {json.dumps(fields['check_terms'].strip())};")
    pair = factor_pair(int(fields["check_product"])) if ok.get("multiply") and str(fields.get("check_product", "")).isdigit() else None
    if pair:
        lines.append(f"a = {pair[0]}; b = {pair[1]};")
    marks = ["const reference =", "const termsCode =", "const a =", "const b =", "  const TERMS = ["]
    if not lines or not all(m in source for m in marks):
        return source
    for name in ("reference", "termsCode", "a", "b"):
        source = source.replace(f"const {name} =", f"let {name} =", 1)
    return source.replace("  const TERMS = [", "  " + " ".join(lines) + "\n  const TERMS = [", 1)


def window_sizes(events):
    """The window size of each page, from the fingerprint of the page."""
    sizes = {}
    for e in events:
        if e["type"] == "env":
            w, h = (int(n) for n in e["env"]["window"].split("x"))
            sizes[e["page"]] = (w, h)
    return sizes


def cursor_image(scale):
    """A large arrow with a white fill and a black edge, on a yellow halo, so it is easy to see."""
    arrow = [(0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12)]
    size = int(48 * scale)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    r = int(14 * scale)
    draw.ellipse([0, 0, 2 * r, 2 * r], fill=(255, 210, 0, 90))
    points = [(r + x * scale, r + y * scale) for x, y in arrow]
    draw.polygon(points, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=max(2, int(scale * 1.5)))
    return image, (r, r)


class Replay:
    def __init__(self, events, base_url, browser, fps, speed):
        self.events = events
        self.base = base_url
        self.fps = fps
        self.speed = speed
        self.sizes = window_sizes(events)
        # The video has the window size of most pages. A link preview bot can open the first page with another size.
        sizes = Counter(self.sizes.values())
        first_size = max(sizes, key=lambda size: (sizes[size], size)) if sizes else (1280, 800)
        self.width = first_size[0] + first_size[0] % 2
        self.height = first_size[1] + BAR + (first_size[1] + BAR) % 2
        self.order = next((e for e in events if e["type"] == "order"), None)
        self.captcha_source = None
        self.allow_navigation = False
        self.context = browser.new_context(viewport={"width": first_size[0], "height": first_size[1]},
                                           device_scale_factor=1, timezone_id="Europe/Warsaw", locale="en-US")
        self.context.add_init_script(INIT_SCRIPT)
        self.context.route("**/*", self.route)
        self.page = self.context.new_page()
        self.cursor, self.hotspot = cursor_image(CURSOR_SCALE)
        self.font = ImageFont.load_default(size=22)

    def route(self, route):
        request = route.request
        path = request.url[len(self.base):].split("?")[0]
        # Only the replay opens pages. A page that opens a page itself would change the order of the log.
        if request.is_navigation_request() and not self.allow_navigation:
            return route.abort("aborted")
        if path == "/api/events":
            return route.fulfill(json={"accepted": 0, "rejected": 0})
        if path == "/api/order":
            return route.fulfill(json={"order": self.order["order"] if self.order else "PS-000000"})
        if path == "/api/contact":
            return route.fulfill(json={"ok": True})
        if path == CAPTCHA_URL:
            if self.captcha_source is None:
                self.captcha_source = patch_captcha(route.fetch().text(), self.events)
            return route.fulfill(body=self.captcha_source, content_type="text/javascript")
        return route.continue_()

    def open(self, path, page_id):
        if path.startswith("/order.html") and self.order:
            total = self.order.get("total")
            email = self.order["fields"].get("email", "")
            self.page.evaluate("(v) => sessionStorage.setItem('ps_last_order', v)",
                               json.dumps({"order": self.order["order"], "email": email, "total": total}))
        if page_id in self.sizes:
            w, h = self.sizes[page_id]
            self.page.set_viewport_size({"width": w, "height": h})
        self.allow_navigation = True
        try:
            self.page.goto(self.base + path, wait_until="networkidle")
            self.page.evaluate("window.__settle()")
        finally:
            self.allow_navigation = False

    def run(self, code, out_path):
        self.allow_navigation = True
        self.page.goto(f"{self.base}/s/{code}", wait_until="networkidle")
        self.allow_navigation = False
        client = [e for e in self.events if e.get("src") == "client"]
        start, end = client[0]["ts"], client[-1]["ts"] + 1000
        ffmpeg = subprocess.Popen(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{self.width}x{self.height}", "-r", str(self.fps), "-i", "-",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-threads", "1", str(out_path)],
            stdin=subprocess.PIPE)
        current, path, hidden = None, "", False
        paths, history = {}, {}
        cursor, clicks = None, []
        shot, dirty, moved = None, True, False
        i, frame = 0, 0
        step = 1000 / self.fps * self.speed
        while start + frame * step <= end:
            now = start + frame * step
            while i < len(client) and client[i]["ts"] <= now:
                e = client[i]
                i += 1
                if e["type"] == "page_view":
                    # The browser sends "hidden" when a page closes. A new page is visible.
                    current, path, hidden = e["page"], e["path"], False
                    paths[current], history[current] = path, []
                    self.open(path, current)
                    dirty = True
                elif e["page"] != current and e["page"] in paths and not closing(e):
                    # The back button shows an earlier page from the cache of the browser, without a new page_view.
                    current, path, hidden = e["page"], paths[e["page"]], False
                    self.open(path, current)
                    for old in history[current]:
                        self.page.evaluate("(e) => window.__replay(e)", old)
                    dirty = True
                if e["page"] != current:
                    continue
                if e["type"] in STATE_ACTIONS:
                    history[current].append(e)
                if e["type"] in POINTER and "x" in e:
                    cursor = (e["x"], e["y"])
                    moved = True
                if e["type"] == "pointer_down":
                    clicks.append((e["ts"], e["x"], e["y"]))
                if e["type"] == "visibility":
                    hidden = e["state"] == "hidden"
                if e["type"] == "resize":
                    self.page.set_viewport_size({"width": e["w"], "height": e["h"]})
                    dirty = True
                if e["type"] in PAGE_ACTIONS:
                    self.page.evaluate("(e) => window.__replay(e)", e)
                    dirty = True
            if moved and cursor:
                # The real mouse of the replay shows the hover state of the page.
                self.page.mouse.move(*cursor)
                dirty = True
            if dirty:
                self.page.evaluate("window.__settle()")
                shot = Image.open(BytesIO(self.page.screenshot(animations="disabled"))).convert("RGB")
                dirty = moved = False
            clicks = [c for c in clicks if now - c[0] < CLICK_MS]
            ffmpeg.stdin.write(self.draw(shot, cursor, clicks, now, now - start, path, hidden).tobytes())
            frame += 1
        ffmpeg.stdin.close()
        ffmpeg.wait()
        self.context.close()
        return frame

    def draw(self, shot, cursor, clicks, now, elapsed, path, hidden):
        # The marks go on the page first, so a page with another window size keeps them in place after the scale.
        page = shot.copy()
        draw = ImageDraw.Draw(page, "RGBA")
        if hidden:
            draw.rectangle([0, 0, page.width, page.height], fill=(0, 0, 0, 150))
        for ts, x, y in clicks:
            progress = (now - ts) / CLICK_MS
            r = 10 + 30 * progress
            draw.ellipse([x - r, y - r, x + r, y + r], outline=(230, 0, 0, int(255 * (1 - progress))), width=5)
        if cursor and not hidden:
            page.paste(self.cursor, (int(cursor[0] - self.hotspot[0]), int(cursor[1] - self.hotspot[1])), self.cursor)
        area = (self.width, self.height - BAR)
        if page.size != area:
            scale = min(area[0] / page.width, area[1] / page.height)
            page = page.resize((max(1, round(page.width * scale)), max(1, round(page.height * scale))), Image.LANCZOS)
        canvas = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        canvas.paste(page, ((area[0] - page.width) // 2, (area[1] - page.height) // 2))
        draw = ImageDraw.Draw(canvas)
        seconds = int(elapsed / 1000)
        text = f"{seconds // 60:02d}:{seconds % 60:02d}   {path}" + ("   [tab hidden]" if hidden else "")
        draw.rectangle([0, self.height - BAR, self.width, self.height], fill=(30, 30, 30))
        draw.text((12, self.height - BAR + 8), text, fill=(255, 255, 255), font=self.font)
        return canvas


def main():
    parser = argparse.ArgumentParser(prog="python -m src.replay", description=__doc__.splitlines()[0])
    parser.add_argument("data_dir", help="the folder with sessions.jsonl and events/")
    parser.add_argument("--session", action="append", help="the session code (default: all sessions)")
    parser.add_argument("--out", default="data/replay", help="the folder for the videos")
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--speed", type=float, default=1.0, help="2 makes the video two times shorter")
    args = parser.parse_args()

    files = sorted(Path(args.data_dir, "events").glob("*.jsonl"))
    if args.session:
        files = [f for f in files if f.stem in args.session]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # A new empty shop gives the pages. The replay records nothing in the real data.
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        server = make_server(tmp, port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = "http://%s:%d" % server.server_address
        store = server.RequestHandlerClass.store
        browser = p.chromium.launch()
        for path in files:
            events = load_session(path)
            target = out / f"{path.stem}.mp4"
            frames = Replay(events, base, browser, args.fps, args.speed).run(store.new_session("bot", note="replay"), target)
            print(f"{target}: {frames} frames, {frames / args.fps:.0f} s")
        browser.close()
        server.shutdown()


if __name__ == "__main__":
    main()
