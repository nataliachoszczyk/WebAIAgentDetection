# Event log format (version 1)

The page records the events of each session. The detectors and the analysis read these logs. The code of the format is in `src/shop/logger/schema.py` and `src/shop/store.py`.

## Sources for the set of events

Real sites record similar events. We use the same set, so that our detectors use only data that a real site can have.

| Type of tool | Examples | What the tool records |
|---|---|---|
| Web analytics | Google Analytics 4, Matomo | page views, scroll depth, clicks on links, form start and form submit, shop events (view item, add to cart, begin checkout, purchase) |
| Session replay | Microsoft Clarity, Hotjar | mouse movement, clicks, scroll, window size, focus of the tab, input without the text |
| Bot protection | reCAPTCHA v3, hCaptcha, Cloudflare Turnstile, DataDome | mouse and touch movement, the time of each key press, the `isTrusted` flag of events, the browser fingerprint (user agent, `navigator.webdriver`, languages, screen, time zone, WebGL renderer) |

The logger does not record the text that a person types into a text field. It records only the length of the text and the type of the key (letter, digit, Backspace and so on). It records the value of a select field, a check box or a radio button. The shop events record the data of the order, because the tasks give this data.

## Files

The server writes all files into one data folder (default `data/shop/`):

- `sessions.jsonl`: one line for each session code. Fields: `session` (the code), `label` (`human`, `agent` or `bot`), `model` (the model id of an agent, or empty), `note`, `created` (Unix time in ms).
- `events/<session>.jsonl`: the events of one session, one JSON object on each line, in the order of arrival.

JSON Lines is plain text. A person can read it in an editor, and `pandas.read_json(path, lines=True)` loads it directly. `src.shop.store.load_events(data_dir)` loads all sessions into one DataFrame with the label and the model of each session.

## Fields of each event

The server adds these fields to each event:

| Field | Meaning |
|---|---|
| `v` | The version of the format (1) |
| `session` | The session code |
| `src` | `client` (from the browser) or `server` |
| `recv` | The time when the server received the event (Unix time in ms) |

The browser sends these fields with each event:

| Field | Meaning |
|---|---|
| `page` | A random id of one page view. A new page load gives a new id. |
| `seq` | The number of the event in the page view (0, 1, 2, ...) |
| `t` | The time from the start of the page load in ms (`performance.now()`) |
| `ts` | The time of the event (Unix time in ms) |
| `type` | The type of the event |
| `path` | The path of the page, for example `/product.html?id=ridge-runner` |

The server events have no `page` and no `seq`, and their `ts` is the same as `recv`. To put the events of a session in order, sort by `ts`, then by `page` and `seq`.

`target` describes an element in this form: the tag, then `#id`, `[name=...]` or the first class. Examples: `button#add-to-cart`, `input[name=email]`. A trap element has the form `trap:<trap id>`.

`trusted` is the value of `event.isTrusted`. It is `false` for an event that a script made with `dispatchEvent`.

## Event types

Events from the browser:

| Type | Fields | When |
|---|---|---|
| `page_view` | `title`, `referrer`, `time_origin` | The page loads. |
| `env` | `env` (object) | The page loads. `env` holds the browser fingerprint (see below). |
| `pointer_move` | `x`, `y`, `ptype` | The mouse moves. At most one event in 50 ms. |
| `pointer_down`, `pointer_up` | `x`, `y`, `button`, `ptype`, `target`, `trusted` | A mouse button goes down or up. |
| `click` | `x`, `y`, `button`, `target`, `text`, `href`, `trusted` | A click. `text` is the first 60 characters of the text of the element. |
| `wheel` | `dx`, `dy`, `trusted` | The mouse wheel turns. At most one event in 100 ms. |
| `scroll` | `sx`, `sy` | The page scrolls. At most one event in 100 ms. |
| `key_down` | `key`, `target`, `repeat`, `trusted` | A key goes down. `key` is `char`, `digit`, `space` or the name of a special key (`Backspace`, `Enter`, `Tab`, `Shift`, ...). |
| `key_up` | `key`, `target`, `trusted` | A key goes up. |
| `input` | `target`, `len`, `itype`, `trusted` | The text of a field changes. `len` is the new length. `itype` is the `inputType` (`insertText`, `insertFromPaste`, ...). It is empty when a script set the value. |
| `change` | `target`, `value`, `trusted` | A select field, a check box or a radio button changes. |
| `paste`, `copy` | `target`, `len` | A paste or a copy. `len` is the length of the text. |
| `focus`, `blur` | `target` | A form field gets or loses the focus. |
| `submit` | `target` | A form is sent. |
| `visibility` | `state` | The tab becomes `hidden` or `visible`. |
| `window_focus`, `window_blur` | | The browser window gets or loses the focus. |
| `resize` | `w`, `h` | The window size changes. At most one event in 250 ms. |
| `page_hide` | | The page closes or the user goes to a different page. |
| `trap` | `trap`, `action`, `target` | The user touches a trap (see `docs/test_page.md`). `action` is `focus`, `input`, `click`, `value` or `follow`. |
| `captcha` | `captcha`, `ok`, `ms`, `len`, `keys`, `pasted`, `seen`, `scrolled` | The user sends the checkout form with the reverse CAPTCHA. There is one event for each check and each attempt. `ms` is the time from the first view of the check (`seen` is `true`), or from the page load (`seen` is `false`). `keys` is the number of key presses in the field. `scrolled` is the part of the terms box that the user scrolled (0 to 1), only for `terms-code`. |
| `shop` | `action`, `product`, `size`, `color`, `qty`, `value` | A shop action: `view_item`, `add_to_cart`, `remove_from_cart`, `search`, `filter`, `sort`, `begin_checkout`, `apply_code`. |

The `env` object has these fields: `ua`, `webdriver`, `languages`, `platform`, `screen`, `window`, `outer`, `dpr`, `tz`, `cores`, `memory`, `touch`, `plugins`, `webgl_vendor`, `webgl_renderer`, `chrome`.

Events from the server:

| Type | Fields | When |
|---|---|---|
| `session_start` | `ua` | The user opens the session link `/s/<code>`. |
| `canary` | `trap` | The user opens a canary link. |
| `order` | `order`, `items`, `total`, `fields` | The user places an order. `fields` holds the data of the checkout form. |
| `contact` | `fields` | The user sends the contact form. |

## Example

```json
{"v": 1, "session": "3kP0x9QwZ1aB", "src": "client", "recv": 1764260000123, "page": "q8x2m1", "seq": 14, "t": 5321.4, "ts": 1764260000101, "type": "click", "path": "/product.html?id=ridge-runner", "x": 812, "y": 455, "button": 0, "target": "button#add-to-cart", "text": "Add to cart", "href": null, "trusted": true}
```
