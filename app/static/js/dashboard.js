/* Dashboard charts. The browser only renders; every number arrives already
   aggregated from the server (SQL GROUP BY), keeping the payload tiny. */
(function () {
  "use strict";

  const palette = {
    navy: "#16344e",
    brass: "#b6883b",
    green: "#2f8a59",
    amber: "#a9762a",
    red: "#bf4133",
    blue: "#2f6bb0",
    slate: "#8c9aa6",
    grid: "#eef1f0",
    ink: "#46596a",
  };

  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.color = palette.ink;
  Chart.defaults.font.size = 12;

  const statusColors = {
    pending: palette.amber,
    cleared: palette.green,
    flagged: palette.red,
    inspected: palette.blue,
  };

  async function getJSON(url) {
    const res = await fetch(url, { headers: { "Accept": "application/json" } });
    if (!res.ok) throw new Error("Request failed: " + url);
    return res.json();
  }

  const noLegend = { legend: { display: false } };

  function makeBar(ctx, data, color, horizontal) {
    return new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [{ data: data.values, backgroundColor: color, borderRadius: 6, maxBarThickness: 38 }],
      },
      options: {
        indexAxis: horizontal ? "y" : "x",
        responsive: true,
        maintainAspectRatio: false,
        plugins: noLegend,
        scales: {
          x: { grid: { color: palette.grid, drawBorder: false }, ticks: { precision: 0 } },
          y: { grid: { color: palette.grid, drawBorder: false }, ticks: { precision: 0 } },
        },
      },
    });
  }

  async function init() {
    try {
      const [trend, status, risk, flights, categories] = await Promise.all([
        getJSON("/api/analytics/trend"),
        getJSON("/api/analytics/status"),
        getJSON("/api/analytics/risk"),
        getJSON("/api/analytics/flights"),
        getJSON("/api/analytics/categories"),
      ]);

      // Trend line.
      new Chart(document.getElementById("trendChart"), {
        type: "line",
        data: {
          labels: trend.labels,
          datasets: [{
            data: trend.values,
            borderColor: palette.navy,
            backgroundColor: "rgba(22,52,78,.08)",
            fill: true,
            tension: 0.32,
            pointRadius: 3,
            pointBackgroundColor: palette.navy,
            borderWidth: 2,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: noLegend,
          scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true, grid: { color: palette.grid, drawBorder: false }, ticks: { precision: 0 } },
          },
        },
      });

      // Status doughnut.
      new Chart(document.getElementById("statusChart"), {
        type: "doughnut",
        data: {
          labels: status.labels.map((s) => s.charAt(0).toUpperCase() + s.slice(1)),
          datasets: [{ data: status.values, backgroundColor: status.labels.map((s) => statusColors[s] || palette.slate), borderWidth: 0 }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: "62%",
          plugins: { legend: { position: "bottom", labels: { boxWidth: 10, boxHeight: 10, padding: 14 } } },
        },
      });

      // Risk doughnut.
      new Chart(document.getElementById("riskChart"), {
        type: "doughnut",
        data: {
          labels: risk.labels,
          datasets: [{ data: risk.values, backgroundColor: [palette.green, palette.amber, palette.red], borderWidth: 0 }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: "62%",
          plugins: { legend: { position: "bottom", labels: { boxWidth: 10, boxHeight: 10, padding: 14 } } },
        },
      });

      makeBar(document.getElementById("flightChart"), flights, palette.navy, true);
      makeBar(document.getElementById("categoryChart"), categories, palette.brass, true);
    } catch (err) {
      console.error(err);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
