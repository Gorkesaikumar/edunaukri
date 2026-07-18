(function () {
  "use strict";

  function escapeHtml(v) {
    return String(v || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showSkeleton(show) {
    var sk = document.getElementById("recAnalyticsSkeleton");
    var body = document.getElementById("recAnalyticsBody");
    if (sk) sk.hidden = !show;
    if (body) body.style.opacity = show ? "0.5" : "1";
  }

  function renderChart(trend) {
    var chart = document.getElementById("recAppsChart");
    var totalEl = document.getElementById("recAnalyticsTrendTotal");
    if (!chart || !trend) return;
    if (totalEl) totalEl.textContent = trend.total + " total";
    if (!trend.points || !trend.points.length) {
      chart.innerHTML = '<p class="rcd-analytics-v3__empty-inline">No applications in this period.</p>';
      return;
    }
    chart.innerHTML = trend.points
      .map(function (p) {
        return (
          '<div class="rcd-analytics-v3__bar-col" data-value="' +
          p.value +
          '">' +
          '<div class="rcd-analytics-v3__bar-wrap">' +
          '<div class="rcd-analytics-v3__bar" style="height:' +
          (p.bar_pct || 4) +
          '%"></div>' +
          '<span class="rcd-analytics-v3__tooltip">' +
          p.value +
          " applications</span></div>" +
          '<span class="rcd-analytics-v3__bar-label">' +
          escapeHtml(p.label) +
          "</span></div>"
        );
      })
      .join("");
  }

  function renderFunnel(funnel) {
    var host = document.getElementById("recFunnelList");
    if (!host || !funnel) return;
    host.innerHTML = funnel
      .map(function (step, idx) {
        return (
          '<div class="rcd-analytics-v3__funnel-row" style="animation-delay:' +
          idx * 40 +
          'ms">' +
          '<div class="rcd-analytics-v3__funnel-meta">' +
          '<span class="rcd-analytics-v3__funnel-label">' +
          escapeHtml(step.label) +
          "</span>" +
          '<span class="rcd-analytics-v3__funnel-stats"><strong>' +
          step.value +
          "</strong><small>" +
          step.pct +
          "%</small>" +
          (step.drop_off
            ? '<small class="rcd-analytics-v3__drop">−' + step.drop_off + "%</small>"
            : "") +
          "</span></div>" +
          '<div class="rcd-analytics-v3__funnel-track">' +
          '<div class="rcd-analytics-v3__funnel-fill rcd-analytics-v3__funnel-fill--' +
          escapeHtml(step.tone) +
          '" style="width:' +
          step.bar_pct +
          '%"></div></div></div>'
        );
      })
      .join("");
  }

  function renderMetrics(metrics) {
    var host = document.getElementById("recAnalyticsMetrics");
    if (!host || !metrics) return;
    host.innerHTML = metrics
      .map(function (m) {
        return (
          '<div class="rcd-analytics-v3__metric" data-metric-key="' +
          escapeHtml(m.key) +
          '">' +
          '<span class="material-symbols-outlined">' +
          escapeHtml(m.icon) +
          "</span><div>" +
          '<span class="rcd-analytics-v3__metric-label">' +
          escapeHtml(m.label) +
          "</span>" +
          '<strong class="rcd-analytics-v3__metric-value">' +
          escapeHtml(m.value) +
          (m.unit ? "<small>" + escapeHtml(m.unit) + "</small>" : "") +
          "</strong></div></div>"
        );
      })
      .join("");
  }

  function renderDepts(depts) {
    var host = document.getElementById("recAnalyticsDepts");
    if (!host) return;
    if (!depts || !depts.length) {
      host.innerHTML = '<p class="rcd-analytics-v3__empty-inline">No department data for this period.</p>';
      return;
    }
    host.innerHTML = depts
      .map(function (d) {
        return (
          '<div class="rcd-analytics-v3__dept-row">' +
          '<div class="rcd-analytics-v3__dept-head"><span>' +
          escapeHtml(d.label) +
          '</span><span class="rcd-analytics-v3__dept-counts">' +
          d.applicants +
          " applicants · " +
          d.hired +
          " hired</span></div>" +
          '<div class="rcd-analytics-v3__dept-track"><div class="rcd-analytics-v3__dept-fill" style="width:' +
          d.bar_pct +
          '%"></div></div>' +
          "<small class=\"text-muted\">" +
          d.jobs +
          " job(s)</small></div>"
        );
      })
      .join("");
  }

  function renderList(id, items, emptyMsg) {
    var host = document.getElementById(id);
    if (!host) return;
    if (!items || !items.length) {
      host.innerHTML = '<li class="rcd-analytics-v3__empty-inline">' + escapeHtml(emptyMsg) + "</li>";
      return;
    }
    if (id === "recAnalyticsTopJobs") {
      host.innerHTML = items
        .map(function (j) {
          return "<li><span>" + escapeHtml(j.title) + "</span><strong>" + j.applications + " apps</strong></li>";
        })
        .join("");
    } else {
      host.innerHTML = items
        .map(function (s) {
          return (
            "<li><span>" +
            escapeHtml(s.label) +
            "</span><strong>" +
            s.pct +
            "% (" +
            s.count +
            ")</strong></li>"
          );
        })
        .join("");
    }
  }

  function renderHighlights(hl) {
    if (!hl) return;
    Object.keys(hl).forEach(function (key) {
      var el = document.querySelector('[data-hl="' + key + '"]');
      if (el && hl[key] !== undefined && hl[key] !== null) {
        if (typeof hl[key] === "object" && hl[key].title) {
          el.textContent = hl[key].count;
        } else {
          el.textContent = hl[key];
        }
      }
    });
  }

  function render(analytics) {
    if (!analytics) return;
    var panel = document.getElementById("recAnalyticsPanel");
    var empty = document.getElementById("recAnalyticsEmpty");
    var body = document.getElementById("recAnalyticsBody");
    var label = document.getElementById("recAnalyticsPeriodLabel");

    if (label && analytics.period_label) label.textContent = analytics.period_label;

    if (!analytics.has_data) {
      if (empty) empty.hidden = false;
      if (body) body.hidden = true;
      return;
    }
    if (empty) empty.hidden = true;
    if (body) body.hidden = false;

    renderHighlights(analytics.highlights);
    renderChart(analytics.application_trend);
    renderFunnel(analytics.funnel);
    renderMetrics(analytics.metrics);
    renderDepts(analytics.departments);
    renderList("recAnalyticsTopJobs", analytics.top_jobs, "No job performance data yet.");
    renderList("recAnalyticsTopSources", analytics.top_sources, "No source data yet.");

    if (panel && analytics.period) {
      panel.querySelectorAll(".rcd-analytics-v3__period").forEach(function (btn) {
        var active = btn.getAttribute("data-period") === analytics.period;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-selected", active ? "true" : "false");
      });
    }
  }

  function bindPeriods(onChange) {
    document.querySelectorAll(".rcd-analytics-v3__period").forEach(function (btn) {
      if (btn._bound) return;
      btn._bound = true;
      btn.addEventListener("click", function () {
        var period = btn.getAttribute("data-period");
        if (onChange) onChange(period);
      });
    });
  }

  function bindExport() {
    document.querySelectorAll(".rec-analytics-export").forEach(function (btn) {
      if (btn._bound) return;
      btn._bound = true;
      btn.addEventListener("click", function () {
        var panel = document.getElementById("recAnalyticsPanel");
        var base = panel ? panel.getAttribute("data-export-url") : "";
        if (!base) return;
        var fmt = btn.getAttribute("data-format") || "csv";
        var active = document.querySelector(".rcd-analytics-v3__period.is-active");
        var period = active ? active.getAttribute("data-period") : "7d";
        var url = base + "?format=" + encodeURIComponent(fmt) + "&analytics_period=" + encodeURIComponent(period);
        if (fmt === "pdf") {
          window.open(url, "_blank");
        } else {
          window.location.href = url;
        }
      });
    });
  }

  window.RecAnalyticsSection = {
    render: render,
    showSkeleton: showSkeleton,
    bindPeriods: bindPeriods,
    bindExport: bindExport,
  };

  document.addEventListener("DOMContentLoaded", function () {
    bindExport();
  });
})();
