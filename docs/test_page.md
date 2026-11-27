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
