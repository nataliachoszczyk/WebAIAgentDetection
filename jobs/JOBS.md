# Kaggle jobs

## How to run a job

1. Make a new folder `jobs/runs/YYYY-MM-DD_NN_<job name>` (NN: the next number after the last job, not a number for each day). Put `run.py`, `kernel-metadata.json` and one `<codename>.yaml` for each codename into it. Copy them from the last job.
2. Use one Kaggle kernel for each job: the kernel id is `<kaggle user>/wad-<job name>`. The Kaggle API does not give the version ID.
3. The user in the kernel id must be the account that `jobs/kaggle.sh` selects. The account needs phone verification (for internet) and access to the project dataset.
4. A job that calls an LLM API needs the key in Kaggle Secrets. Attach the secret to the kernel once on the web page of the kernel.
5. The script clones the branch in `run.py` from GitHub, so push the code first.
6. Push with `bash jobs/kaggle.sh kernels push -p jobs/runs/<job folder>`. Then run `bash jobs/wait.sh <kernel id> <job name>` as a background task.
7. Download only small outputs: `bash jobs/kaggle.sh kernels output <kernel id> -p jobs/runs/<job folder>/output --file-pattern '(json|csv)$'`.

One folder in `jobs/runs/` has one row. A new version of a job uses the same row and gets a note in the comment.

Status values: to run, waiting for another job, queued, running, complete, failed, cancelled. The status cell has only one of these values, because `wait.sh` changes it. Put results into the comment.

| Date | Job | Folder | Link | Comment | Status |
|---|---|---|---|---|---|
| 2026-11-26 | smoke | `2026-11-26_01_smoke` | [wad-smoke](https://www.kaggle.com/code/jeronimoo/wad-smoke) | Check the repository clone, the internet, Playwright and headless Chromium on a CPU session. | to run |
| 2026-11-26 | probe | `2026-11-26_02_probe` | [wad-probe](https://www.kaggle.com/benchmarks/tasks/nataliachoszczyk/wad-probe) | A Kaggle Benchmark Task, not a kernel. Push: `kaggle benchmarks tasks push wad-probe -f probe_task.py --wait`. Check Playwright, Chromium and the model proxy in one session. Version 1: the Playwright sync API failed in the asyncio loop. Version 2: a wrong proxy URL. Version 3: Chromium install 35 s, the model called `click` from a screenshot. | complete |
