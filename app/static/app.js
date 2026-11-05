// Shared helpers for every page: API calls, escaping, labels, form errors.

async function api(method, url, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  let data = {};
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) {
    if (res.status === 401 && !url.startsWith("/api/auth/")) {
      window.location = "/login";
    }
    const err = new Error(data.error || `Something went wrong (${res.status}).`);
    err.fields = data.fields || {};
    throw err;
  }
  return data;
}

// Always escape user text before putting it in HTML (prevents XSS).
function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

const LABELS = {
  status: { open: "Open", in_progress: "In progress", resolved: "Resolved", closed: "Closed" },
  category: { account: "Account", wifi: "Wi-Fi", software: "Software", hardware: "Hardware", other: "Other" },
  priority: { low: "Low", medium: "Medium", high: "High" },
};

function badge(kind, value) {
  return `<span class="badge ${kind}-${esc(value)}">${esc(LABELS[kind][value] || value)}</span>`;
}

function when(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function ago(iso) {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function clearErrors(form) {
  form.querySelectorAll(".field-error").forEach((n) => (n.textContent = ""));
  form.querySelectorAll(".invalid").forEach((n) => n.classList.remove("invalid"));
  const box = form.querySelector(".form-error");
  if (box) box.textContent = "";
}

function showErrors(form, err) {
  const box = form.querySelector(".form-error");
  if (box) box.textContent = err.message;
  for (const [name, msg] of Object.entries(err.fields || {})) {
    const input = form.elements[name];
    if (input) input.classList.add("invalid");
    const slot = form.querySelector(`[data-error-for="${name}"]`);
    if (slot) slot.textContent = msg;
  }
}

// Wire a form: clears errors, disables the button while submitting, shows errors on failure.
function handleSubmit(form, onSubmit) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors(form);
    const button = form.querySelector("button[type=submit]");
    if (button) button.disabled = true;
    try {
      await onSubmit(formData(form));
    } catch (err) {
      showErrors(form, err);
    } finally {
      if (button) button.disabled = false;
    }
  });
}

async function logout() {
  await api("POST", "/api/auth/logout");
  window.location = "/login";
}
