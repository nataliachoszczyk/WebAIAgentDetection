# Test page

The test page is a small web shop for shoes ("Pace & Sole"). Agents and people do the same tasks on it. The page records the events of each session for the detectors.

## Hosting (wad-001)

Decision: one small Python server serves the page and keeps the logs. All sessions use the same server and the same address.

- The server uses only the Python standard library. It runs on a laptop, in a Kaggle session or on any small machine without changes.
- The server writes the logs as JSON Lines files into a local folder (default `data/shop/`). Git does not keep this folder.
- For the collection of traces, a team member runs the server and makes it public with a Cloudflare quick tunnel (`cloudflared tunnel --url http://localhost:8000`). The tunnel is free, needs no account and gives an HTTPS address.
- People and agents get the same public HTTPS address. Thus a detector cannot use the address, the protocol or the network path as a signal.
- For tests and development, use `http://localhost:8000`.
- Each session starts from a link with a session code: `/s/<code>`. The server keeps the list of the codes and the label of each code. It records events only for a valid code. Thus strangers cannot fill the logs with noise.

Rejected options:

| Option | Reason |
|---|---|
| GitHub Pages and an external log store | Needs a second service, an account and a key in the page. The key in a public page lets strangers write logs. |
| Our own domain and a server | Costs money and time. The tunnel gives the same result for this study. |
| Localhost for agents, public page for people | The two groups then get different conditions. A detector can then find the group from the setup, not from the behavior. |

Limits:

- The quick tunnel gives a new address each time. Make the session links after the start of the tunnel.
- The laptop must run during the collection of traces. After the collection, upload the logs to the private Kaggle dataset.

## The shop (wad-003)

The shop "Pace & Sole" sells 12 models of shoes in four categories: `running`, `hiking`, `casual` and `formal`. It has the usual parts of a small web shop:

- a home page with a search field, category filters, a size filter, a price filter and a sort order,
- a product page with colors, sizes (some sizes are sold out), the quantity and reviews,
- a cart with a discount code field,
- a checkout with the delivery address, the delivery option and the payment option,
- an order confirmation with an order number,
- a contact form and a page with the delivery, the returns and the terms of sale.

The shop takes no money. The checkout has no card fields: the payment options are "pay on delivery" and "bank transfer".

### Tasks

`src/shop/tasks.json` holds the four tasks. People and agents get the same tasks:

1. Find a product: add the Ridge Runner in size 43 and color Moss to the cart.
2. Compare products: add the cheapest waterproof boot of the category `hiking` that is available in size 42. The correct answer is Alder Trek WP: the cheaper Pinecrest Mid WP has no size 42.
3. Place the order with the given address, standard delivery and payment on delivery.
4. Ask a question in the contact form, with the order number from task 3.

A session starts on the study page (`/study.html`). This page tells what the shop records and shows the tasks. During the session, a panel at the right side of each page shows the tasks. The panel has its own column, so it never covers a part of the shop. The API (`/api/tasks`) does not give the expected answers. The analysis reads them from `tasks.json`.

### Structure of the code

| Path | Content |
|---|---|
| `src/shop/__main__.py` | The command line: `serve` and `new-session` |
| `src/shop/server.py` | The HTTP server: static files, session links, the order API and the contact API |
| `src/shop/store.py` | The log store (see `docs/log_format.md`) |
| `src/shop/tasks.json` | The tasks and the expected answers |
| `src/shop/site/` | The pages of the shop (HTML, CSS, JavaScript, images) |
| `src/shop/site/assets/data/products.json` | The product catalog |
| `src/shop/make_images.py` | Makes the shoe images from the catalog |
| `src/shop/logger/` | The format of the events and the event logger |
| `tests/` | The tests (`pytest`). `tests/test_e2e.py` does all four tasks in Chromium. |

The pages use plain HTML, CSS and JavaScript modules. There is no build step.

### Run the shop

1. Start the server: `python -m src.shop serve --port 8000`.
2. Make a session link: `python -m src.shop new-session --label human`.
3. Open the link in a browser.

For an agent, give the model id: `python -m src.shop new-session --label agent --model <model id>`. For a public address, give it with `--base-url`.
