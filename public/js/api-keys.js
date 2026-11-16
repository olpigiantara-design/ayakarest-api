let newKeyFull = null;

async function fetchKeys() {
  const res = await fetch("/api/keys", { credentials: "include" });
  const data = await res.json();
  if (!data.success) throw new Error(data.message);
  renderKeys(data.data);
}

function renderKeys(keys) {
  const tbody = document.querySelector("#keys-table tbody");
  tbody.innerHTML = "";
  if (!keys.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty">Belum ada API Key. Generate yang pertama.</td></tr>`;
    return;
  }
  keys.forEach((k) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${k.name}</strong><br><small>${k.description || ""}</small></td>
      <td><code>${k.key_prefix}••••••••</code></td>
      <td><span class="badge badge-${k.status}">${k.status}</span></td>
      <td>${k.permissions.join(", ")}</td>
      <td>${k.last_used_at ? new Date(k.last_used_at).toLocaleString("id-ID") : "—"}</td>
      <td>
        <button class="btn btn-sm btn-outline" data-revoke="${k.id}">Revoke</button>
      </td>`;
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll("[data-revoke]").forEach((btn) => {
    btn.addEventListener("click", () => revokeKey(btn.dataset.revoke));
  });
}

async function revokeKey(id) {
  if (!confirm("Cabut API Key ini? Tindakan ini tidak dapat dibatalkan.")) return;
  const csrf = getCookie("ayaka_csrf");
  const res = await fetch(`/api/keys/${id}`, {
    method: "DELETE",
    credentials: "include",
    headers: { "X-CSRF-Token": csrf },
  });
  const data = await res.json();
  if (data.success) {
    showToast(data.message, "success");
    fetchKeys();
  } else {
    showToast(data.message, "error");
  }
}

// Generate form
const genForm = document.getElementById("generate-key-form");
if (genForm) {
  genForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(genForm);
    const csrf = getCookie("ayaka_csrf");
    const res = await fetch("/api/keys/generate", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({
        name: f.get("name"),
        description: f.get("description"),
      }),
    });
    const data = await res.json();
    if (!data.success) return showToast(data.message, "error");
    newKeyFull = data.data.full_key;
    document.getElementById("new-key-modal").classList.add("open");
    document.getElementById("new-key-value").textContent = newKeyFull;
    fetchKeys();
  });
}

// Copy full key
document.getElementById("copy-new-key")?.addEventListener("click", () => {
  if (newKeyFull) navigator.clipboard.writeText(newKeyFull);
  showToast("API Key disalin. Simpan di tempat aman.", "success");
});

function getCookie(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="))
    ?.split("=")[1];
}

fetchKeys().catch((e) => showToast(e.message, "error"));