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

Run `.venv/bin/python -m pytest`. The browser tests do all four tasks in headless Chromium.

### Run the shop

1. Start the server: `.venv/bin/python -m src.shop serve --port 8000`
2. Make a session link for a person: `.venv/bin/python -m src.shop new-session --label human`
3. Make a session link for an agent: `.venv/bin/python -m src.shop new-session --label agent --model <model id>`
4. Open the link in a browser. The session starts on the task page.

The server writes the logs into `data/shop/`. Git does not keep this folder. For a public HTTPS address, see "Hosting" in [`docs/test_page.md`](docs/test_page.md).

To load all logs into one pandas DataFrame, use `src.shop.store.load_events("data/shop")`.
