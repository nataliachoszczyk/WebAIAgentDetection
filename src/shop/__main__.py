"""Command line of the test shop. Run `python -m src.shop --help` to see the commands."""

import argparse

from .server import make_server
from .store import Store

DEFAULT_DATA_DIR = "data/shop"


def main():
    parser = argparse.ArgumentParser(prog="python -m src.shop")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="run the shop server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--data-dir", default=DEFAULT_DATA_DIR)

    new = commands.add_parser("new-session", help="make session links")
    new.add_argument("--label", required=True, choices=["human", "agent", "bot"])
    new.add_argument("--model", help="the model id of the agent")
    new.add_argument("--note")
    new.add_argument("--count", type=int, default=1)
    new.add_argument("--base-url", default="http://localhost:8000")
    new.add_argument("--data-dir", default=DEFAULT_DATA_DIR)

    args = parser.parse_args()
    if args.command == "serve":
        server = make_server(args.data_dir, args.host, args.port)
        print(f"Shop at http://{args.host}:{args.port}/ (data in {args.data_dir})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    else:
        store = Store(args.data_dir)
        for _ in range(args.count):
            code = store.new_session(args.label, args.model, args.note)
            print(f"{args.base_url.rstrip('/')}/s/{code}")


if __name__ == "__main__":
    main()
