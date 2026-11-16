const API = ""; // same-origin

async function postJSON(path, body, headers = {}) {
  const res = await fetch(API + path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  
  let data;
  try {
    // Mencoba membaca respons sebagai JSON
    data = await res.json();
  } catch (e) {
    // Jika gagal (server error / bukan JSON), lempar pesan yang ramah
    throw new Error("Terjadi kesalahan pada server. Pastikan database sudah terhubung.");
  }

  if (!res.ok || !data.success) {
    throw new Error(data.message || "Request gagal");
  }
  return data;
}

// Register form
const registerForm = document.getElementById("register-form");
if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(registerForm);
    
    if (f.get("password") !== f.get("confirm_password")) {
      return showToast("Konfirmasi password tidak cocok.", "error");
    }
    
    const btn = registerForm.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    btn.textContent = "LOADING...";
    btn.disabled = true;

    try {
      await postJSON("/api/auth/register", {
        username: f.get("username"),
        full_name: f.get("full_name"),
        email: f.get("email"),
        password: f.get("password"),
      });
      showToast("Registrasi berhasil. Silakan login.", "success");
      setTimeout(() => (location.href = "/login"), 1200);
    } catch (err) {
      showToast(err.message, "error");
      btn.textContent = originalText;
      btn.disabled = false;
    }
  });
}

// Login form
const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(loginForm);
    
    const btn = loginForm.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    btn.textContent = "LOADING...";
    btn.disabled = true;

    try {
      await postJSON("/api/auth/login", {
        email: f.get("email"),
        password: f.get("password"),
        remember: f.get("remember") === "on",
      });
      location.href = "/dashboard";
    } catch (err) {
      showToast(err.message, "error");
      btn.textContent = originalText;
      btn.disabled = false;
    }
  });
}

// Fungsi Toast Notification
function showToast(message, type = "info") {
  // Hapus toast lama jika ada
  const existingToast = document.querySelector(".toast");
  if (existingToast) existingToast.remove();

  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  document.body.appendChild(el);
  
  // Hilangkan setelah 4 detik
  setTimeout(() => {
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 300);
  }, 4000);
}