// Scroll reveal dengan IntersectionObserver
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add("visible");
    });
  },
  { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
);
document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));

// Counter animation
function animateCounter(el) {
  const target = parseInt(el.dataset.counter || "0", 10);
  if (!target) return;
  let current = 0;
  const step = Math.max(1, Math.floor(target / 40));
  const timer = setInterval(() => {
    current += step;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    el.textContent = current.toLocaleString("id-ID");
  }, 30);
}
const counterObserver = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (e.isIntersecting) {
      animateCounter(e.target);
      counterObserver.unobserve(e.target);
    }
  });
});
document.querySelectorAll("[data-counter]").forEach((el) => counterObserver.observe(el));

// Visitor tracking (anonim)
if (location.pathname === "/" || location.pathname === "/documentation") {
  fetch("/api/track", { method: "POST" }).catch(() => {});
}