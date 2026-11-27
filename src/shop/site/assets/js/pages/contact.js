import { initLayout } from "../common.js";

initLayout();
const form = document.getElementById("contact-form");
const status = document.getElementById("contact-status");
const REQUIRED = ["name", "email", "topic", "message"];

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  let ok = true;
  for (const name of REQUIRED) {
    const empty = !String(data[name] ?? "").trim();
    form.elements[name].closest(".field").classList.toggle("error", empty);
    if (empty) ok = false;
  }
  if (!ok) {
    status.innerHTML = `<p class="error-text">Fill in all required fields.</p>`;
    return;
  }
  const response = await fetch("/api/contact", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields: data }),
  });
  status.innerHTML = response.ok
    ? `<div class="notice ok">Thank you. We received your message and answer within one working day.</div>`
    : `<p class="error-text">The message was not sent. Try again.</p>`;
  if (response.ok) form.reset();
});
