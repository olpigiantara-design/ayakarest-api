document.addEventListener("DOMContentLoaded", async () => {
  // 1. Cek role Admin
  try {
    const res = await fetch("/api/auth/me", { credentials: "include" });
    if (!res.ok) throw new Error("Unauthorized");
    const data = await res.json();
    
    if (data.data.role !== "admin") {
      window.location.href = "/dashboard";
      return;
    }
  } catch (err) {
    window.location.href = "/login";
    return;
  }

  // 2. Load Overview Stats
  loadAdminStats();
  
  // 3. Load Users
  loadAdminUsers();
  
  // 4. Load Maintenance Status
  checkMaintenance();
});

async function loadAdminStats() {
  try {
    const res = await fetch("/api/admin/overview", { credentials: "include" });
    const data = await res.json();
    if (data.success) {
      document.getElementById("adm-total-users").textContent = data.data.total_users;
      document.getElementById("adm-total-keys").textContent = data.data.total_keys;
      document.getElementById("adm-total-requests").textContent = data.data.total_requests;
    }
  } catch (err) {
    console.error("Failed to load stats", err);
  }
}

async function loadAdminUsers() {
  const tbody = document.getElementById("admin-users-table");
  try {
    const res = await fetch("/api/admin/users", { credentials: "include" });
    const data = await res.json();
    
    if (data.success) {
      tbody.innerHTML = "";
      data.data.forEach(user => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${user.username}</strong><br><small>${user.full_name}</small></td>
          <td>${user.email}</td>
          <td><span class="badge badge-${user.role === 'admin' ? 'admin' : 'active'}">${user.role}</span></td>
          <td><span class="badge ${user.is_active ? 'badge-active' : 'badge-revoked'}">${user.is_active ? 'Active' : 'Suspended'}</span></td>
          <td>
            <button class="btn btn-outline btn-sm" onclick="toggleUserStatus('${user.id}', ${user.is_active})">
              ${user.is_active ? 'Suspend' : 'Activate'}
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;">Failed to load users</td></tr>`;
  }
}

async function toggleUserStatus(userId, isCurrentlyActive) {
  if (!confirm(`Yakin ingin ${isCurrentlyActive ? 'menangguhkan' : 'mengaktifkan'} user ini?`)) return;
  
  const action = isCurrentlyActive ? 'suspend' : 'activate';
  try {
    const res = await fetch(`/api/admin/users/${userId}/${action}`, {
      method: "POST",
      credentials: "include"
    });
    const data = await res.json();
    if (data.success) {
      alert(data.message);
      loadAdminUsers(); // Reload table
    } else {
      alert(data.message);
    }
  } catch (err) {
    alert("Terjadi kesalahan sistem.");
  }
}

// Maintenance Mode
async function checkMaintenance() {
  try {
    const res = await fetch("/api/admin/maintenance", { credentials: "include" });
    const data = await res.json();
    if (data.success) {
      updateMaintenanceBtn(data.data.enabled);
    }
  } catch (err) {}
}

document.getElementById("maintenance-toggle")?.addEventListener("click", async () => {
  const btn = document.getElementById("maintenance-toggle");
  const isCurrentlyEnabled = btn.textContent === "ENABLED";
  
  try {
    const res = await fetch("/api/admin/maintenance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ 
        enabled: !isCurrentlyEnabled,
        message: "AYAKA API sedang dalam pemeliharaan."
      })
    });
    const data = await res.json();
    if (data.success) {
      updateMaintenanceBtn(!isCurrentlyEnabled);
      alert("Pengaturan maintenance disimpan.");
    }
  } catch (err) {
    alert("Gagal mengubah maintenance mode.");
  }
});

function updateMaintenanceBtn(isEnabled) {
  const btn = document.getElementById("maintenance-toggle");
  if (!btn) return;
  if (isEnabled) {
    btn.textContent = "ENABLED";
    btn.className = "btn btn-primary"; // Kuning
  } else {
    btn.textContent = "DISABLED";
    btn.className = "btn btn-outline"; // Putih
  }
}