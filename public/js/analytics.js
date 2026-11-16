let analyticsTimer = null;

async function loadAnalytics() {
  const res = await fetch("/api/analytics", { credentials: "include" });
  const data = await res.json();
  if (!data.success) return;
  const d = data.data;
  const map = {
    "stat-total-requests": d.total_requests,
    "stat-total-keys": d.total_keys,
    "stat-active-keys": d.active_keys,
    "stat-revoked-keys": d.revoked_keys,
    "stat-success": d.success_requests,
    "stat-failed": d.failed_requests,
    "stat-premium": d.premium_active,
    "stat-emails": d.emails_sent,
  };
  Object.entries(map).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = Number(val).toLocaleString("id-ID");
  });
  document.getElementById("last-updated").textContent =
    "Terakhir: " + new Date(d.server_time).toLocaleTimeString("id-ID");

  if (window.Chart) {
    renderChart(d.hourly);
  }
}

function renderChart(hourly) {
  const ctx = document.getElementById("requests-chart");
  if (!ctx) return;
  if (window._chart) window._chart.destroy();
  window._chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: hourly.map((h) => new Date(h.hour).getHours() + ":00"),
      datasets: [
        {
          label: "Success",
          data: hourly.map((h) => h.success),
          borderColor: "#151515",
          backgroundColor: "rgba(255,214,0,.35)",
          fill: true,
          tension: 0.3,
        },
        {
          label: "Failed",
          data: hourly.map((h) => h.failed),
          borderColor: "#c62828",
          borderDash: [5, 4],
          tension: 0.3,
        },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });
}

function startPolling() {
  loadAnalytics();
  analyticsTimer = setInterval(loadAnalytics, 4000);
}

function stopPolling() {
  if (analyticsTimer) clearInterval(analyticsTimer);
  analyticsTimer = null;
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopPolling();
  else if (!analyticsTimer) startPolling();
});

if (document.getElementById("analytics-page")) startPolling();