// Shared parts of all shop pages: catalog, cart, layout and the shopping list with the tasks.

export const DELIVERY = {
  standard: { label: "Standard delivery (2-4 days)", price: 4.9, freeFrom: 150 },
  express: { label: "Express delivery (next day)", price: 12.9 },
};
export const DISCOUNT_CODES = { WELCOME10: 0.1 };
const CART_KEY = "ps_cart";
const CODE_KEY = "ps_code";

export const CATEGORIES = {
  running: "Running",
  hiking: "Hiking",
  casual: "Casual",
  formal: "Formal",
};

// The public shop runs through a tunnel. A short network fault must not leave the page empty.
export async function fetchJson(url, tries = 3) {
  for (let i = 1; ; i++) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      if (i >= tries) throw error;
      await new Promise((resolve) => setTimeout(resolve, 500 * i));
    }
  }
}

let catalogPromise;
export function loadCatalog() {
  catalogPromise ??= fetchJson("/assets/data/products.json").catch((error) => {
    catalogPromise = null;
    throw error;
  });
  return catalogPromise;
}

export async function findProduct(id) {
  return (await loadCatalog()).find((p) => p.id === id);
}

export function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

export function money(value) {
  return `€${value.toFixed(2)}`;
}

export function slug(text) {
  return text.toLowerCase().replace(/\s+/g, "-");
}

export function imageUrl(product, colorName) {
  const color = colorName ?? product.colors[0].name;
  return `/assets/img/${product.id}-${slug(color)}.svg`;
}

export function stars(rating) {
  const full = Math.round(rating);
  return "★".repeat(full) + "☆".repeat(5 - full);
}

// Shop events go to the event logger if the page has one.
export function track(action, data = {}) {
  window.psAnalytics?.log("shop", { action, ...data });
}

// Cart ------------------------------------------------------------------

export function getCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) ?? [];
  } catch {
    return [];
  }
}

function saveCart(items) {
  localStorage.setItem(CART_KEY, JSON.stringify(items));
  updateCartCount();
}

export function addToCart(item) {
  const items = getCart();
  const same = items.find((i) => i.product === item.product && i.color === item.color && i.size === item.size);
  if (same) same.qty += item.qty;
  else items.push(item);
  saveCart(items);
}

export function setQuantity(index, qty) {
  const items = getCart();
  if (!items[index]) return;
  items[index].qty = qty;
  saveCart(items.filter((i) => i.qty > 0));
}

export function removeFromCart(index) {
  const items = getCart();
  items.splice(index, 1);
  saveCart(items);
}

export function clearCart() {
  saveCart([]);
  sessionStorage.removeItem(CODE_KEY);
}

export function getDiscountCode() {
  return sessionStorage.getItem(CODE_KEY);
}

export function setDiscountCode(code) {
  if (code) sessionStorage.setItem(CODE_KEY, code);
  else sessionStorage.removeItem(CODE_KEY);
}

export async function cartLines() {
  const catalog = await loadCatalog();
  return getCart().map((item) => {
    const product = catalog.find((p) => p.id === item.product);
    return { ...item, product, total: product.price * item.qty };
  });
}

export function totals(lines, delivery = "standard") {
  const subtotal = lines.reduce((sum, l) => sum + l.total, 0);
  const code = getDiscountCode();
  const discount = code ? subtotal * DISCOUNT_CODES[code] : 0;
  const rule = DELIVERY[delivery];
  const shipping = lines.length === 0 || (rule.freeFrom && subtotal - discount >= rule.freeFrom) ? 0 : rule.price;
  return { subtotal, discount, shipping, total: subtotal - discount + shipping };
}

function updateCartCount() {
  const count = getCart().reduce((sum, i) => sum + i.qty, 0);
  const badge = document.querySelector(".cart-count");
  if (badge) badge.textContent = count;
}

// Layout ----------------------------------------------------------------

function header(active) {
  const nav = Object.entries(CATEGORIES)
    .map(([id, label]) => `<a href="/?category=${id}#catalog" class="${active === id ? "active" : ""}">${label}</a>`)
    .join("");
  return `
    <div class="announce">Free standard delivery from €150 · 30-day returns · Use code WELCOME10 for 10% off</div>
    <div class="site-header"><div class="inner">
      <a class="logo" href="/"><span class="logo-mark">P&amp;S</span>Pace &amp; Sole</a>
      <nav class="main-nav" aria-label="Categories">${nav}</nav>
      <form class="search" action="/" role="search">
        <input type="search" name="q" placeholder="Search shoes" aria-label="Search shoes">
        <button type="submit" aria-label="Search">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>
        </button>
      </form>
      <a class="cart-link" href="/cart.html">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 7h12l-1 13H7L6 7z"/><path d="M9 7a3 3 0 0 1 6 0"/></svg>
        Cart <span class="cart-count">0</span>
      </a>
    </div></div>`;
}

function footer() {
  return `
    <div class="inner">
      <div>
        <a class="logo" href="/" style="color:#fff"><span class="logo-mark">P&amp;S</span>Pace &amp; Sole</a>
        <p>Shoes for running, hiking and every day. Shipped from our warehouse in Chełm.</p>
      </div>
      <div><h4>Shop</h4>${Object.entries(CATEGORIES).map(([id, l]) => `<a href="/?category=${id}#catalog">${l}</a>`).join("")}</div>
      <div><h4>Help</h4>
        <a href="/info.html#delivery">Delivery</a>
        <a href="/info.html#returns">Returns</a>
        <a href="/info.html#size-guide">Size guide</a>
        <a href="/contact.html">Contact us</a>
      </div>
      <div><h4>Company</h4>
        <a href="/info.html#about">About us</a>
        <a href="/info.html#terms">Terms of sale</a>
        <a href="/info.html#privacy">Privacy</a>
      </div>
    </div>
    <div class="legal">© 2026 Pace &amp; Sole. All prices include VAT.</div>`;
}

async function taskList() {
  if (!document.cookie.split("; ").includes("ps_visit=1")) return;
  let data;
  try {
    data = await fetchJson("/api/tasks");
  } catch {
    return;
  }
  const panel = document.createElement("aside");
  panel.className = "shopping-list";
  panel.id = "shopping-list";
  panel.setAttribute("aria-label", "Your shopping list");
  if (sessionStorage.getItem("ps_list") === "closed") panel.classList.add("collapsed");
  panel.innerHTML = `
    <header><span>Your shopping list</span><button type="button" aria-expanded="true">Hide</button></header>
    <ol>${data.tasks.map((t) => `<li><strong>${esc(t.title)}.</strong> ${esc(t.text)}</li>`).join("")}</ol>`;
  const toggle = panel.querySelector("button");
  const sync = () => {
    const closed = panel.classList.contains("collapsed");
    toggle.textContent = closed ? "Show" : "Hide";
    toggle.setAttribute("aria-expanded", String(!closed));
    document.body.classList.toggle("list-open", !closed);
  };
  toggle.addEventListener("click", () => {
    panel.classList.toggle("collapsed");
    sessionStorage.setItem("ps_list", panel.classList.contains("collapsed") ? "closed" : "open");
    sync();
  });
  sync();
  document.body.append(panel);
}

export function initLayout(active) {
  const top = document.createElement("header");
  top.innerHTML = header(active);
  document.body.prepend(top);
  const bottom = document.createElement("footer");
  bottom.className = "site-footer";
  bottom.innerHTML = footer();
  document.body.append(bottom);
  const query = new URLSearchParams(location.search).get("q");
  if (query) top.querySelector(".search input").value = query;
  updateCartCount();
  taskList();
}
