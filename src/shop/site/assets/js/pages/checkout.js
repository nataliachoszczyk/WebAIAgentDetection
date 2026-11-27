import { DELIVERY, cartLines, clearCart, esc, getDiscountCode, imageUrl, initLayout, money, totals } from "../common.js";

initLayout();
const root = document.getElementById("checkout");
const lines = await cartLines();

const COUNTRIES = { PL: "Poland", DE: "Germany", CZ: "Czechia", SK: "Slovakia", LT: "Lithuania" };
const REQUIRED = ["email", "name", "street", "postcode", "city", "country"];

if (!lines.length) {
  root.innerHTML = `<div class="card empty"><p>Your cart is empty.</p><a class="btn" href="/">Continue shopping</a></div>`;
} else {
  render();
}

function summary(delivery) {
  const t = totals(lines, delivery);
  return `
    <h2>Your order</h2>
    ${lines.map((l) => `<div class="mini-item"><img src="${imageUrl(l.product, l.color)}" alt="">
      <div><strong>${esc(l.product.name)}</strong><div class="muted">${esc(l.color)} · ${l.size} · ×${l.qty}</div></div>
      <span style="margin-left:auto">${money(l.total)}</span></div>`).join("")}
    <div class="summary-line"><span>Subtotal</span><span>${money(t.subtotal)}</span></div>
    ${t.discount ? `<div class="summary-line"><span>Discount (${esc(getDiscountCode())})</span><span>−${money(t.discount)}</span></div>` : ""}
    <div class="summary-line"><span>Delivery</span><span>${t.shipping ? money(t.shipping) : "Free"}</span></div>
    <div class="summary-line total"><span>Total</span><span>${money(t.total)}</span></div>`;
}

function render() {
  root.innerHTML = `
    <div class="steps"><span>Cart</span>›<span class="on">Delivery and payment</span>›<span>Confirmation</span></div>
    <div class="layout-2">
      <form class="card" id="checkout-form" novalidate>
        <h2>Contact</h2>
        <div class="field"><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="email">
          <span class="hint">We send the order confirmation to this address.</span></div>

        <h2 style="margin-top:22px">Delivery address</h2>
        <div class="field"><label for="name">Full name</label><input id="name" name="name" type="text" autocomplete="name"></div>
        <div class="field"><label for="street">Street and number</label><input id="street" name="street" type="text" autocomplete="street-address"></div>
        <div class="row">
          <div class="field"><label for="postcode">Postal code</label><input id="postcode" name="postcode" type="text" autocomplete="postal-code"></div>
          <div class="field"><label for="city">City</label><input id="city" name="city" type="text" autocomplete="address-level2"></div>
        </div>
        <div class="field"><label for="country">Country</label>
          <select id="country" name="country" autocomplete="country">
            <option value="">Select a country</option>
            ${Object.entries(COUNTRIES).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}
          </select></div>
        <div class="field"><label for="phone">Phone (optional)</label><input id="phone" name="phone" type="tel" autocomplete="tel"></div>

        <h2 style="margin-top:22px">Delivery</h2>
        ${Object.entries(DELIVERY).map(([k, d], i) => `
          <label class="radio-card"><input type="radio" name="delivery" value="${k}" ${i === 0 ? "checked" : ""}>
            <span class="grow">${d.label}${d.freeFrom ? `<br><span class="muted">Free from ${money(d.freeFrom)}</span>` : ""}</span>
            <span>${money(d.price)}</span></label>`).join("")}

        <h2 style="margin-top:22px">Payment</h2>
        <label class="radio-card"><input type="radio" name="payment" value="cod" checked>
          <span class="grow">Pay on delivery<br><span class="muted">Pay the courier in cash or by card.</span></span></label>
        <label class="radio-card"><input type="radio" name="payment" value="transfer">
          <span class="grow">Bank transfer<br><span class="muted">We send the bank details by email.</span></span></label>

        <div class="field" style="margin-top:14px"><label for="notes">Order notes (optional)</label>
          <textarea id="notes" name="notes" rows="3"></textarea></div>

        <div id="checkout-extra"></div>

        <label class="check" style="margin:14px 0"><input type="checkbox" name="terms" id="terms">
          I accept the <a href="/info.html#terms" target="_blank">terms of sale</a>.</label>
        <div id="form-error" role="alert"></div>
        <button class="btn block" type="submit" id="place-order">Place order</button>
      </form>
      <aside class="card" id="summary">${summary("standard")}</aside>
    </div>`;

  const form = document.getElementById("checkout-form");
  form.addEventListener("change", (e) => {
    if (e.target.name === "delivery") document.getElementById("summary").innerHTML = summary(e.target.value);
  });
  form.addEventListener("submit", submit);
}

function validate(data) {
  const errors = [];
  for (const name of REQUIRED) {
    const field = document.getElementById(name).closest(".field");
    const empty = !String(data[name] ?? "").trim();
    field.classList.toggle("error", empty);
    if (empty) errors.push(name);
  }
  if (data.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(data.email)) {
    document.getElementById("email").closest(".field").classList.add("error");
    errors.push("email");
  }
  return errors;
}

async function submit(e) {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form));
  const error = document.getElementById("form-error");
  const errors = validate(data);
  // Other parts of the page (for example a check before the order) can stop the order.
  const check = new CustomEvent("checkout:validate", { cancelable: true, detail: { errors } });
  document.dispatchEvent(check);
  if (errors.length || check.defaultPrevented) {
    error.innerHTML = `<p class="error-text">Correct the marked fields.</p>`;
    return;
  }
  if (!data.terms) {
    error.innerHTML = `<p class="error-text">Accept the terms of sale to place the order.</p>`;
    return;
  }
  error.innerHTML = "";
  const button = document.getElementById("place-order");
  button.disabled = true;
  button.textContent = "Placing the order…";
  const t = totals(lines, data.delivery);
  const items = lines.map((l) => ({ product: l.product.id, color: l.color, size: l.size, qty: l.qty, price: l.product.price }));
  const response = await fetch("/api/order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items, total: Math.round(t.total * 100) / 100, fields: { ...data, code: getDiscountCode() } }),
  });
  if (!response.ok) {
    button.disabled = false;
    button.textContent = "Place order";
    error.innerHTML = `<p class="error-text">The order failed. Try again.</p>`;
    return;
  }
  const { order } = await response.json();
  sessionStorage.setItem("ps_last_order", JSON.stringify({ order, email: data.email, total: t.total }));
  clearCart();
  location.href = "/order.html";
}
