import {
  DISCOUNT_CODES, cartLines, esc, getDiscountCode, imageUrl, initLayout, money,
  removeFromCart, setDiscountCode, setQuantity, totals, track,
} from "../common.js";

initLayout();
const root = document.getElementById("cart");
let codeMessage = "";

async function render() {
  const lines = await cartLines();
  if (!lines.length) {
    root.innerHTML = `<div class="card empty"><p>Your cart is empty.</p><a class="btn" href="/">Continue shopping</a></div>`;
    return;
  }
  const t = totals(lines);
  const code = getDiscountCode();
  root.innerHTML = `
    <div class="layout-2">
      <div class="card">
        ${lines.map((l, i) => `
          <div class="cart-item">
            <a href="/product.html?id=${l.product.id}"><img src="${imageUrl(l.product, l.color)}" alt="${esc(l.product.name)}"></a>
            <div>
              <strong>${esc(l.product.name)}</strong>
              <div class="muted">Color: ${esc(l.color)} · Size: ${l.size}</div>
              <div class="qty" style="margin-top:8px">
                <label for="qty-${i}" class="muted">Qty</label>
                <input id="qty-${i}" type="number" min="0" max="5" value="${l.qty}" data-index="${i}">
                <button type="button" class="link-btn" data-remove="${i}">Remove</button>
              </div>
            </div>
            <strong>${money(l.total)}</strong>
          </div>`).join("")}
      </div>
      <aside class="card">
        <h2>Order summary</h2>
        <div class="summary-line"><span>Subtotal</span><span>${money(t.subtotal)}</span></div>
        ${t.discount ? `<div class="summary-line"><span>Discount (${esc(code)})</span><span>−${money(t.discount)}</span></div>` : ""}
        <div class="summary-line"><span>Standard delivery</span><span>${t.shipping ? money(t.shipping) : "Free"}</span></div>
        <form class="code-row" id="code-form">
          <input type="text" name="code" placeholder="Discount code" aria-label="Discount code" value="${esc(code ?? "")}">
          <button class="btn secondary" type="submit">Apply</button>
        </form>
        <div role="status">${codeMessage}</div>
        <div class="summary-line total"><span>Total</span><span>${money(t.total)}</span></div>
        <a class="btn block" href="/checkout.html" id="checkout-link" style="margin-top:14px">Go to checkout</a>
        <p class="muted" style="font-size:.85rem;margin-top:12px">Taxes included. Delivery options at the checkout.</p>
      </aside>
    </div>`;

  root.querySelectorAll("input[data-index]").forEach((input) =>
    input.addEventListener("change", () => {
      setQuantity(Number(input.dataset.index), Math.max(0, Math.min(5, Number(input.value) || 0)));
      render();
    }));
  root.querySelectorAll("[data-remove]").forEach((btn) =>
    btn.addEventListener("click", () => {
      const line = lines[Number(btn.dataset.remove)];
      removeFromCart(Number(btn.dataset.remove));
      track("remove_from_cart", { product: line.product.id, size: line.size, color: line.color });
      render();
    }));
  document.getElementById("code-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const value = new FormData(e.target).get("code").trim().toUpperCase();
    track("apply_code", { value });
    if (!value) {
      setDiscountCode(null);
      codeMessage = "";
    } else if (DISCOUNT_CODES[value]) {
      setDiscountCode(value);
      codeMessage = `<div class="notice ok">Code ${esc(value)} applied.</div>`;
    } else {
      codeMessage = `<div class="notice warn">The code ${esc(value)} is not valid.</div>`;
    }
    render();
  });
  document.getElementById("checkout-link").addEventListener("click", () => track("begin_checkout"));
}

render();
