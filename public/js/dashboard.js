// Cek Autentikasi saat halaman dimuat
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const res = await fetch("/api/auth/me", { credentials: "include" });
    if (!res.ok) {
      window.location.href = "/login";
      return;
    }
    const data = await res.json();
    if (data.success) {
      document.getElementById("user-name").textContent = data.data.username;
      
      // Jika admin, tampilkan tombol admin (opsional)
      if (data.data.role === "admin") {
        const adminBtn = document.createElement("a");
        adminBtn.href = "/admin";
        adminBtn.className = "btn btn-outline";
        adminBtn.textContent = "ADMIN PANEL";
        adminBtn.style.marginLeft = "12px";
        document.querySelector(".topbar").appendChild(adminBtn);
      }
    }
  } catch (err) {
    window.location.href = "/login";
  }
});

// Logout
document.getElementById("logout-btn")?.addEventListener("click", async () => {
  const csrf = getCookie("ayaka_csrf");
  await fetch("/api/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrf },
    credentials: "include"
  });
  window.location.href = "/login";
});

// Tab Navigation (SPA behavior)
const navLinks = document.querySelectorAll(".sidebar-nav a[data-target]");
const sections = document.querySelectorAll(".page-section");

navLinks.forEach(link => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    // Remove active class
    navLinks.forEach(l => l.classList.remove("active"));
    link.classList.add("active");
    
    // Hide all sections
    sections.forEach(s => s.style.display = "none");
    
    // Show target section
    const targetId = link.getAttribute("data-target");
    document.getElementById(targetId).style.display = "block";
    
    // Update Title
    document.getElementById("page-title").textContent = link.textContent.trim();
  });
});

// Mobile Menu Toggle
const mobileBtn = document.getElementById("mobile-menu-btn");
const sidebar = document.getElementById("sidebar");
if (mobileBtn && window.innerWidth <= 768) {
  mobileBtn.style.display = "block";
  mobileBtn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });
}

// Utility
function getCookie(name) {
  return document.cookie.split("; ").find(row => row.startsWith(name + "="))?.split("=")[1];
}