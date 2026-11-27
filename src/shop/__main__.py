"""Command line of the test shop. Run `python -m src.shop --help` to see the commands."""

import argparse
import time
from datetime import datetime, timedelta

from .server import make_server
from .store import Store

DEFAULT_DATA_DIR = "data/shop"
LABELS = ["human", "agent", "bot"]


def end_of_day(text):
    """Return the end of the day YYYY-MM-DD in local time, as Unix time in ms."""
    day = datetime.strptime(text, "%Y-%m-%d")
    return int((day + timedelta(days=1)).timestamp() * 1000) - 1


def show_time(ms):
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M") if ms else "-"


def status(store):
    sessions = list(store.sessions().values())
    print(f"{'label':8} {'sessions':>8} {'started':>8} {'ordered':>8} {'done':>8}")
    for label in LABELS:
        group = [s for s in sessions if s.get("label") == label]
        if group:
            counts = [sum(1 for s in group if s.get(k)) for k in ("started", "ordered", "closed")]
            print(f"{label:8} {len(group):8} {counts[0]:8} {counts[1]:8} {counts[2]:8}")
    now = time.time() * 1000
    for secret, join in store.joins().items():
        used = store.join_sessions(secret)
        done = sum(1 for s in used if s.get("closed"))
        state = "expired" if now > join["until"] else "full" if len(used) >= join["max"] else "open"
        print(f"join {secret[:6]}… {join['label']}: {len(used)}/{join['max']} used, {done} done,"
              f" until {show_time(join['until'])} ({state}) {join.get('note') or ''}")


def main():
    parser = argparse.ArgumentParser(prog="python -m src.shop")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", parents=[common], help="run the shop server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    new = commands.add_parser("new-session", parents=[common], help="make links for one person or one agent run each")
    new.add_argument("--label", required=True, choices=LABELS)
    new.add_argument("--model", help="the model id of the agent")
    new.add_argument("--note")
    new.add_argument("--count", type=int, default=1)
    new.add_argument("--base-url", default="http://localhost:8000")

    join = commands.add_parser("new-join", parents=[common], help="make one link for a group: each visit makes a new session")
    join.add_argument("--label", required=True, choices=LABELS)
    join.add_argument("--max", type=int, required=True, help="the maximum number of sessions")
    join.add_argument("--until", help="the last day of the link, YYYY-MM-DD (default: in 7 days)")
    join.add_argument("--model", help="the model id of the agent")
    join.add_argument("--note")
    join.add_argument("--base-url", default="http://localhost:8000")

    commands.add_parser("status", parents=[common], help="show the number of sessions and the use of the join links")

    args = parser.parse_args()
    store = Store(args.data_dir)
    base_url = getattr(args, "base_url", "").rstrip("/")
    if args.command == "serve":
        server = make_server(args.data_dir, args.host, args.port)
        print(f"Shop at http://{args.host}:{args.port}/ (data in {args.data_dir})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    elif args.command == "new-session":
        for _ in range(args.count):
            print(f"{base_url}/s/{store.new_session(args.label, args.model, args.note)}")
    elif args.command == "new-join":
        until = end_of_day(args.until) if args.until else int((time.time() + 7 * 86400) * 1000)
        secret = store.new_join(args.label, args.max, until, args.model, args.note)
        print(f"{base_url}/join/{secret}")
        print(f"Up to {args.max} sessions ({args.label}) until {show_time(until)}.")
    else:
        status(store)


if __name__ == "__main__":
    main()
