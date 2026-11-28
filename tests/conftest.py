import threading

import pytest

from src.shop.server import make_server


@pytest.fixture
def shop(tmp_path):
    """Start a shop server on a free port. Give the base URL, the store and the data folder."""
    server = make_server(tmp_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield {"url": f"http://{host}:{port}", "store": server.RequestHandlerClass.store, "data": tmp_path}
    server.shutdown()
    server.server_close()


def open_link(page, url):
    """Open a session link or a join link like a person: the link shows a start button first."""
    page.goto(url)
    if page.locator("#begin").count():
        with page.expect_navigation():
            page.click("#begin")
    page.wait_for_load_state("networkidle")
