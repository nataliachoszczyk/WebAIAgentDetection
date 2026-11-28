"""The sessions of the study and the check of their logs (wad-011, wad-012). See docs/traces.md.

Run: python -m src.traces [data folder] [--agent-logs data/agent] [--out results/log_check.csv]
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from src.shop.logger.schema import CLIENT_EVENTS, COMMON_FIELDS, SERVER_EVENTS

TASKS = json.loads((Path(__file__).parent / "shop" / "tasks.json").read_text())

# Sessions that do not go into the analysis. Keep all exclusions here, with the reason.
EXCLUDED = {
    "_1QnFCzrsUVW": "link preview bots opened the link first, and the tunnel failed during the session",
}
# The first runs of small models came before the tools accepted their mistakes (see docs/agent.md).
EXCLUDED.update({code: "small model before the tool fixes of 2026-11-28" for code in (
    "SD8nICbv6Jrz", "liXfHzey-jOj", "sJPQbPSAVFAj", "ZXq8EvCIwncN", "3hJwzBr-qYs_", "pvN2J7vUYO6D")})
EXCLUDED.update({code: "the model API refused the first request (a wrong effort option)" for code in (
    "-p98yJyFSZw9", "iNiKITsujmAg", "EMeWLWmxxfHp", "W4td1KtTEn7R", "qrJOcKrfx9LI", "sbEYUF6oLXHq")})
# The versions of the agent (AGENT_VERSION in src/agent/agent.py) in the study. Older versions were tests.
STUDY_AGENT_VERSIONS = {"2"}
# Notes of sessions that only tested the setup.
TEST_NOTES = {"start-test", "dev", "e2e test", "test"}

SERVER_FIELDS = ("v", "session", "src", "recv")
LATE_MS = 5000


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_note(note):
    """An agent note has the form `browser=plain motion=direct effort=medium run=wad-009`."""
    return dict(part.split("=", 1) for part in (note or "").split() if "=" in part)


def sessions(data_dir):
    """Return the sessions of the data folder, with the reason when a session is not in the study."""
    merged = {}
    for record in read_jsonl(Path(data_dir) / "sessions.jsonl"):
        merged.setdefault(record["session"], {}).update(record)
    result = []
    for code, s in merged.items():
        setup = parse_note(s.get("note"))
        run = setup.get("run", s.get("note"))
        reason = EXCLUDED.get(code)
        if reason is None and (run in TEST_NOTES or s.get("label") not in ("human", "agent")):
            reason = "test of the setup"
        if reason is None and s.get("label") == "agent" and setup.get("agent") not in STUDY_AGENT_VERSIONS:
            reason = "older version of the agent"
        if reason is None and not s.get("started"):
            reason = "never started"
        result.append({"session": code, "label": s.get("label"), "model": s.get("model"), "run": run,
                       "browser": setup.get("browser"), "motion": setup.get("motion"), "effort": setup.get("effort"),
                       "agent": setup.get("agent"),
                       "created": s.get("created"), "in_study": reason is None, "reason": reason})
    return result


def study_sessions(data_dir):
    """The sessions that the analysis uses."""
    return [s for s in sessions(data_dir) if s["in_study"]]


def check_events(events):
    """Check the completeness of the log of one session. Return a dict of measures."""
    pages = defaultdict(list)
    unknown = Counter()
    for e in events:
        kind = e.get("type")
        known = CLIENT_EVENTS.get(kind) if e.get("src") == "client" else SERVER_EVENTS.get(kind)
        if known is None:
            unknown[f"type:{kind}"] += 1
            continue
        allowed = set(SERVER_FIELDS) | set(known) | ({"ts", "type"} if e.get("src") == "server" else set(COMMON_FIELDS))
        for name in set(e) - allowed:
            unknown[f"{kind}.{name}"] += 1
        if e.get("src") == "client":
            pages[e["page"]].append(e)

    gaps = no_view = no_hide = late = 0
    for page_events in pages.values():
        seqs = sorted({e["seq"] for e in page_events})
        gaps += seqs[-1] + 1 - len(seqs)
        first = min(page_events, key=lambda e: e["seq"])
        no_view += first["type"] != "page_view"
        no_hide += not any(e["type"] == "page_hide" for e in page_events)
        late += sum(e["recv"] - e["ts"] > LATE_MS for e in page_events)

    by_type = defaultdict(list)
    for e in events:
        by_type[e["type"]].append(e)
    orders = by_type["order"]
    items = orders[0]["items"] if orders else []
    expected = TASKS["expected"]

    def has(task):
        want = expected[task]
        return any(i["product"] == want["product"] and i["size"] == want["size"]
                   and want.get("color") in (None, i["color"]) for i in items)

    captchas = by_type["captcha"]
    last_try = {c["captcha"]: c for c in captchas}  # the last attempt of each check
    env = by_type["env"][0]["env"] if by_type["env"] else {}
    times = [e["ts"] for e in events if "ts" in e]
    return {
        "events": len(events),
        "pages": len(pages),
        "seq_gaps": gaps,
        "pages_no_view": no_view,
        "pages_no_hide": no_hide,
        "late_events": late,
        "unknown_fields": ";".join(f"{k}={v}" for k, v in sorted(unknown.items())),
        "minutes": round((max(times) - min(times)) / 60000, 2) if times else 0,
        "webdriver": env.get("webdriver"),
        "headless_ua": "Headless" in env.get("ua", ""),
        "ordered": bool(orders),
        "contact": bool(by_type["contact"]),
        "task1_ok": has("find-product"),
        "task2_ok": has("compare-products"),
        "captcha_tries": len(captchas) // 3 if captchas else 0,
        "captcha_ok": bool(last_try) and all(c["ok"] for c in last_try.values()),
        "traps": ";".join(sorted({e["trap"] for e in by_type["trap"]} | {e["trap"] for e in by_type["canary"]})),
        "key_chars": sum(e["key"] == "char" for e in by_type["key_down"]),
        "pointer_moves": len(by_type["pointer_move"]),
    }


def agent_summary(agent_dir, code):
    lines = read_jsonl(Path(agent_dir) / f"{code}.jsonl")
    summary = next((r for r in lines if r.get("type") == "summary"), None)
    if summary is None:
        return {"agent_end": "no step log" if not lines else "no summary"}
    return {"agent_end": summary["end"], "agent_steps": summary["steps"], "agent_cost": summary["cost"],
            "agent_error": summary.get("error")}


def check(data_dir, agent_dir="data/agent", only_study=False):
    """One row for each session: the setup, the reason of an exclusion and the measures of the log."""
    rows = []
    for s in sessions(data_dir):
        if only_study and not s["in_study"]:
            continue
        row = dict(s)
        row.update(check_events(read_jsonl(Path(data_dir) / "events" / f"{s['session']}.jsonl")))
        if s["label"] == "agent":
            row.update(agent_summary(agent_dir, s["session"]))
        row["problems"] = ";".join(problems(row))
        rows.append(row)
    return rows


def problems(row):
    """The faults of a log that need a look before the analysis. A task that the session did not do is not a fault."""
    found = []
    if row["events"] == 0:
        return ["no events"]
    for name in ("seq_gaps", "pages_no_view", "pages_no_hide"):
        if row[name]:
            found.append(f"{name}={row[name]}")
    if row["unknown_fields"]:
        found.append("unknown fields")
    if row["label"] == "agent" and row.get("agent_end") != "finish":
        found.append(f"agent end: {row.get('agent_end')}")
    return found


def summary(table):
    """One row for each group of the study: people, and each model with each browser and motion."""
    study = table[table.in_study].copy()
    study["model"] = study["model"].fillna("-")
    study[["browser", "motion"]] = study[["browser", "motion"]].fillna("-")
    study["all_tasks"] = study.task1_ok & study.task2_ok & study.contact & study.captcha_ok
    study["any_trap"] = study.traps.fillna("") != ""
    for name in ("agent_cost", "agent_steps"):
        if name not in study:
            study[name] = None
    groups = study.groupby(["label", "model", "browser", "motion"], dropna=False)
    return groups.agg(sessions=("session", "size"), all_tasks=("all_tasks", "sum"), any_trap=("any_trap", "sum"),
                      minutes=("minutes", "median"), events=("events", "median"),
                      steps=("agent_steps", "median"), cost_usd=("agent_cost", "mean")).round(3).reset_index()


def main():
    import pandas as pd

    parser = argparse.ArgumentParser(prog="python -m src.traces")
    parser.add_argument("data", nargs="?", default="data/shop")
    parser.add_argument("--agent-logs", default="data/agent")
    parser.add_argument("--out", default="results/log_check.csv")
    parser.add_argument("--all", action="store_true", help="also show the sessions that are not in the study")
    args = parser.parse_args()

    table = pd.DataFrame(check(args.data, args.agent_logs))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    table.drop(columns=["created"]).to_csv(args.out, index=False)
    shown = table if args.all else table[table.in_study]
    columns = ["session", "label", "model", "browser", "motion", "events", "pages", "seq_gaps", "minutes",
               "task1_ok", "task2_ok", "captcha_ok", "traps", "problems"]
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 40):
        print(shown[columns].fillna("").to_string(index=False))
    groups = summary(table)
    groups.to_csv(Path(args.out).with_name("session_summary.csv"), index=False)
    print("\n" + groups.astype(object).fillna("").to_string(index=False))
    study = table[table.in_study]
    print(f"\nIn the study: {(study.label == 'human').sum()} human and {(study.label == 'agent').sum()} agent sessions."
          f" Not in the study: {(~table.in_study).sum()}. Written: {args.out}")


if __name__ == "__main__":
    main()
