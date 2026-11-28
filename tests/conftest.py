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
