"""The event log format (version 1). See docs/log_format.md."""

FORMAT_VERSION = 1

MAX_STRING = 300
MAX_BATCH = 500

# Fields that the browser sends with each event.
COMMON_FIELDS = ("page", "seq", "t", "ts", "type", "path")

# The fields of each event type, in addition to the common fields.
CLIENT_EVENTS = {
    "page_view": ("title", "referrer", "time_origin"),
    "env": ("env",),
    "pointer_move": ("x", "y", "ptype"),
    "pointer_down": ("x", "y", "button", "ptype", "target", "trusted"),
    "pointer_up": ("x", "y", "button", "ptype", "target", "trusted"),
    "click": ("x", "y", "button", "target", "text", "href", "trusted"),
    "wheel": ("dx", "dy", "trusted"),
    "scroll": ("sx", "sy"),
    "key_down": ("key", "target", "repeat", "trusted"),
    "key_up": ("key", "target", "trusted"),
    "input": ("target", "value", "len", "itype", "trusted"),
    "change": ("target", "value", "trusted"),
    "paste": ("target", "len"),
    "copy": ("target", "len"),
    "focus": ("target",),
    "blur": ("target",),
    "submit": ("target",),
    "visibility": ("state",),
    "window_focus": (),
    "window_blur": (),
    "resize": ("w", "h"),
    "page_hide": (),
    "trap": ("trap", "action", "target"),
    "captcha": ("captcha", "ok", "ms", "len", "keys", "pasted", "seen", "scrolled"),
    "shop": ("action", "product", "size", "color", "qty", "value"),
}

# Events that the server writes. The browser cannot send them.
SERVER_EVENTS = {
    "session_start": ("ua", "again"),
    "canary": ("trap",),
    "order": ("order", "items", "total", "fields"),
    "contact": ("fields",),
}

# Fields that can hold an object or a list. All other fields hold a scalar.
NESTED_FIELDS = {"env", "items", "fields"}


class InvalidEvent(ValueError):
    pass


def _clean_value(name, value):
    if name in NESTED_FIELDS:
        if not isinstance(value, (dict, list)):
            raise InvalidEvent(f"field {name} must be an object or a list")
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:MAX_STRING]
    raise InvalidEvent(f"field {name} must be a scalar")


def clean_client_event(raw):
    """Return the event with only the known fields, or raise InvalidEvent."""
    if not isinstance(raw, dict):
        raise InvalidEvent("event must be an object")
    kind = raw.get("type")
    if kind not in CLIENT_EVENTS:
        raise InvalidEvent(f"unknown event type {kind!r}")
    if not isinstance(raw.get("t"), (int, float)) or not isinstance(raw.get("seq"), int):
        raise InvalidEvent("fields t and seq must be numbers")
    event = {}
    for name in COMMON_FIELDS + CLIENT_EVENTS[kind]:
        if name in raw:
            event[name] = _clean_value(name, raw[name])
    return event
