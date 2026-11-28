"""The HTTP server of the test shop: static files, session links and a small JSON API."""

import json
import mimetypes
import secrets
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .logger.schema import MAX_BATCH, InvalidEvent, clean_client_event
from .store import Store
from .traps import canary_paths

PACKAGE_DIR = Path(__file__).resolve().parent

SITE_DIR = PACKAGE_DIR / "site"
# The scripts of the study have neutral public names, like the scripts of a real shop.
# A name such as "traps.js" in the page source would warn an agent that reads the DOM.
SCRIPTS = {
    "/assets/js/analytics.js": PACKAGE_DIR / "logger" / "logger.js",
    "/assets/js/widgets.js": PACKAGE_DIR / "traps" / "traps.js",
    "/assets/js/order-check.js": PACKAGE_DIR / "captcha" / "captcha.js",
}
PUBLIC_SUFFIXES = {".html", ".css", ".js", ".json", ".svg", ".png", ".ico"}
CANARY_PATHS = canary_paths()

TASKS_FILE = PACKAGE_DIR / "tasks.json"
# Neutral names, like the cookies of a real shop.
SESSION_COOKIE = "ps_sid"
STUDY_COOKIE = "ps_visit"
MAX_BODY = 256 * 1024


def resolve_static(url_path):
    """Return the file for a URL path, or None. A site file must be inside the site folder."""
    if url_path in SCRIPTS:
        return SCRIPTS[url_path]
    candidate = (SITE_DIR / (url_path.lstrip("/") or "index.html")).resolve()
    if candidate.is_relative_to(SITE_DIR) and candidate.is_file() and candidate.suffix in PUBLIC_SUFFIXES:
        return candidate
    return None


class ShopHandler(BaseHTTPRequestHandler):
    # The default header names a Python test server. A real shop shows a usual web server.
    server_version = "nginx"
    sys_version = ""
    store: Store

    # Routes --------------------------------------------------------------

    def do_GET(self):
        url = urlsplit(self.path)
        # A link only shows the start button. Link preview bots of chat apps open each link, but they do not press it.
        if url.path.startswith("/s/"):
            return self.session_link(url.path[3:], parse_qs(url.query))
        if url.path.startswith("/join/"):
            return self.join_link(url.path[6:], parse_qs(url.query))
        if url.path == "/api/tasks":
            tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            # The expected answers are for the analysis only, not for the page.
            tasks.pop("expected", None)
            tasks["done"] = self.store.state(self.session(), "closed") is not None
            return self.send_json(tasks)
        if url.path == "/api/health":
            return self.send_json({"ok": True})
        if url.path in CANARY_PATHS:
            self.record([{"type": "canary", "trap": CANARY_PATHS[url.path]}])
            return self.send_not_found()
        return self.send_static(url.path)

    def do_HEAD(self):
        # A usual web server answers HEAD with the headers of GET. A 501 answer is a sign of a test server.
        self.do_GET()

    def do_POST(self):
        url = urlsplit(self.path)
        if url.path.startswith("/s/"):
            return self.start_session(url.path[3:], parse_qs(url.query))
        if url.path.startswith("/join/"):
            return self.join(url.path[6:], parse_qs(url.query))
        handlers = {
            "/api/events": self.receive_events,
            "/api/order": self.place_order,
            "/api/contact": self.send_contact,
        }
        handler = handlers.get(url.path)
        if handler is None:
            return self.send_error(HTTPStatus.NOT_FOUND)
        body = self.read_json()
        if body is None:
            return self.send_error(HTTPStatus.BAD_REQUEST)
        return handler(body)

    # Sessions ------------------------------------------------------------

    def session(self):
        """Return the session code of the request if the session takes events, else None."""
        code = self.cookie_session()
        return code if self.store.accepts_events(code) else None

    def cookie_session(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        return cookie[SESSION_COOKIE].value if SESSION_COOKIE in cookie else None

    def session_link(self, code, query):
        if not self.store.is_valid(code):
            return self.send_not_found()
        # The same browser continues without the button. A closed session shows its end page.
        if self.cookie_session() == code or self.store.state(code, "closed") is not None:
            return self.start_session(code, query)
        return self.send_file(SITE_DIR / "welcome.html")

    def join_link(self, secret, query):
        if secret not in self.store.joins():
            return self.send_not_found()
        own = self.cookie_session()
        if own and self.store.sessions().get(own, {}).get("join") == secret:
            return self.start_session(own, query)
        if self.store.join_problem(secret):
            return self.send_file(SITE_DIR / "closed.html", HTTPStatus.GONE)
        return self.send_file(SITE_DIR / "welcome.html")

    def start_session(self, code, query):
        if not self.store.is_valid(code):
            return self.send_not_found()
        if self.store.state(code, "closed") is not None:
            # The person who did the tasks sees the end page. A second person cannot use the link.
            if self.cookie_session() == code:
                return self.send_file(SITE_DIR / "done.html")
            return self.send_file(SITE_DIR / "closed.html", HTTPStatus.GONE)
        again = self.store.state(code, "started") is not None
        self.store.mark(code, "started")
        self.store.append(code, [{"type": "session_start", "ua": self.headers.get("User-Agent", ""),
                                  "again": again}], source="server")
        # A person who opens the link again continues with the same cart.
        target = query.get("next", ["/" if again else "/start.html"])[0]
        if not target.startswith("/") or target.startswith("//"):
            target = "/start.html"
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", target)
        # The session cookie is HttpOnly, so a script on the page cannot read the code.
        self.send_header("Set-Cookie", f"{SESSION_COOKIE}={code}; Path=/; HttpOnly; SameSite=Lax")
        self.send_header("Set-Cookie", f"{STUDY_COOKIE}=1; Path=/; SameSite=Lax")
        self.end_headers()

    def join(self, secret, query):
        """A join link for a group: each new browser gets its own session."""
        if secret not in self.store.joins():
            return self.send_not_found()
        own = self.cookie_session()
        # The same browser keeps its session. It does not take a second place of the limit.
        if own and self.store.sessions().get(own, {}).get("join") == secret:
            return self.start_session(own, query)
        code, _ = self.store.join_session(secret)
        if code is None:
            return self.send_file(SITE_DIR / "closed.html", HTTPStatus.GONE)
        return self.start_session(code, query)

    def record(self, events):
        session = self.session()
        if session:
            self.store.append(session, events, source="server")

    def receive_events(self, body):
        session = self.session()
        if session is None:
            return self.send_json({"error": "no session"}, HTTPStatus.FORBIDDEN)
        raw = body.get("events")
        if not isinstance(raw, list) or len(raw) > MAX_BATCH:
            return self.send_json({"error": "bad batch"}, HTTPStatus.BAD_REQUEST)
        events = []
        for item in raw:
            try:
                events.append(clean_client_event(item))
            except InvalidEvent:
                continue
        self.store.append(session, events)
        return self.send_json({"accepted": len(events), "rejected": len(raw) - len(events)})

    # Shop API ------------------------------------------------------------

    def place_order(self, body):
        items = body.get("items")
        if not isinstance(items, list) or not items:
            return self.send_json({"error": "The cart is empty."}, HTTPStatus.BAD_REQUEST)
        order = "PS-" + "".join(secrets.choice("0123456789") for _ in range(6))
        self.record([{"type": "order", "order": order, "items": items,
                      "total": body.get("total"), "fields": body.get("fields", {})}])
        if self.session():
            self.store.mark(self.session(), "ordered")
        return self.send_json({"order": order})

    def send_contact(self, body):
        self.record([{"type": "contact", "fields": body.get("fields", {})}])
        session = self.session()
        # The contact message is the last task, also when the person did not order.
        if session:
            self.store.mark(session, "closed")
        return self.send_json({"ok": True})

    # Helpers -------------------------------------------------------------

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if length <= 0 or length > MAX_BODY:
            return None
        try:
            body = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            return None
        return body if isinstance(body, dict) else None

    def send_json(self, data, status=HTTPStatus.OK):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def send_not_found(self):
        """Send the 404 page of the shop. A canary page gets the same answer as a page that does not exist."""
        self.send_file(SITE_DIR / "404.html", HTTPStatus.NOT_FOUND)

    def send_static(self, url_path):
        path = resolve_static(url_path)
        if path is not None:
            return self.send_file(path)
        if Path(url_path).suffix in ("", ".html"):
            return self.send_not_found()
        return self.send_error(HTTPStatus.NOT_FOUND)

    def send_file(self, path, status=HTTPStatus.OK):
        payload = path.read_bytes()
        if path in SCRIPTS.values():
            # The comments of the study scripts explain the study. A real shop sends no such comments.
            lines = payload.decode("utf-8").splitlines(keepends=True)
            payload = "".join(line for line in lines if not line.lstrip().startswith("//")).encode("utf-8")
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if kind.startswith("text/") or kind in ("application/javascript", "image/svg+xml"):
            kind += "; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def log_message(self, format, *args):
        # The default access log prints the IP address of each visitor. We do not keep it.
        pass


def make_server(data_dir, host="127.0.0.1", port=8000):
    handler = type("BoundShopHandler", (ShopHandler,), {"store": Store(data_dir)})
    return ThreadingHTTPServer((host, port), handler)
