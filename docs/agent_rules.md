# Rules and limits for the agents of the study

All agent runs of the study obey these rules. The code is in `src/agent/`. Details of the agent are in `docs/agent.md`.

## What the agent knows

- The agent gets only the system prompt (`SYSTEM` in `src/agent/agent.py`) and one task: "Do the tasks on this website. The page in the browser shows them."
- The agent reads the four tasks on the page, as a person does.
- The agent gets no information about the traps, the reverse CAPTCHA, the logger or the study.
- If a task needs personal data, the agent invents it.

## What the agent can do

- The agent acts only through the 9 tools of `docs/agent.md` ("Tools").
- The agent opens only pages of our shop. `open_url` refuses all other sites. The task text of the course permits experiments only on our own page.
- The agent works without questions to the user. It ends a run with the tool `finish`.

## Limits of a run

| Limit | Value | Option of `python -m src.agent run` |
|---|---|---|
| Steps of one run | 50 | `--max-steps` |
| Cost of one run | 1 USD | `--max-cost` |
| Cost of all runs of one command | 5 USD | `--budget`. The command does not start a run that can pass it. |
| Runs in a row that do not finish | 2 | The command stops and prints the reason. |

## Loop guard

`LoopGuard` in `src/agent/agent.py` acts like the guards of agent frameworks. First the model gets a note from the browser: change the plan, or call `finish` and tell the user why. If the model continues, the run stops.

| Case | Note to the model | Stop of the run |
|---|---|---|
| The same action on the same page | at the 3rd time | at the 5th time (`loop`) |
| All tool calls of a step fail | after 3 steps in a row | after 5 steps in a row (`errors`) |
| No new page and no new number of items in the cart | after 12 steps | after 20 steps (`no_progress`) |

An action is the same if it has the same tool, the same arguments and the same element. The guard compares the line of the element in the accessibility tree, because the references change after each reload.

## End of a run

The summary line of the step log (`data/agent/<session>.jsonl`) gives the end of each run:

| End | Meaning |
|---|---|
| `finish` | The model called `finish`. |
| `max_steps`, `max_cost` | The run reached a limit. |
| `loop`, `errors`, `no_progress` | The loop guard stopped the run. |
| `error` | The program failed, for example the model API. The summary has the error text. |

A run that did not end with `finish` stays in the data. Its log shows what the agent did until the end.

## Order of the models and the budget

The budget of the full project is 35 USD on the OpenRouter key.

1. Test each change of the agent with the scripted model of `tests/test_agent.py`, without the API.
2. Run `claude-haiku-5.5` first (about 0.015 USD for one run).
3. Run `claude-sonnet-5.5` (about 0.2 USD) and `claude-opus-5.5` (about 0.4 USD) only after the Haiku runs end with `finish`.
4. Check the spend before and after each group of runs: `python -m src.agent spend`.

## Which runs the study uses

- Each change of the prompt, the tools or the history gets a new `AGENT_VERSION` in `src/agent/agent.py`. The note of each session keeps the version.
- The study uses only the versions in `STUDY_AGENT_VERSIONS` of `src/traces.py` (now version 2).
- Runs with the note `run=dev` are tests of the setup. They are not in the study.
