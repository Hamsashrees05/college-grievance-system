(function () {
  var el = document.getElementById("chart-data");
  if (!el || typeof Chart === "undefined") { return; }
  var d = JSON.parse(el.textContent);
  var palette = ["#0a6c6a", "#17253a", "#b26a00", "#6b4c9a", "#2f7d32", "#a3333d", "#2a6fb0", "#7a7a7a"];
  function make(id, type, data, opts) {
    var canvas = document.getElementById(id);
    if (!canvas) { return; }
    new Chart(canvas, {
      type: type,
      data: { labels: data.labels, datasets: [{ label: "Complaints", data: data.values,
        backgroundColor: type === "line" ? "#0a6c6a" : palette, borderColor: "#0a6c6a", tension: 0.25 }] },
      options: Object.assign({ responsive: true, maintainAspectRatio: false }, opts || {})
    });
  }
  make("chart-status", "doughnut", d.status, { plugins: { legend: { position: "bottom" } } });
  make("chart-category", "bar", d.category, { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } });
  make("chart-monthly", "line", d.monthly, { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } });
})();
