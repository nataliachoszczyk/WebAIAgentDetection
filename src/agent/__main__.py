"""Command line of the agent. Run `python -m src.agent --help`. See docs/agent.md."""

import argparse
import json
import subprocess
from pathlib import Path

from .agent import AGENT_VERSION, run_episode
from .browser import BROWSERS, MOTIONS
from .model import Model, spend


def new_link(args):
    """Make a session link with the label `agent`. The note keeps the setup of the run."""
    note = (f"browser={args.browser} motion={args.motion} effort={args.effort or 'none'} agent={AGENT_VERSION}"
            f" run={args.note}")
    if args.sessions == "docker":
        command = ["docker", "compose", "exec", "-T", "shop", "/usr/bin/python3", "-m", "src.shop", "new-session",
                   "--label", "agent", "--model", args.model, "--note", note, "--base-url", args.base_url]
        return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]
    from src.shop.store import Store

    return f"{args.base_url.rstrip('/')}/s/{Store(args.sessions).new_session('agent', args.model, note)}"


def main():
    parser = argparse.ArgumentParser(prog="python -m src.agent")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("spend", help="show the spend of the OpenRouter key")
    run = commands.add_parser("run", help="run the agent for one or more sessions")
    run.add_argument("--model", required=True, help="for example anthropic/claude-haiku-5.5")
    run.add_argument("--effort", default="medium", help="the effort of the model, or an empty text for none")
    run.add_argument("--api", default="openrouter", choices=["openrouter", "kaggle"])
    run.add_argument("--browser", default="plain", choices=BROWSERS)
    run.add_argument("--motion", default="direct", choices=MOTIONS)
    run.add_argument("--link", help="a session link; else the command makes a new link for each run")
    run.add_argument("--sessions", default="docker",
                     help="where to make the links: `docker` (the public shop) or the data folder of a local shop")
    run.add_argument("--base-url", default="http://localhost:8000", help="the address of the shop in the links")
    run.add_argument("--note", default="dev", help="the name of the group of runs, for example wad-009")
    run.add_argument("--runs", type=int, default=1)
    run.add_argument("--max-steps", type=int, default=50)
    run.add_argument("--max-cost", type=float, default=1.0, help="USD for one run")
    run.add_argument("--budget", type=float, default=5.0, help="USD for all runs of this command")
    run.add_argument("--out", default="data/agent", help="the folder for the step logs")
    args = parser.parse_args()

    if args.command == "spend":
        print(json.dumps(spend()))
        return
    model = Model(args.model, effort=args.effort or None, api=args.api)
    total, failed = 0.0, 0
    for i in range(args.runs):
        if total + args.max_cost > args.budget:
            print(f"Stop: the next run can pass the budget ({total:.3f} of {args.budget} USD used).")
            break
        link = args.link or new_link(args)
        session = link.rstrip("/").rsplit("/", 1)[-1]
        print(f"Run {i + 1}/{args.runs}: session {session}", flush=True)
        summary = run_episode(model, link, Path(args.out) / f"{session}.jsonl", args.browser, args.motion,
                              args.max_steps, args.max_cost, seed=session)
        total += summary["cost"]
        failed = 0 if summary["end"] == "finish" else failed + 1
        if failed >= 2:
            print(f"Stop: {failed} runs in a row did not finish. Look at the step logs before more runs.")
            break
        print(json.dumps({k: summary.get(k) for k in ("end", "steps", "cost", "seconds", "error", "finish")},
                         ensure_ascii=False), flush=True)
    print(f"Cost of all runs: {total:.4f} USD")


if __name__ == "__main__":
    main()
