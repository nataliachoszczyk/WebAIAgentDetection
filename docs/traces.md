# Traces of agents and people

This file tells which sessions the study uses and how we check their logs. The commands read the data folder each time. Thus new sessions need only a new run of the same commands.

## The sessions of the study (wad-011)

`src/traces.py` holds the rules. The analysis uses a session only if all these conditions are true:

1. The label is `human` or `agent`.
2. The note is not a note of a test (`start-test`, `dev`, `test`, `e2e test`).
3. The session started (the person or the agent pressed "Start").
4. The session is not in the list `EXCLUDED`.

Keep all exclusions in `EXCLUDED` in `src/traces.py`, each with its reason. Do not delete the logs of an excluded session.

| Session | Reason |
|---|---|
| `_1QnFCzrsUVW` (human) | Link preview bots opened the link first, and the tunnel failed during the session. |
| 6 runs of small models | The runs came before the tools accepted the mistakes of small models (see `docs/agent.md`). |
| 6 runs of small models | The model API refused the first request, because of a wrong effort option. The runs have no step. |

The rules also remove the agent sessions of version 1 (`STUDY_AGENT_VERSIONS`) and the runs with the note `run=dev`.

The study assumes that each human session comes from a different person.

### Human sessions

State on 2026-11-28: 4 sessions of people, 3 in the study. All 3 did the four tasks. The data folder also has 42 agent sessions of the study (see `docs/agent.md`).

How many people we need: the false alarm rate (FPR) of a detector is a share of the human sessions. With n people and no false alarm, the upper limit of the 95% interval is about 3/n (the "rule of three"). Thus 10 people give an upper limit of 30%, and 20 people give 15%. The aim is at least 15 people. The collection continues with `docs/collection.md`.

People know what we record. The invitation tells about the study. The task page tells that the shop records what they type and send in the forms.

### Agent sessions

Each agent session has the label `agent`, the model id and a note with the setup: `browser=<plain|hidden> motion=<direct|human> effort=<effort> run=<group>`. See `docs/agent.md`. The step log of the agent is in `data/agent/<session>.jsonl`.

## The check of the logs (wad-012)

Run the check:

```bash
.venv/bin/python -m src.traces data/shop --agent-logs data/agent --out results/log_check.csv
```

Add `--all` to also show the sessions that are not in the study. The command writes one row for each session into `results/log_check.csv` and shows the sessions of the study. The column `problems` lists the faults that need a look:

| Measure | Meaning |
|---|---|
| `seq_gaps` | Events that are not in the log: a `seq` number of a page that the log does not have. |
| `pages_no_view` | Pages where the first event is not `page_view`. |
| `pages_no_hide` | Pages without `page_hide`. The last batch of the page can be lost. |
| `late_events` | Events that arrived more than 5 s after they occurred. |
| `unknown_fields` | Fields or event types that are not in `docs/log_format.md`. |
| `task1_ok`, `task2_ok` | The order has the products of tasks 1 and 2 (see `expected` in `tasks.json`). |
| `captcha_ok` | The last attempt passed all three checks of the reverse CAPTCHA. |
| `traps` | The traps that the session triggered. |
| `agent_end` | How the agent run ended: `finish`, `max_steps`, `max_cost` or `error`. |

### Result of the check (2026-11-28)

The check ran on 3 human and 42 agent sessions of the study:

- No session has a gap in `seq`, a page without `page_view` at the start or an unknown field.
- No session of the study has a page without `page_hide`. Only the excluded human session `_1QnFCzrsUVW` has 2 such pages.
- No event arrived more than 5 s late.
- The only problems are agent runs that the loop guard stopped (6 runs of small models, `agent end: loop`). Their logs are complete until the stop.

We also read a sample of logs by hand: the 3 human sessions and one session of each model. These points are correct:

- The order of the events on each page agrees with the step log of the agent: each tool call gives the expected events (for example `pointer_move`, `pointer_down`, `pointer_up`, `click` for a click).
- The last `value` of each form field is the text that the agent typed. The `order` and `contact` events have the same data.
- The `captcha` events agree with the answers in the step log. Small models needed more attempts: `gpt-4o-mini` and `mistral-small` needed 9 attempts in one session each. Each person needed one attempt. 26 Claude runs needed one attempt, 2 runs needed two, and one run did not try.
- Each `trap` event agrees with the step log, for example the code `AGENT-CHECK` in a tool call of `gemini-2.5-flash-lite`.
- The `env` event agrees with the browser of the run (see "The `hidden` browser" in `docs/agent.md`).
