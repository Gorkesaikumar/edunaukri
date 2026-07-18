(function () {
  "use strict";

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderStats(stats) {
    if (!stats || !stats.length) return;
    stats.forEach(function (stat) {
      var card = document.querySelector('[data-stat-key="' + stat.key + '"] [data-stat-value]');
      if (card) card.textContent = stat.value;
    });
  }

  function renderPipeline(pipeline) {
    var row = document.getElementById("icdPipelineRow");
    if (!row || !pipeline) return;
    row.innerHTML = pipeline
      .map(function (stat) {
        return (
          '<article class="icd-card icd-card--hover icd-tracker__item icd-tracker__item--' +
          escapeHtml(stat.tone) +
          '"><p class="icd-tracker__value">' +
          escapeHtml(stat.value) +
          '</p><p class="icd-tracker__label">' +
          escapeHtml(stat.label) +
          "</p></article>"
        );
      })
      .join("");
  }

  function renderOverviewStats(stats) {
    var grid = document.getElementById("icdOverviewStatsGrid");
    if (!grid || !stats) return;
    if (!stats.length) return;
    grid.innerHTML = stats
      .map(function (stat) {
        return (
          '<article class="icd-card icd-frd-kpi" data-overview-key="' +
          escapeHtml(stat.key) +
          '"><p class="icd-frd-kpi__label">' +
          escapeHtml(stat.label) +
          '</p><p class="icd-frd-kpi__value">' +
          escapeHtml(stat.value) +
          '</p><p class="icd-frd-kpi__trend">' +
          escapeHtml(stat.trend || "") +
          "</p></article>"
        );
      })
      .join("");
  }

  function renderPipelineView(stages) {
    var box = document.getElementById("icdPipelineView");
    if (!box || !stages) return;
    if (!stages.length) return;
    box.innerHTML = stages
      .map(function (stage) {
        var pct = Number(stage.pct || 0);
        pct = Math.max(0, Math.min(100, pct));
        return (
          '<article class="icd-frd-pipeline__row" data-stage-key="' +
          escapeHtml(stage.key) +
          '"><div class="icd-frd-pipeline__meta"><p>' +
          escapeHtml(stage.label) +
          "</p><strong>" +
          escapeHtml(stage.value) +
          '</strong></div><div class="icd-frd-pipeline__track"><span class="icd-frd-pipeline__bar icd-frd-pipeline__bar--' +
          escapeHtml(stage.tone) +
          '" style="width: ' +
          pct +
          '%;"></span></div></article>'
        );
      })
      .join("");
  }

  function renderRecentApplications(rows) {
    var body = document.getElementById("icdRecentApplicationsBody");
    if (!body) return;
    if (!rows || !rows.length) return;
    body.innerHTML = rows
      .map(function (row) {
        return (
          "<tr><td><a href=\"" +
          escapeHtml(row.url) +
          "\">" +
          escapeHtml(row.candidate) +
          "</a></td><td>" +
          escapeHtml(row.vacancy_title) +
          "</td><td>" +
          escapeHtml(row.match_score || 0) +
          "%</td><td>" +
          escapeHtml(row.applied_label) +
          '</td><td><span class="icd-badge ' +
          escapeHtml(row.status_class) +
          '">' +
          escapeHtml(row.status_label) +
          "</span></td></tr>"
        );
      })
      .join("");
  }

  function renderActiveVacancies(vacancies) {
    var list = document.getElementById("icdActiveVacanciesList");
    if (!list || !vacancies) return;
    if (!vacancies.length) return;
    list.innerHTML = vacancies
      .map(function (vacancy) {
        return (
          '<li class="icd-card icd-card--hover icd-list__item"><h3 class="icd-list__title">' +
          escapeHtml(vacancy.title) +
          '</h3><p class="icd-list__meta">' +
          escapeHtml(vacancy.department) +
          " • " +
          escapeHtml(vacancy.location) +
          '</p><p class="icd-list__count">' +
          escapeHtml(vacancy.applications_count) +
          " application(s)</p></li>"
        );
      })
      .join("");
  }

  function refreshDashboard(forceLive) {
    var page = document.getElementById("icdDashboardPage");
    if (!page) return;
    var url = page.getAttribute("data-insights-url");
    if (!url) return;
    fetch(url + "?live=" + (forceLive ? "1" : "0"), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success || !payload.data) return;
        var data = payload.data;
        renderStats(data.stats);
        renderOverviewStats(data.overview_stats);
        renderPipeline(data.pipeline);
        renderPipelineView(data.pipeline_view);
        renderRecentApplications(data.recent_applications);
        renderActiveVacancies(data.active_vacancies);
      })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!document.getElementById("icdDashboardPage")) return;
    refreshDashboard(true);
    window.setInterval(function () {
      refreshDashboard(false);
    }, 120000);
  });
})();
