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

PACKAGE_DIR = Path(__file__).resolve().parent

# URL prefix -> folder. Each part of the page keeps its own folder.
MOUNTS = {
    "/": PACKAGE_DIR / "site",
    "/logger/": PACKAGE_DIR / "logger",
}
# Only these files are public. Python files in the same folders stay private.
PUBLIC_SUFFIXES = {".html", ".css", ".js", ".json", ".svg", ".png", ".ico"}

TASKS_FILE = PACKAGE_DIR / "tasks.json"
SESSION_COOKIE = "wad_sid"
STUDY_COOKIE = "wad_study"
MAX_BODY = 256 * 1024


def resolve_static(url_path):
    """Return the file for a URL path, or None. The file must be inside its mount folder."""
    for prefix in sorted(MOUNTS, key=len, reverse=True):
        if url_path.startswith(prefix):
            root = MOUNTS[prefix]
            relative = url_path[len(prefix):] or "index.html"
            candidate = (root / relative).resolve()
            if candidate.is_relative_to(root) and candidate.is_file() and candidate.suffix in PUBLIC_SUFFIXES:
                return candidate
            return None
    return None


class ShopHandler(BaseHTTPRequestHandler):
    server_version = "nginx"
    sys_version = ""
    store: Store

    # Routes --------------------------------------------------------------

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path.startswith("/s/"):
            return self.start_session(url.path[3:], parse_qs(url.query))
        if url.path == "/api/tasks":
            tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            # The expected answers are for the analysis only, not for the page.
            tasks.pop("expected", None)
            return self.send_json(tasks)
        if url.path == "/api/health":
            return self.send_json({"ok": True})
        return self.send_static(url.path)

    def do_POST(self):
        url = urlsplit(self.path)
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
        """Return the session code of the request if it is valid, else None."""
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        code = cookie[SESSION_COOKIE].value if SESSION_COOKIE in cookie else None
        return code if self.store.is_valid(code) else None

    def start_session(self, code, query):
        if not self.store.is_valid(code):
            return self.send_error(HTTPStatus.NOT_FOUND)
        self.store.append(code, [{"type": "session_start", "ua": self.headers.get("User-Agent", "")}],
                          source="server")
        target = query.get("next", ["/study.html"])[0]
        if not target.startswith("/") or target.startswith("//"):
            target = "/study.html"
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", target)
        # The session cookie is HttpOnly, so a script on the page cannot read the code.
        self.send_header("Set-Cookie", f"{SESSION_COOKIE}={code}; Path=/; HttpOnly; SameSite=Lax")
        self.send_header("Set-Cookie", f"{STUDY_COOKIE}=1; Path=/; SameSite=Lax")
        self.end_headers()

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
        return self.send_json({"order": order})

    def send_contact(self, body):
        self.record([{"type": "contact", "fields": body.get("fields", {})}])
        return self.send_json({"ok": True})

    # Helpers -------------------------------------------------------------

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
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
        self.wfile.write(payload)

    def send_static(self, url_path):
        path = resolve_static(url_path)
        if path is None:
            return self.send_error(HTTPStatus.NOT_FOUND)
        payload = path.read_bytes()
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if kind.startswith("text/") or kind in ("application/javascript", "image/svg+xml"):
            kind += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        # The default access log prints the IP address of each visitor. We do not keep it.
        pass


def make_server(data_dir, host="127.0.0.1", port=8000):
    handler = type("BoundShopHandler", (ShopHandler,), {"store": Store(data_dir)})
    return ThreadingHTTPServer((host, port), handler)
