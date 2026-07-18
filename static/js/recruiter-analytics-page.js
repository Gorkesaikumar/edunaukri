(function () {
  "use strict";

  var sortState = { key: "application_count", dir: "desc" };

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function parseJsonScript(id, fallback) {
    var node = document.getElementById(id);
    if (!node || !node.textContent) return fallback;
    try {
      return JSON.parse(node.textContent);
    } catch (_err) {
      return fallback;
    }
  }

  function donutColor(tone) {
    if (tone === "primary") return "#3525cd";
    if (tone === "secondary") return "#8a4cfc";
    if (tone === "tertiary") return "#a78bfa";
    return "#c4b5fd";
  }

  function renderSourceDonut(sources) {
    var svg = document.getElementById("recDonutSvg");
    var totalEl = document.getElementById("recDonutTotal");
    var legend = document.getElementById("recDonutLegend");
    if (!svg || !legend) return;

    var segments = (sources && sources.segments) || [];
    var total = (sources && sources.total) || 0;
    if (totalEl) totalEl.textContent = total;

    var bg =
      '<circle cx="18" cy="18" r="16" fill="none" stroke="#ede7ff" stroke-width="4"></circle>';
    var offset = 0;
    var arcs = segments
      .filter(function (seg) {
        return (seg.pct || 0) > 0;
      })
      .map(function (seg) {
        var arc =
          '<circle cx="18" cy="18" r="16" fill="none" stroke="' +
          donutColor(seg.tone) +
          '" stroke-width="4" stroke-dasharray="' +
          seg.pct +
          ' 100" stroke-dashoffset="-' +
          offset +
          '" stroke-linecap="round" transform="rotate(-90 18 18)"></circle>';
        offset += seg.pct || 0;
        return arc;
      })
      .join("");
    svg.innerHTML = bg + arcs;

    legend.innerHTML = segments.length
      ? segments
          .map(function (seg) {
            return (
              '<div class="rcd-donut-legend__row">' +
              '<span><span class="rcd-donut-legend__dot rcd-donut-legend__dot--' +
              escapeHtml(seg.tone || "muted") +
              '"></span>' +
              escapeHtml(seg.label) +
              "</span>" +
              "<strong>" +
              (seg.pct || 0) +
              "% (" +
              (seg.count || 0) +
              ")</strong></div>"
            );
          })
          .join("")
      : '<p class="text-muted small mb-0">No source data yet.</p>';
  }

  function renderMiniBars(hostId, points, valueFormatter) {
    var host = document.getElementById(hostId);
    if (!host) return;
    var list = points || [];
    if (!list.length) {
      host.innerHTML = '<p class="rcd-analytics-v3__empty-inline">No trend data for this period.</p>';
      return;
    }
    var max = 0;
    list.forEach(function (point) {
      max = Math.max(max, Number(point.value || 0));
    });
    max = max || 1;
    host.innerHTML = list
      .map(function (point) {
        var value = Number(point.value || 0);
        var height = Math.max(4, Math.round((value / max) * 100));
        return (
          '<div class="rcd-analytics-page__mini-col" title="' +
          escapeHtml((valueFormatter ? valueFormatter(value) : value) + " on " + (point.label || "")) +
          '">' +
          '<div class="rcd-analytics-page__mini-bar" style="height:' +
          height +
          '%"></div>' +
          '<span class="rcd-analytics-page__mini-label">' +
          escapeHtml(point.label || "") +
          "</span></div>"
        );
      })
      .join("");
  }

  function renderInterviewSummary(analytics) {
    var trends = (analytics && analytics.interview_trends) || null;
    var scheduled = 0;
    var completed = 0;
    var cancelled = 0;
    var noShow = 0;

    if (trends) {
      scheduled = Number(trends.scheduled || 0);
      completed = Number(trends.completed || 0);
      cancelled = Number(trends.cancelled || 0);
      noShow = Number(trends.no_show || 0);
    } else {
      var funnel = (analytics && analytics.funnel) || [];
      funnel.forEach(function (step) {
        if (step.key === "interview_scheduled") scheduled = Number(step.value || 0);
        if (step.key === "interview_completed") completed = Number(step.value || 0);
      });
    }

    var successDen = completed + cancelled + noShow;
    var successRate = successDen ? Math.round((completed / successDen) * 100) : 0;

    var scheduledEl = document.getElementById("recInterviewScheduled");
    var completedEl = document.getElementById("recInterviewCompleted");
    var cancelledEl = document.getElementById("recInterviewCancelled");
    var noShowEl = document.getElementById("recInterviewNoShow");
    var successEl = document.getElementById("recInterviewSuccessRate");

    if (scheduledEl) scheduledEl.textContent = String(scheduled);
    if (completedEl) completedEl.textContent = String(completed);
    if (cancelledEl) cancelledEl.textContent = String(cancelled);
    if (noShowEl) noShowEl.textContent = String(noShow);
    if (successEl) successEl.textContent = String(successRate) + "%";
  }

  function updateResponseRate(metrics) {
    var host = document.getElementById("recAnalyticsResponseRate");
    if (!host || !metrics || !metrics.length) return;
    var responseMetric = metrics.find(function (metric) {
      return metric.key === "response_time";
    });
    if (responseMetric && responseMetric.value !== undefined && responseMetric.value !== null) {
      host.textContent = String(responseMetric.value) + "%";
    }
  }

  function renderVacancyRows(items) {
    var tbody = document.getElementById("recVacancyPerformanceBody");
    if (!tbody) return;
    var rows = items || [];
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="9"><div class="rcd-empty rcd-empty--compact">' +
        '<span class="material-symbols-outlined">work_off</span>' +
        "<h3>No vacancies to analyze</h3>" +
        "<p>Publish jobs to unlock vacancy-level conversion analytics.</p>" +
        "</div></td></tr>";
      return;
    }

    tbody.innerHTML = rows
      .map(function (job) {
        var apps = Number(job.application_count || 0);
        var hired = Number(job.hired_count || 0);
        var conversion = apps ? Math.round((hired / apps) * 100) : 0;
        return (
          '<tr data-title="' +
          escapeHtml((job.title || "").toLowerCase()) +
          '" data-status="' +
          escapeHtml(job.status || "") +
          '" data-title-sort="' +
          escapeHtml(job.title || "") +
          '" data-application_count="' +
          apps +
          '" data-views="' +
          Number(job.views || 0) +
          '" data-shortlisted_count="' +
          Number(job.shortlisted_count || 0) +
          '" data-interview_count="' +
          Number(job.interview_count || 0) +
          '" data-offer_count="' +
          Number(job.offer_count || 0) +
          '" data-hired_count="' +
          hired +
          '" data-conversion_rate="' +
          conversion +
          '">' +
          "<td>" +
          escapeHtml(job.title) +
          "</td>" +
          "<td>" +
          apps +
          "</td>" +
          "<td>" +
          Number(job.views || 0) +
          "</td>" +
          "<td>" +
          Number(job.shortlisted_count || 0) +
          "</td>" +
          "<td>" +
          Number(job.interview_count || 0) +
          "</td>" +
          "<td>" +
          Number(job.offer_count || 0) +
          "</td>" +
          "<td>" +
          hired +
          "</td>" +
          "<td>" +
          conversion +
          "%</td>" +
          '<td><span class="rcd-status-pill">' +
          escapeHtml(job.status_label || job.status || "") +
          "</span></td></tr>"
        );
      })
      .join("");
    applyVacancyFilters();
  }

  function sortedRows() {
    var tbody = document.getElementById("recVacancyPerformanceBody");
    if (!tbody) return [];
    var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr[data-title]"));
    var key = sortState.key;
    var dir = sortState.dir === "asc" ? 1 : -1;
    rows.sort(function (a, b) {
      var aval = a.getAttribute("data-" + key) || "";
      var bval = b.getAttribute("data-" + key) || "";
      if (key === "title") {
        aval = a.getAttribute("data-title-sort") || "";
        bval = b.getAttribute("data-title-sort") || "";
        return aval.localeCompare(bval) * dir;
      }
      return (Number(aval || 0) - Number(bval || 0)) * dir;
    });
    return rows;
  }

  function applyVacancyFilters() {
    var tbody = document.getElementById("recVacancyPerformanceBody");
    if (!tbody) return;
    var search = document.getElementById("recVacancySearch");
    var status = document.getElementById("recVacancyStatusFilter");
    var query = ((search && search.value) || "").trim().toLowerCase();
    var statusFilter = ((status && status.value) || "").trim().toLowerCase();

    sortedRows().forEach(function (row) {
      var title = (row.getAttribute("data-title") || "").toLowerCase();
      var rowStatus = (row.getAttribute("data-status") || "").toLowerCase();
      var matchesQuery = !query || title.indexOf(query) !== -1;
      var matchesStatus = !statusFilter || rowStatus === statusFilter;
      row.hidden = !(matchesQuery && matchesStatus);
      tbody.appendChild(row);
    });
  }

  function bindVacancyControls() {
    var search = document.getElementById("recVacancySearch");
    var status = document.getElementById("recVacancyStatusFilter");
    if (search && !search._bound) {
      search._bound = true;
      search.addEventListener("input", applyVacancyFilters);
    }
    if (status && !status._bound) {
      status._bound = true;
      status.addEventListener("change", applyVacancyFilters);
    }
    document.querySelectorAll(".rcd-table__sort-btn").forEach(function (btn) {
      if (btn._bound) return;
      btn._bound = true;
      btn.addEventListener("click", function () {
        var nextKey = btn.getAttribute("data-sort-key");
        if (sortState.key === nextKey) {
          sortState.dir = sortState.dir === "asc" ? "desc" : "asc";
        } else {
          sortState.key = nextKey;
          sortState.dir = nextKey === "title" ? "asc" : "desc";
        }
        applyVacancyFilters();
      });
    });
  }

  function refreshForPeriod(period) {
    var page = document.getElementById("recAnalyticsPage");
    if (!page) return;
    var url = page.getAttribute("data-insights-url");
    if (!url) return;
    if (window.RecAnalyticsSection) window.RecAnalyticsSection.showSkeleton(true);

    fetch(url + "?live=1&analytics_period=" + encodeURIComponent(period), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success || !payload.data) return;
        if (window.RecAnalyticsSection && payload.data.analytics) {
          window.RecAnalyticsSection.render(payload.data.analytics);
        }
        renderSourceDonut(payload.data.candidate_sources || { total: 0, segments: [] });
        renderMiniBars("recHiringTrendChart", (payload.data.analytics && payload.data.analytics.hiring_trends && payload.data.analytics.hiring_trends.daily) || []);
        renderInterviewSummary(payload.data.analytics || {});
        updateResponseRate((payload.data.analytics && payload.data.analytics.metrics) || []);
        renderVacancyRows(payload.data.active_jobs || []);
      })
      .catch(function () {})
      .finally(function () {
        if (window.RecAnalyticsSection) window.RecAnalyticsSection.showSkeleton(false);
      });
  }

  function bindPeriodSwitching() {
    document.querySelectorAll(".rcd-analytics-v3__period").forEach(function (btn) {
      if (btn._analyticsPageBound) return;
      btn._analyticsPageBound = true;
      btn.addEventListener("click", function () {
        var period = btn.getAttribute("data-period") || "7d";
        refreshForPeriod(period);
      });
    });
  }

  function init() {
    var page = document.getElementById("recAnalyticsPage");
    if (!page) return;

    var sourceData = parseJsonScript("recAnalyticsSourceData", { total: 0, segments: [] });
    var vacancies = parseJsonScript("recAnalyticsVacancyData", []);
    var hiringTrend = parseJsonScript("recAnalyticsHiringTrendData", { daily: [] });
    var interviewTrend = parseJsonScript("recAnalyticsInterviewTrendData", {});

    renderSourceDonut(sourceData);
    renderMiniBars("recHiringTrendChart", hiringTrend.daily || []);
    renderInterviewSummary({ interview_trends: interviewTrend });
    renderVacancyRows(vacancies);
    bindVacancyControls();
    bindPeriodSwitching();

    if (window.RecAnalyticsSection) {
      window.RecAnalyticsSection.bindExport();
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
