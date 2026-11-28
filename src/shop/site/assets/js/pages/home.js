import { CATEGORIES, esc, imageUrl, initLayout, loadCatalog, money, stars, track } from "../common.js";

const params = new URLSearchParams(location.search);
const state = {
  q: params.get("q") ?? "",
  categories: new Set(params.getAll("category")),
  size: params.get("size") ?? "",
  waterproof: params.get("waterproof") === "1",
  maxPrice: params.get("max") ?? "",
  sort: params.get("sort") ?? "featured",
};

initLayout(state.categories.size === 1 ? [...state.categories][0] : null);
const catalog = await loadCatalog();

function card(p) {
  const badge = p.badge ? `<span class="badge ${p.badge.toLowerCase()}">${esc(p.badge)}</span>` : "";
  const old = p.old_price ? `<span class="old">${money(p.old_price)}</span>` : "";
  const dots = p.colors.map((c) => `<span class="swatch-dot" style="background:${c.upper}" title="${esc(c.name)}"></span>`).join("");
  return `
    <a class="product-card" href="/product.html?id=${p.id}">
      <div class="media">${badge}<img src="${imageUrl(p)}" alt="${esc(p.name)}"></div>
      <div class="body">
        <span class="muted">${CATEGORIES[p.category]}</span>
        <span class="name">${esc(p.name)}</span>
        <span class="rating">${stars(p.rating)} <span>${p.rating} (${p.reviews})</span></span>
        <span class="price">${money(p.price)}${old}</span>
        <div class="swatches">${dots}</div>
      </div>
    </a>`;
}

function matches(p) {
  if (state.q && !`${p.name} ${p.short} ${p.category}`.toLowerCase().includes(state.q.toLowerCase())) return false;
  if (state.categories.size && !state.categories.has(p.category)) return false;
  if (state.size && !(p.sizes.includes(+state.size) && !p.sold_out.includes(+state.size))) return false;
  if (state.waterproof && !p.waterproof) return false;
  if (state.maxPrice && p.price > +state.maxPrice) return false;
  return true;
}

const SORTS = {
  featured: () => 0,
  "price-asc": (a, b) => a.price - b.price,
  "price-desc": (a, b) => b.price - a.price,
  rating: (a, b) => b.rating - a.rating,
};

function syncUrl() {
  const next = new URLSearchParams();
  if (state.q) next.set("q", state.q);
  state.categories.forEach((c) => next.append("category", c));
  if (state.size) next.set("size", state.size);
  if (state.waterproof) next.set("waterproof", "1");
  if (state.maxPrice) next.set("max", state.maxPrice);
  if (state.sort !== "featured") next.set("sort", state.sort);
  const query = next.toString();
  history.replaceState(null, "", `/${query ? `?${query}` : ""}#catalog`);
}

function render() {
  const list = catalog.filter(matches).sort(SORTS[state.sort]);
  document.getElementById("product-grid").innerHTML = list.length
    ? list.map(card).join("")
    : `<div class="empty">No shoes match the filters. <button class="link-btn" type="button" data-reset>Clear the filters</button></div>`;
  document.querySelector("[data-reset]")?.addEventListener("click", reset);
  const title = state.q ? `Results for “${esc(state.q)}”`
    : state.categories.size === 1 ? CATEGORIES[[...state.categories][0]] : "All shoes";
  document.getElementById("catalog-title").innerHTML = title;
  document.getElementById("catalog-count").textContent = `${list.length} ${list.length === 1 ? "product" : "products"}`;
  syncUrl();
}

function reset() {
  Object.assign(state, { q: "", size: "", waterproof: false, maxPrice: "", sort: "featured" });
  state.categories.clear();
  fillControls();
  render();
}

function fillControls() {
  document.querySelectorAll("#filter-category input").forEach((box) => (box.checked = state.categories.has(box.value)));
  document.getElementById("filter-size").value = state.size;
  document.getElementById("filter-waterproof").checked = state.waterproof;
  document.getElementById("filter-price").value = state.maxPrice;
  document.getElementById("sort").value = state.sort;
}

document.getElementById("filter-category").innerHTML = Object.entries(CATEGORIES)
  .map(([id, label]) => `<label class="check"><input type="checkbox" value="${id}"> ${label}</label>`).join("");
const sizes = [...new Set(catalog.flatMap((p) => p.sizes))].sort((a, b) => a - b);
document.getElementById("filter-size").insertAdjacentHTML("beforeend", sizes.map((s) => `<option value="${s}">${s}</option>`).join(""));
fillControls();

document.getElementById("filter-category").addEventListener("change", (e) => {
  e.target.checked ? state.categories.add(e.target.value) : state.categories.delete(e.target.value);
  track("filter", { value: `category=${[...state.categories].join(",")}` });
  render();
});
document.getElementById("filter-size").addEventListener("change", (e) => {
  state.size = e.target.value;
  track("filter", { value: `size=${state.size}` });
  render();
});
document.getElementById("filter-waterproof").addEventListener("change", (e) => {
  state.waterproof = e.target.checked;
  track("filter", { value: `waterproof=${state.waterproof}` });
  render();
});
document.getElementById("filter-price").addEventListener("change", (e) => {
  state.maxPrice = e.target.value;
  track("filter", { value: `max=${state.maxPrice}` });
  render();
});
document.getElementById("sort").addEventListener("change", (e) => {
  state.sort = e.target.value;
  track("sort", { value: state.sort });
  render();
});
document.getElementById("filter-reset").addEventListener("click", reset);

if (state.q) track("search", { value: state.q });
render();
