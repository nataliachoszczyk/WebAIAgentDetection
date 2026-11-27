import { esc, initLayout, money } from "../common.js";

initLayout();
const last = JSON.parse(sessionStorage.getItem("ps_last_order") ?? "null");
document.getElementById("confirm").innerHTML = last
  ? `<div class="tick">✓</div>
     <h1>Thank you for your order</h1>
     <p>Your order number:</p>
     <div class="order-number" id="order-number">${esc(last.order)}</div>
     <p class="muted">We sent a confirmation to ${esc(last.email)}. Total: ${money(last.total)}.</p>
     <p><a class="btn" href="/">Continue shopping</a> <a class="btn secondary" href="/contact.html">Contact us</a></p>`
  : `<h1>No recent order</h1><p><a class="btn" href="/">Go to the shop</a></p>`;
