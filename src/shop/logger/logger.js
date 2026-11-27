// Event logger of the test shop. The format is in docs/log_format.md.
// It only listens: it never stops or changes an event, so the page works the same with it.
(() => {
  "use strict";

  // Only study sessions are recorded. The session cookie is HttpOnly, so we look at the study flag.
  if (!document.cookie.split("; ").includes("wad_study=1")) {
    window.WAD = { log() {} };
    return;
  }

  const ENDPOINT = "/api/events";
  const FLUSH_MS = 2000;
  const MAX_QUEUE = 100;
  const THROTTLE = { pointer_move: 50, wheel: 100, scroll: 100, resize: 250 };
  const SELECTABLE = new Set(["checkbox", "radio"]);

  const page = Math.random().toString(36).slice(2, 10);
  let seq = 0;
  let queue = [];
  const lastTime = {};

  const path = () => location.pathname + location.search;
  const round = (n) => Math.round(n * 10) / 10;

  function emit(type, data = {}) {
    const t = performance.now();
    if (THROTTLE[type]) {
      if (t - (lastTime[type] ?? -Infinity) < THROTTLE[type]) return;
      lastTime[type] = t;
    }
    queue.push({ page, seq: seq++, t: round(t), ts: Math.round(performance.timeOrigin + t), type, path: path(), ...data });
    if (queue.length >= MAX_QUEUE) flush();
  }

  function flush(final = false) {
    if (!queue.length) return;
    const body = JSON.stringify({ events: queue });
    queue = [];
    // At the end of a page, only sendBeacon is sure to reach the server.
    if (final && navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }));
      return;
    }
    fetch(ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true })
      .catch(() => {});
  }

  // A short, stable description of an element. It never holds the text that a user typed.
  function describe(el) {
    if (!(el instanceof Element)) return el === document || el === window ? "document" : null;
    const trap = el.closest("[data-trap]");
    if (trap) return `trap:${trap.dataset.trap}`;
    const tag = el.tagName.toLowerCase();
    if (el.id) return `${tag}#${el.id}`;
    const name = el.getAttribute("name");
    if (name) return `${tag}[name=${name}]`;
    const cls = el.classList[0];
    return cls ? `${tag}.${cls}` : tag;
  }

  function isTextField(el) {
    return (el instanceof HTMLInputElement && !SELECTABLE.has(el.type)) || el instanceof HTMLTextAreaElement;
  }

  function label(el) {
    if (!(el instanceof Element) || isTextField(el)) return null;
    const clickable = el.closest("a, button, label, [role=button]") ?? el;
    const text = clickable.getAttribute("aria-label") || clickable.textContent || "";
    return text.replace(/\s+/g, " ").trim().slice(0, 60) || null;
  }

  function keyClass(key) {
    if (key.length === 1) return /\d/.test(key) ? "digit" : key === " " ? "space" : "char";
    return key;
  }

  function point(e) {
    return { x: Math.round(e.clientX), y: Math.round(e.clientY) };
  }

  function environment() {
    const env = {
      ua: navigator.userAgent,
      webdriver: navigator.webdriver ?? null,
      languages: (navigator.languages ?? []).join(","),
      platform: navigator.platform,
      screen: `${screen.width}x${screen.height}x${screen.colorDepth}`,
      window: `${innerWidth}x${innerHeight}`,
      outer: `${outerWidth}x${outerHeight}`,
      dpr: devicePixelRatio,
      tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
      cores: navigator.hardwareConcurrency ?? null,
      memory: navigator.deviceMemory ?? null,
      touch: navigator.maxTouchPoints ?? 0,
      plugins: navigator.plugins?.length ?? 0,
      chrome: typeof window.chrome === "object",
    };
    try {
      const gl = document.createElement("canvas").getContext("webgl");
      const info = gl?.getExtension("WEBGL_debug_renderer_info");
      if (info) {
        env.webgl_vendor = gl.getParameter(info.UNMASKED_VENDOR_WEBGL);
        env.webgl_renderer = gl.getParameter(info.UNMASKED_RENDERER_WEBGL);
      }
    } catch {
      // Some browsers block WebGL. The fingerprint is then without it.
    }
    return env;
  }

  const listen = (target, type, handler) =>
    target.addEventListener(type, (e) => {
      try {
        handler(e);
      } catch {
        // The logger must never break the page.
      }
    }, { capture: true, passive: true });

  listen(document, "pointermove", (e) => emit("pointer_move", { ...point(e), ptype: e.pointerType }));
  for (const type of ["pointerdown", "pointerup"]) {
    listen(document, type, (e) => emit(type === "pointerdown" ? "pointer_down" : "pointer_up", {
      ...point(e), button: e.button, ptype: e.pointerType, target: describe(e.target), trusted: e.isTrusted,
    }));
  }
  listen(document, "click", (e) => emit("click", {
    ...point(e), button: e.button, target: describe(e.target), text: label(e.target),
    href: e.target instanceof Element ? e.target.closest("a")?.getAttribute("href") ?? null : null,
    trusted: e.isTrusted,
  }));
  listen(document, "wheel", (e) => emit("wheel", { dx: Math.round(e.deltaX), dy: Math.round(e.deltaY), trusted: e.isTrusted }));
  listen(window, "scroll", () => emit("scroll", { sx: Math.round(scrollX), sy: Math.round(scrollY) }));
  listen(document, "keydown", (e) => emit("key_down", {
    key: keyClass(e.key ?? ""), target: describe(e.target), repeat: e.repeat, trusted: e.isTrusted,
  }));
  listen(document, "keyup", (e) => emit("key_up", { key: keyClass(e.key ?? ""), target: describe(e.target), trusted: e.isTrusted }));
  listen(document, "input", (e) => {
    if (!isTextField(e.target)) return;
    emit("input", { target: describe(e.target), len: e.target.value.length, itype: e.inputType ?? "", trusted: e.isTrusted });
  });
  listen(document, "change", (e) => {
    const el = e.target;
    if (isTextField(el)) return;
    const value = el instanceof HTMLInputElement && SELECTABLE.has(el.type) ? (el.checked ? el.value || "on" : "") : el.value;
    emit("change", { target: describe(el), value, trusted: e.isTrusted });
  });
  listen(document, "paste", (e) => emit("paste", { target: describe(e.target), len: e.clipboardData?.getData("text").length ?? 0 }));
  listen(document, "copy", () => emit("copy", { target: describe(document.activeElement), len: String(getSelection()).length }));
  listen(document, "focusin", (e) => emit("focus", { target: describe(e.target) }));
  listen(document, "focusout", (e) => emit("blur", { target: describe(e.target) }));
  listen(document, "submit", (e) => emit("submit", { target: describe(e.target) }));
  listen(document, "visibilitychange", () => {
    emit("visibility", { state: document.visibilityState });
    if (document.visibilityState === "hidden") flush(true);
  });
  listen(window, "focus", (e) => e.target === window && emit("window_focus"));
  listen(window, "blur", (e) => e.target === window && emit("window_blur"));
  listen(window, "resize", () => emit("resize", { w: innerWidth, h: innerHeight }));
  listen(window, "pagehide", () => {
    emit("page_hide");
    flush(true);
  });

  emit("page_view", { title: document.title, referrer: document.referrer, time_origin: Math.round(performance.timeOrigin) });
  // The fingerprint needs a WebGL context. Make it after the page load, so it does not delay the page.
  addEventListener("load", () => setTimeout(() => emit("env", { env: environment() }), 0), { once: true });
  setInterval(flush, FLUSH_MS);

  // Other parts of the page (shop, traps, reverse CAPTCHA) record their events here.
  window.WAD = { log: (type, data) => emit(type, data) };
})();
