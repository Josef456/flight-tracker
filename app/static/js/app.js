/* Shell behaviour: sidebar collapse (desktop), drawer toggle (mobile), and
   clickable table rows. State for the collapse is remembered per browser. */
(function () {
  "use strict";
  const shell = document.getElementById("shell");
  if (!shell) return;

  const collapseBtn = document.getElementById("sideCollapse");
  const toggleBtn = document.getElementById("sideToggle");
  const scrim = document.getElementById("scrim");

  // Desktop collapse, remembered.
  if (localStorage.getItem("ft-collapsed") === "1") shell.classList.add("collapsed");
  if (collapseBtn) {
    collapseBtn.addEventListener("click", function () {
      const on = shell.classList.toggle("collapsed");
      localStorage.setItem("ft-collapsed", on ? "1" : "0");
    });
  }

  // Mobile drawer.
  function closeNav() { shell.classList.remove("nav-open"); }
  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () { shell.classList.toggle("nav-open"); });
  }
  if (scrim) scrim.addEventListener("click", closeNav);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeNav(); });

  // Clickable rows: navigate on click unless a link or button was the target.
  document.querySelectorAll("tr.clickable[data-href]").forEach(function (row) {
    row.addEventListener("click", function (e) {
      if (e.target.closest("a, button, form")) return;
      window.location.href = row.getAttribute("data-href");
    });
  });
})();
