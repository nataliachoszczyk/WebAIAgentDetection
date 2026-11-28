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
