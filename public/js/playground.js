const sendBtn = document.getElementById("pg-send-btn");

if (sendBtn) {
  sendBtn.addEventListener("click", async () => {
    const method = document.getElementById("pg-method").value;
    const endpoint = document.getElementById("pg-endpoint").value;
    const apiKey = document.getElementById("pg-apikey").value;
    const bodyText = document.getElementById("pg-body").value;
    
    const responseArea = document.getElementById("pg-response");
    const statusBadge = document.getElementById("pg-status");
    const timeBadge = document.getElementById("pg-time");
    
    // Reset UI
    responseArea.value = "Loading...";
    statusBadge.style.display = "none";
    timeBadge.textContent = "";
    
    const startTime = performance.now();
    
    try {
      const headers = {
        "Content-Type": "application/json"
      };
      
      if (apiKey) {
        headers["X-API-Key"] = apiKey;
      }
      
      const options = {
        method,
        headers
      };
      
      if (method !== "GET" && bodyText.trim()) {
        // Validasi JSON
        try {
          JSON.parse(bodyText);
          options.body = bodyText;
        } catch (e) {
          throw new Error("Invalid JSON Body");
        }
      }
      
      // Pastikan endpoint diawali dengan /api/
      const url = endpoint.startsWith("/") ? endpoint : "/" + endpoint;
      
      const res = await fetch(url, options);
      const endTime = performance.now();
      const duration = Math.round(endTime - startTime);
      
      const data = await res.json();
      
      // Update UI
      statusBadge.textContent = res.status;
      statusBadge.className = `badge ${res.ok ? 'badge-active' : 'badge-revoked'}`;
      statusBadge.style.display = "inline-block";
      timeBadge.textContent = `${duration} ms`;
      
      responseArea.value = JSON.stringify(data, null, 2);
      
    } catch (err) {
      responseArea.value = `Error: ${err.message}`;
      statusBadge.textContent = "ERROR";
      statusBadge.className = "badge badge-revoked";
      statusBadge.style.display = "inline-block";
    }
  });
}