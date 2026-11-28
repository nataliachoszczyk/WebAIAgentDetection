import { CATEGORIES, addToCart, esc, findProduct, imageUrl, initLayout, money, stars, track } from "../common.js";

const REVIEWS = [
  { name: "Marta K.", stars: 5, text: "True to size and comfortable from the first day." },
  { name: "Tomasz W.", stars: 4, text: "Good grip. The laces are a bit short." },
  { name: "Ola P.", stars: 5, text: "Fast delivery, the shoes look like the photos." },
];

const id = new URLSearchParams(location.search).get("id");
const product = await findProduct(id);
initLayout(product?.category);

const root = document.getElementById("product");
if (!product) {
  root.innerHTML = `<div class="empty"><h1>Product not found</h1><a class="btn" href="/">Back to the shop</a></div>`;
} else {
  render(product);
}

function render(p) {
  document.title = `${p.name} | Pace & Sole`;
  document.getElementById("breadcrumbs").innerHTML =
    `<a href="/">Home</a> / <a href="/?category=${p.category}#catalog">${CATEGORIES[p.category]}</a> / ${esc(p.name)}`;
  const state = { color: p.colors[0].name, size: null };

  root.innerHTML = `
    <div class="product">
      <div class="gallery"><img id="product-image" src="${imageUrl(p)}" alt="${esc(p.name)} in ${esc(state.color)}"></div>
      <div class="info">
        <span class="muted">${CATEGORIES[p.category]}${p.waterproof ? " · Waterproof" : ""}</span>
        <h1>${esc(p.name)}</h1>
        <span class="rating">${stars(p.rating)} <span>${p.rating} · ${p.reviews} reviews</span></span>
        <div class="price">${money(p.price)}${p.old_price ? `<span class="old">${money(p.old_price)}</span>` : ""}</div>
        <p>${esc(p.description)}</p>

        <div class="option-label"><span>Color: <span id="color-name">${esc(state.color)}</span></span></div>
        <div class="colors" role="group" aria-label="Color">
          ${p.colors.map((c) => `
            <button type="button" class="color-option" data-color="${esc(c.name)}" aria-pressed="${c.name === state.color}">
              <span class="swatch-dot" style="background:${c.upper}"></span>${esc(c.name)}
            </button>`).join("")}
        </div>

        <div class="option-label"><span>Size (EU)</span><a href="/info.html#size-guide" class="muted">Size guide</a></div>
        <div class="sizes" role="group" aria-label="Size">
          ${p.sizes.map((s) => {
            const out = p.sold_out.includes(s);
            return `<button type="button" class="size-option" data-size="${s}" aria-pressed="false" ${out ? "disabled" : ""}
              aria-label="Size ${s}${out ? ", sold out" : ""}">${s}</button>`;
          }).join("")}
        </div>

        <div class="buy-row">
          <div class="qty"><label for="qty">Qty</label><input id="qty" type="number" min="1" max="5" value="1"></div>
          <button type="button" class="btn" id="add-to-cart">Add to cart</button>
        </div>
        <div id="buy-notice" role="status"></div>

        <div class="perks">
          <span>✓ Free standard delivery from €150</span>
          <span>✓ 30-day returns</span>
          <span>✓ Shipped in 1-2 working days</span>
        </div>
        <details><summary>Details</summary><ul>${p.features.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></details>
        <details><summary>Delivery and returns</summary>
          <p>Standard delivery costs €4.90 and takes 2-4 working days. You can return unworn shoes within 30 days. See the <a href="/info.html#returns">returns policy</a>.</p>
        </details>
      </div>
    </div>
    <section class="reviews">
      <h2>Customer reviews</h2>
      ${REVIEWS.map((r) => `<div class="review"><span class="rating">${stars(r.stars)}</span> <strong>${r.name}</strong><p>${r.text}</p></div>`).join("")}
    </section>`;

  const notice = document.getElementById("buy-notice");
  root.querySelectorAll(".color-option").forEach((btn) =>
    btn.addEventListener("click", () => {
      state.color = btn.dataset.color;
      root.querySelectorAll(".color-option").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      document.getElementById("color-name").textContent = state.color;
      const img = document.getElementById("product-image");
      img.src = imageUrl(p, state.color);
      img.alt = `${p.name} in ${state.color}`;
    }));
  root.querySelectorAll(".size-option").forEach((btn) =>
    btn.addEventListener("click", () => {
      state.size = Number(btn.dataset.size);
      root.querySelectorAll(".size-option").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      notice.innerHTML = "";
    }));
  document.getElementById("add-to-cart").addEventListener("click", () => {
    if (!state.size) {
      notice.innerHTML = `<div class="notice warn">Select a size first.</div>`;
      return;
    }
    const qty = Math.min(5, Math.max(1, Number(document.getElementById("qty").value) || 1));
    addToCart({ product: p.id, color: state.color, size: state.size, qty });
    track("add_to_cart", { product: p.id, size: state.size, color: state.color, qty });
    notice.innerHTML = `<div class="notice ok">Added to the cart: ${esc(p.name)}, ${esc(state.color)}, size ${state.size}.
      <a href="/cart.html">Go to the cart</a></div>`;
  });
  track("view_item", { product: p.id });
}
