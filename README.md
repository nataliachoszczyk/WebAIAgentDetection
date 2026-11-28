# Detection of LLM Web Agents

This project examines how a web site can distinguish an LLM browser agent from a human. We look at the problem from the side of the defender.

- Task: [`docs/task_eng.md`](docs/task_eng.md) (Polish original: [`docs/task.md`](docs/task.md))
- Worklog: [`docs/WORKLOG.md`](docs/WORKLOG.md)
- Kaggle method: [`KAGGLE.md`](KAGGLE.md)

## Test page

The test page is a small web shop for shoes ("Pace & Sole"). Agents and people do the same four tasks on it. The page records the events of each session, and it has traps and a reverse CAPTCHA.

- Description of the page, the tasks, the traps and the reverse CAPTCHA: [`docs/test_page.md`](docs/test_page.md)
- Format of the event logs: [`docs/log_format.md`](docs/log_format.md)
- Code: [`src/shop/`](src/shop/)

### Install

Use Python 3.12 and uv.

1. Make the environment: `uv venv --python 3.12 .venv`
2. Install the packages: `uv pip install --python .venv -r requirements.txt`
3. Install Chromium for Playwright: `.venv/bin/playwright install chromium` (on Windows: `.venv\Scripts\playwright install chromium`)

### Run the tests

Run `.venv/bin/python -m pytest`. The browser tests do all four tasks in headless Chromium, Firefox and WebKit. To install Firefox and WebKit, run `.venv/bin/playwright install firefox webkit`. WebKit also needs system libraries: `sudo .venv/bin/playwright install-deps webkit`. A test for a browser that cannot start is skipped.

### Run the shop

1. Start the server: `.venv/bin/python -m src.shop serve --port 8000`
2. Make a session link for a person: `.venv/bin/python -m src.shop new-session --label human`
3. Make a session link for an agent: `.venv/bin/python -m src.shop new-session --label agent --model <model id>`
4. Open the link in a browser. The session starts on the task page.

To give one link to a group of people, make a join link: `.venv/bin/python -m src.shop new-join --label human --max 15 --until <YYYY-MM-DD>`. Each new browser gets its own session. To see the progress, run `.venv/bin/python -m src.shop status`.

The server writes the logs into `data/shop/`. Git does not keep this folder. For a public HTTPS address, see "Hosting" in [`docs/test_page.md`](docs/test_page.md).

To load all logs into one pandas DataFrame, use `src.shop.store.load_events("data/shop")`.

## Traces of agents and people

The agent does the four tasks through a model API. People do the same tasks through the same public address.

- The agent, its tools and its runs: [`docs/agent.md`](docs/agent.md)
- Rules and limits for the agents of the study: [`docs/agent_rules.md`](docs/agent_rules.md)
- Collection of human traces: [`docs/collection.md`](docs/collection.md)
- The sessions of the study and the check of the logs: [`docs/traces.md`](docs/traces.md)
- Code: [`src/agent/`](src/agent/), [`src/traces.py`](src/traces.py)

### Run the agent

The agent needs `OPENROUTER_API_KEY` in `.env`.

1. Start the public shop: `docker compose up -d --build`. Find its address in `docker compose logs tunnel`.
2. Check the spend of the key: `.venv/bin/python -m src.agent spend`
3. Run the agent: `.venv/bin/python -m src.agent run --model anthropic/claude-haiku-5.5 --base-url https://<name>.trycloudflare.com --runs 3 --note wad-009`
4. Copy the logs and stop the shop: `docker compose cp shop:/app/data/shop/. data/shop/`, then `docker compose down`.

Options of the run: `--browser plain|hidden`, `--motion direct|human`, `--effort`, `--max-steps`, `--max-cost`, `--budget`. See [`docs/agent_rules.md`](docs/agent_rules.md).

### Check the logs

1. Extract the zip of the private Kaggle dataset `jankombajn/wad-traces` into `data/` (see [`docs/traces.md`](docs/traces.md)).
2. Run `.venv/bin/python -m src.traces`. The command writes `results/log_check.csv` and `results/session_summary.csv`.
3. Make the videos of the sessions: `.venv/bin/python -m src.replay data/shop --out data/replay`
