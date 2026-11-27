# Worklog

## 2026-11-26

- Made the repository structure: `.gitignore`, `requirements.txt`, `README.md`, `KAGGLE.md`.
- Added the task text in Polish (`docs/task.md`) and in English (`docs/task_eng.md`).
- Added `jobs/` with `JOBS.md`, `kaggle.sh` and `wait.sh`, from the method in `KAGGLE.md`.
- Added the smoke test job `2026-11-26_01_smoke`: it checks the repository clone, the internet and headless Chromium with Playwright on a Kaggle CPU session.
- Checked the Kaggle Model Proxy (AI quota: $10 for each day, $100 for each month):
  - The account `jeronimoo` gets no proxy key. It needs phone or identity verification first.
  - The account `nataliachoszczyk` gets a key.
  - These models read a screenshot and call a `click` tool: `anthropic/claude-sonnet-5@default`, `google/gemini-3-flash-preview`, `google/gemini-3.1-flash-lite-preview`, `openai/gpt-5.4-nano-2026-03-17`.
  - `openai/gpt-oss-120b` does not accept images.
- Ran the Kaggle Benchmark Task `nataliachoszczyk/wad-probe` (version 3). One session did all steps:
  - It installed Playwright and Chromium in 35 s.
  - It made a screenshot of a local page.
  - It sent the screenshot to `gemini-3.1-flash-lite-preview` through the proxy, and the model called `click` on the correct button.
- Lessons from `wad-probe`:
  - The task runs in a Jupyter kernel with an asyncio loop. Thus the Playwright sync API must run in a separate thread.
  - In the task session, `MODEL_PROXY_URL` already ends with `/openapi`.
  - The session runs Python 3.12. `navigator.webdriver` is `true` in headless Chromium from Playwright.
- Added the general rules of the course project to `docs/task.md` and `docs/task_eng.md`: report format, grading criteria, the deadline (11 January 2027, 16:00).

## 2026-11-27

- Decided the hosting of the test page (wad-001, #21). See `docs/test_page.md`:
  - One Python server (standard library only) serves the page and writes the logs as JSON Lines files.
  - People and agents use the same public HTTPS address from a Cloudflare quick tunnel.
  - Each session starts from a link with a session code. The server records events only for a valid code.
