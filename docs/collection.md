# Collection of human traces

This procedure collects traces from people through the public shop. Details: "Hosting" in `docs/test_page.md`.

## 1. Start

1. Start the containers: `docker compose up -d --build`
2. Find the public address: `docker compose logs tunnel | grep trycloudflare.com`
3. Open `https://<name>.trycloudflare.com` in a browser to check the address.

## 2. Make the links

Do option A or option B. Make the links again after each start, because the address changes.

### Option A: one link for a group

1. Make the link: `docker compose exec shop /usr/bin/python3 -m src.shop new-join --label human --max <N> --until <YYYY-MM-DD> --base-url https://<name>.trycloudflare.com`
2. Send the link to the group.

### Option B: one link for each person

1. Make the links: `docker compose exec shop /usr/bin/python3 -m src.shop new-session --label human --count <N> --base-url https://<name>.trycloudflare.com`
2. Send one link to each person.

## 3. During the collection

- See the progress: `docker compose exec shop /usr/bin/python3 -m src.shop status`
- Keep the laptop on. If the containers stop, the shop is not available.

## 4. End

1. Copy the logs to the laptop: `docker compose cp shop:/app/data/shop/. data/shop/`
2. Stop the containers: `docker compose down`
3. Make one zip file: `cd data && zip -r shop_<YYYY-MM-DD>.zip shop`
4. Upload the zip file to the private Kaggle dataset. After the first collection, make this dataset from the output of a Kaggle notebook.

Do not use `docker compose down -v` before step 1. The option `-v` deletes the logs.

## 5. Watch the sessions

1. Make one video for each session: `.venv/bin/python -m src.replay data/shop --out data/replay`
2. Open the videos in `data/replay/`. Do not put the videos into git.
