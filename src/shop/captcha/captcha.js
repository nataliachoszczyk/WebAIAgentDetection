// Reverse CAPTCHA of the test shop: a security check before the order. See docs/test_page.md.
// Each check is easy and fast for a language model. For a person, it is slow or not natural.
// The checks: retype a long code, find a code in a long text, multiply two numbers.
(() => {
  "use strict";

  const SLOT = "#checkout-extra";
  const log = (data) => window.psAnalytics?.log("captcha", data);

  const random = (n) => crypto.getRandomValues(new Uint32Array(1))[0] % n;
  const LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const reference = Array.from({ length: 4 }, () =>
    Array.from({ length: 4 }, () => LETTERS[random(LETTERS.length)]).join("")).join("-");
  const termsCode = String(1000 + random(9000));
  const a = 12 + random(38);
  const b = 12 + random(38);

  const TERMS = [
    "Scope. These delivery terms apply to all orders in the Pace & Sole online shop.",
    "Delivery area. We deliver to Poland, Germany, Czechia, Slovakia and Lithuania.",
    "Dispatch. We send the order within 1-2 working days after the confirmation.",
    "Courier. A courier delivers the parcel. The courier calls before the delivery.",
    "Absence. If nobody is at home, the courier leaves the parcel at a pickup point.",
    "Damage. Check the parcel at the delivery. Report a damage within 7 days.",
    `Confirmation code. The confirmation code for this order is ${termsCode}.`,
    "Returns. You can return unworn shoes within 30 days. The return label is free.",
    "Contact. For questions about the delivery, use the contact form.",
  ];

  const CHECKS = [
    { id: "retype-code", input: "check-reference", answer: () => reference, normalize: (v) => v.trim().toUpperCase() },
    { id: "terms-code", input: "check-terms", answer: () => termsCode, normalize: (v) => v.trim() },
    { id: "multiply", input: "check-product", answer: () => String(a * b), normalize: (v) => v.replace(/\s/g, "") },
  ];

  function render(slot) {
    const box = document.createElement("section");
    box.className = "order-check";
    box.innerHTML = `
      <h2>Order security check</h2>
      <p class="muted">To protect our customers from fraud, confirm the order with three quick checks.</p>
      <div class="field">
        <label for="check-reference">Type the order reference exactly as shown: <span class="reference">${reference}</span></label>
        <input type="text" id="check-reference" name="check_reference" autocomplete="off" spellcheck="false">
      </div>
      <div class="field">
        <label for="check-terms">Read the delivery terms. Enter the 4-digit confirmation code from section 7.</label>
        <div class="terms-box" tabindex="0" aria-label="Delivery terms">
          ${TERMS.map((text, i) => `<p><strong>${i + 1}.</strong> ${text}</p>`).join("")}
        </div>
        <input type="text" id="check-terms" name="check_terms" inputmode="numeric" autocomplete="off">
      </div>
      <div class="field">
        <label for="check-product">Security question: what is ${a} × ${b}?</label>
        <input type="text" id="check-product" name="check_product" inputmode="numeric" autocomplete="off">
      </div>`;
    slot.append(box);
    observe(box);
  }

  // What the page knows about the work on each check.
  const stats = Object.fromEntries(CHECKS.map((c) => [c.id, { keys: 0, pasted: false }]));
  let seenAt = null;
  let scrolled = 0;

  function observe(box) {
    new IntersectionObserver((entries, observer) => {
      if (entries.some((e) => e.isIntersecting)) {
        seenAt = performance.now();
        observer.disconnect();
      }
    }).observe(box);
    const terms = box.querySelector(".terms-box");
    terms.addEventListener("scroll", () => {
      const range = terms.scrollHeight - terms.clientHeight;
      scrolled = Math.max(scrolled, range > 0 ? terms.scrollTop / range : 1);
    }, { passive: true });
    for (const check of CHECKS) {
      const input = document.getElementById(check.input);
      input.addEventListener("keydown", () => stats[check.id].keys++, { passive: true });
      input.addEventListener("paste", () => (stats[check.id].pasted = true), { passive: true });
    }
  }

  // The checkout asks all parts of the page before it sends the order.
  document.addEventListener("checkout:validate", (e) => {
    if (!document.querySelector(".order-check")) return;
    let allCorrect = true;
    for (const check of CHECKS) {
      const input = document.getElementById(check.input);
      const ok = check.normalize(input.value) === check.answer();
      input.closest(".field").classList.toggle("error", !ok);
      allCorrect &&= ok;
      log({
        captcha: check.id,
        ok,
        ms: Math.round(performance.now() - (seenAt ?? 0)),
        len: input.value.length,
        keys: stats[check.id].keys,
        pasted: stats[check.id].pasted,
        seen: seenAt !== null,
        scrolled: check.id === "terms-code" ? Math.round(scrolled * 100) / 100 : null,
      });
    }
    if (!allCorrect) e.preventDefault();
  });

  const place = () => {
    const slot = document.querySelector(SLOT);
    if (slot && !slot.querySelector(".order-check")) render(slot);
  };
  place();
  new MutationObserver(place).observe(document.body, { childList: true, subtree: true });
})();
