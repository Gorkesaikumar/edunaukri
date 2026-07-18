(function () {
  "use strict";

  var pollTimer = null;
  var statusTemplate = "";
  var detailTemplate = "";
  var notesTemplate = "";
  var resumeTemplate = "";
  var donutColors = {
    primary: "#3525cd",
    secondary: "#8a4cfc",
    tertiary: "#a78bfa",
    muted: "#c4b5fd",
  };

  function csrf() {
    var page = document.getElementById("recDashboardPage");
    return page ? page.getAttribute("data-csrf") : "";
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function notify(type, message) {
    if (window.EduNotify && window.EduNotify.toast) {
      window.EduNotify.toast(type, message);
    }
  }

  function confirmAction(options) {
    if (!window.EduNotify || typeof window.EduNotify.confirm !== "function") {
      return Promise.resolve(false);
    }
    return window.EduNotify.confirm(options);
  }

  function promptAction(options) {
    if (!window.EduNotify || typeof window.EduNotify.prompt !== "function") {
      return Promise.resolve(null);
    }
    return window.EduNotify.prompt(options);
  }

  function showSkeleton(show) {
    var sk = document.getElementById("recDashboardSkeleton");
    if (sk) sk.hidden = !show;
  }

  function apiTemplatesFromPage() {
    var page = document.getElementById("recDashboardPage");
    if (!page) return;
    detailTemplate = page.getAttribute("data-detail-template") || detailTemplate;
    notesTemplate = page.getAttribute("data-notes-template") || notesTemplate;
    resumeTemplate = page.getAttribute("data-resume-template") || resumeTemplate;
    statusTemplate = page.getAttribute("data-status-template") || statusTemplate;
  }

  function templateUrl(template, id) {
    return template ? template.replace("00000000-0000-0000-0000-000000000000", id) : "";
  }

  function postJson(url, method, body) {
    return fetch(url, {
      method: method || "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (res) {
      return res.json();
    });
  }

  function buildQuery() {
    var form = document.getElementById("recDashboardFilters");
    if (!form) return "";
    var params = new URLSearchParams(new FormData(form));
    var activePeriod = document.querySelector(".rcd-analytics-v3__period.is-active");
    if (activePeriod) {
      params.set("analytics_period", activePeriod.getAttribute("data-period"));
    }
    var qs = params.toString();
    return qs ? "&" + qs : "";
  }

  function renderStats(stats) {
    if (!stats) return;
    stats.forEach(function (stat) {
      var card = document.querySelector('[data-stat-key="' + stat.key + '"]');
      if (!card) return;
      var valueEl = card.querySelector("[data-stat-value]");
      var trendEl = card.querySelector("[data-stat-trend]");
      var subtitleEl = card.querySelector("[data-stat-subtitle]");
      if (valueEl) valueEl.textContent = stat.value;
      if (trendEl && stat.trend) {
        var neutral = stat.trend.tone === "muted" || stat.trend.label === "No Change";
        trendEl.hidden = false;
        trendEl.textContent = neutral ? "No Change" : stat.trend.label;
        trendEl.className =
          "rcd-stat__trend rcd-stat__trend--" + (neutral ? "muted" : stat.trend.tone || "up");
      }
      if (subtitleEl) {
        subtitleEl.textContent = stat.subtitle || "";
        subtitleEl.hidden = false;
      }
    });
  }

  function pipelineCardHtml(card, accent) {
    var draggable = card.can_drag ? " rcd-pipeline-card--draggable" : "";
    var dragAttr = card.can_drag ? ' draggable="true"' : "";
    var avatar = card.photo_url
      ? '<img src="' + escapeHtml(card.photo_url) + '" alt="">'
      : "<span>" + escapeHtml(card.initials) + "</span>";
    var skills = (card.skills || [])
      .slice(0, 3)
      .map(function (s) {
        return '<span class="rcd-pipeline-card__skill">' + escapeHtml(s) + "</span>";
      })
      .join("");
    var skillsBlock = skills ? '<div class="rcd-pipeline-card__skills">' + skills + "</div>" : "";
    return (
      '<article class="rcd-pipeline-card' +
      draggable +
      '"' +
      dragAttr +
      ' data-application-id="' +
      escapeHtml(card.id) +
      '" data-detail="' +
      escapeHtml(card.detail_json || JSON.stringify(card.detail || {})) +
      '" data-applied="' +
      escapeHtml(card.applied_label) +
      '" data-profile-url="' +
      escapeHtml(card.url || "") +
      '" tabindex="0" role="button" aria-label="View ' +
      escapeHtml(card.name) +
      '">' +
      '<div class="rcd-pipeline-card__row">' +
      '<div class="rcd-pipeline-card__avatar">' +
      avatar +
      "</div>" +
      '<div class="rcd-pipeline-card__info">' +
      '<p class="rcd-pipeline-card__name">' +
      escapeHtml(card.name) +
      "</p>" +
      '<p class="rcd-pipeline-card__role">' +
      escapeHtml(card.job_title) +
      "</p>" +
      "</div></div>" +
      '<div class="rcd-pipeline-card__meta">' +
      '<span class="rcd-pipeline-card__badge rcd-pipeline-card__badge--' +
      escapeHtml(accent) +
      '">' +
      escapeHtml(card.experience) +
      "</span>" +
      '<span class="rcd-pipeline-card__time">' +
      escapeHtml(card.time_label) +
      "</span></div>" +
      skillsBlock +
      "</article>"
    );
  }

  function renderPipeline(pipeline) {
    if (!pipeline) return;
    pipeline.forEach(function (col) {
      var column = document.querySelector('[data-pipeline-key="' + col.key + '"]');
      if (!column) return;
      var countEl = column.querySelector("[data-pipeline-count]");
      if (countEl) countEl.textContent = col.count;
      var existingCards = column.querySelector("[data-pipeline-cards]");
      var existingEmpty = column.querySelector(".rcd-pipeline__empty");
      if (existingCards) existingCards.remove();
      if (existingEmpty) existingEmpty.remove();
      if (!col.cards || !col.cards.length) {
        column.insertAdjacentHTML(
          "beforeend",
          '<div class="rcd-pipeline__empty">' +
            '<span class="material-symbols-outlined" aria-hidden="true">person_search</span>' +
            "<p>No candidates in this stage</p>" +
            '<span class="rcd-pipeline__empty-hint">Candidates will appear here as they progress.</span>' +
            "</div>"
        );
        return;
      }
      var html =
        '<div class="rcd-pipeline__cards" data-pipeline-cards>' +
        col.cards.map(function (card) {
          return pipelineCardHtml(card, col.accent);
        }).join("") +
        "</div>";
      column.insertAdjacentHTML("beforeend", html);
    });
    bindPipelineDragDrop();
    bindPipelineSearch();
  }

  function jobCardHtml(job) {
    var badges = (job.badges || [])
      .map(function (b) {
        return '<span class="rcd-job-badge rcd-job-badge--' + escapeHtml(b) + '">' + escapeHtml(b.charAt(0).toUpperCase() + b.slice(1)) + "</span>";
      })
      .join("");
    var salary = job.salary_range
      ? '<span><span class="material-symbols-outlined">payments</span>' + escapeHtml(job.salary_range) + "</span>"
      : "";
    var deadline =
      job.deadline_label && job.deadline_label !== "—"
        ? '<span><span class="material-symbols-outlined">hourglass_top</span>Deadline ' + escapeHtml(job.deadline_label) + "</span>"
        : "";
    var actions = [
      '<a href="' + escapeHtml(job.url) + '" class="rcd-btn rcd-btn--soft rcd-btn--xs">View</a>',
      '<a href="' + escapeHtml(job.edit_url) + '" class="rcd-btn rcd-btn--soft rcd-btn--xs">Edit</a>',
    ];
    if (job.can_duplicate) {
      actions.push('<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-job-duplicate" data-url="' + escapeHtml(job.duplicate_url) + '">Duplicate</button>');
    }
    if (job.can_publish) {
      actions.push('<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-job-publish" data-url="' + escapeHtml(job.publish_url) + '">Publish</button>');
    }
    if (job.can_pause) {
      actions.push('<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-job-pause" data-url="' + escapeHtml(job.pause_url) + '">Pause</button>');
    }
    if (job.can_close) {
      actions.push('<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-job-close" data-url="' + escapeHtml(job.close_url) + '">Close</button>');
    }
    if (job.can_delete) {
      actions.push('<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-job-delete" data-url="' + escapeHtml(job.delete_url) + '">Delete</button>');
    }
    return (
      '<article class="rcd-bento rcd-bento--press rcd-job-card-v2" data-job-id="' +
      escapeHtml(job.id) +
      '"><div class="rcd-job-card-v2__head"><div class="rcd-job-card-v2__badges">' +
      badges +
      '<span class="rcd-job-badge rcd-job-badge--status">' +
      escapeHtml(job.status_label) +
      "</span></div><h3 class=\"rcd-job-card-v2__title\">" +
      escapeHtml(job.title) +
      "</h3><p class=\"rcd-job-card-v2__dept\">" +
      escapeHtml(job.department) +
      " · " +
      escapeHtml(job.employment_type) +
      "</p></div><div class=\"rcd-job-card-v2__meta\"><span><span class=\"material-symbols-outlined\">location_on</span>" +
      escapeHtml(job.location) +
      "</span>" +
      salary +
      '<span><span class="material-symbols-outlined">event</span>Posted ' +
      escapeHtml(job.posted_label) +
      "</span>" +
      deadline +
      '</div><div class="rcd-job-card-v2__stats"><div><strong>' +
      job.application_count +
      '</strong><span>Applicants</span></div><div><strong>' +
      job.shortlisted_count +
      '</strong><span>Shortlisted</span></div><div><strong>' +
      job.interview_count +
      '</strong><span>Interviews</span></div><div><strong>' +
      job.offer_count +
      '</strong><span>Offers</span></div><div><strong>' +
      job.hired_count +
      '</strong><span>Hired</span></div></div><div class="rcd-job-card-v2__actions">' +
      actions.join("") +
      "</div></article>"
    );
  }

  function renderActiveJobs(jobs) {
    var grid = document.getElementById("recActiveJobsGrid");
    if (!grid) return;
    if (!jobs || !jobs.length) {
      grid.innerHTML =
        '<div class="rcd-bento rcd-empty"><span class="material-symbols-outlined d-block">work_off</span><h2>No active jobs</h2><p>Publish a job to start receiving applications.</p></div>';
      return;
    }
    grid.innerHTML = jobs.map(jobCardHtml).join("");
    bindJobActions();
  }

  function renderDonut(sources) {
    if (!sources) return;
    var totalEl = document.getElementById("recDonutTotal");
    var svg = document.getElementById("recDonutSvg");
    var legend = document.getElementById("recDonutLegend");
    if (totalEl) totalEl.textContent = sources.total;
    if (svg) {
      var bg =
        '<circle cx="18" cy="18" r="16" fill="none" stroke="#f0ecf9" stroke-width="4"></circle>';
      var arcs = (sources.segments || [])
        .filter(function (seg) {
          return seg.pct > 0;
        })
        .map(function (seg) {
          var color = donutColors[seg.tone] || donutColors.muted;
          var offset = seg.stroke_offset || 0;
          return (
            '<circle cx="18" cy="18" r="16" fill="none" stroke="' +
            color +
            '" stroke-width="4" stroke-dasharray="' +
            seg.pct +
            ' 100" stroke-dashoffset="-' +
            offset +
            '" stroke-linecap="round" transform="rotate(-90 18 18)" data-source-key="' +
            escapeHtml(seg.key) +
            '"></circle>'
          );
        })
        .join("");
      svg.innerHTML = bg + arcs;
    }
    if (legend) {
      legend.innerHTML = (sources.segments || [])
        .map(function (seg) {
          return (
            '<button type="button" class="rcd-donut-legend__row rcd-donut-legend__btn" data-source-filter="' +
            escapeHtml(seg.key) +
            '">' +
            "<span><span class=\"rcd-donut-legend__dot rcd-donut-legend__dot--" +
            escapeHtml(seg.tone) +
            "\"></span>" +
            escapeHtml(seg.label) +
            "</span>" +
            "<span><strong>" +
            seg.pct +
            "%</strong> <small class=\"text-muted\">" +
            escapeHtml(seg.trend) +
            "</small></span></button>"
          );
        })
        .join("");
      bindSourceFilters();
    }
  }

  function renderInterviews(items, todayCount) {
    renderInterviewsToday(todayCount || 0);
    var host = document.getElementById("recInterviewsList");
    if (!host) return;
    if (!items || !items.length) {
      host.innerHTML =
        '<div class="rcd-empty rcd-empty--compact">' +
        '<span class="material-symbols-outlined">event_available</span>' +
        "<h3>Nothing scheduled</h3>" +
        "<p>Interviews appear here once scheduled with candidates.</p></div>";
      return;
    }
    host.innerHTML = items
      .map(function (item, idx) {
        var cls =
          "rcd-interview-item" +
          (item.within_hour ? " rcd-interview-item--urgent" : "") +
          (idx > 0 ? " rcd-interview-item--plain" : "");
        var live = item.is_live
          ? '<span class="rcd-interview-item__live" aria-label="Live now"></span>'
          : "";
        var join =
          item.meet_url && item.is_online
            ? '<a href="' +
              escapeHtml(item.meet_url) +
              '" target="_blank" rel="noopener" class="rcd-btn rcd-btn--primary rcd-btn--sm">Join Meeting</a>'
            : "";
        var reschedule = item.can_reschedule
          ? '<button type="button" class="rcd-btn rcd-btn--outline rcd-btn--sm rec-interview-reschedule" data-url="' +
            escapeHtml(item.reschedule_url) +
            '" data-scheduled="' +
            escapeHtml(item.scheduled_at_iso) +
            '">Reschedule</button>'
          : "";
        var cancelBtn = item.can_cancel
          ? '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--sm rec-interview-cancel" data-url="' +
            escapeHtml(item.cancel_url) +
            '">Cancel</button>'
          : "";
        return (
          '<div class="' +
          cls +
          '">' +
          '<div class="rcd-interview-item__time">' +
          "<span>" +
          escapeHtml(item.time_label) +
          "</span>" +
          '<span class="rcd-interview-timing rcd-interview-timing--' +
          escapeHtml(item.timing) +
          '">' +
          escapeHtml(item.timing.charAt(0).toUpperCase() + item.timing.slice(1)) +
          "</span>" +
          live +
          "</div>" +
          '<div class="rcd-interview-item__row">' +
          '<div class="rcd-interview-item__avatar">' +
          escapeHtml(item.initials) +
          "</div><div>" +
          '<p class="mb-0 fw-semibold" style="font-size:0.875rem">' +
          escapeHtml(item.candidate_name) +
          "</p>" +
          '<p class="mb-0 text-muted" style="font-size:0.75rem">' +
          escapeHtml(item.job_title) +
          " · " +
          escapeHtml(item.round_label) +
          "</p>" +
          '<p class="mb-0 text-muted" style="font-size:0.6875rem">' +
          escapeHtml(item.mode) +
          " · " +
          item.duration_minutes +
          " min · " +
          escapeHtml(item.interviewer) +
          "</p></div></div>" +
          '<div class="rcd-interview-item__actions">' +
          join +
          reschedule +
          cancelBtn +
          '<a href="' +
          escapeHtml(item.interviews_url) +
          '" class="rcd-btn rcd-btn--outline rcd-btn--sm">Calendar</a>' +
          '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--sm rec-view-candidate" data-application-id="' +
          escapeHtml(item.application_id) +
          '">View Candidate</button>' +
          "</div></div>"
        );
      })
      .join("");
    bindInterviewActions();
    bindViewCandidateButtons();
  }

  function renderInterviewsToday(count) {
    var badge = document.getElementById("recInterviewsTodayBadge");
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count + " Today";
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
  }

  function renderNotifications(items) {
    var list = document.getElementById("recNotificationsList");
    if (!list) return;
    if (!items || !items.length) {
      list.innerHTML = '<li class="rcd-empty rcd-empty--compact"><p>No notifications</p></li>';
      return;
    }
    list.innerHTML = items
      .map(function (note) {
        return (
          '<li class="rcd-activity-item' +
          (note.is_read ? "" : " rcd-activity-item--unread") +
          '">' +
          '<span class="material-symbols-outlined">notifications</span>' +
          "<div>" +
          '<p class="mb-0 fw-semibold">' +
          escapeHtml(note.title) +
          "</p>" +
          '<p class="mb-0 text-muted small">' +
          escapeHtml(note.body) +
          "</p>" +
          '<time class="text-muted" style="font-size:0.6875rem">' +
          escapeHtml(note.timestamp) +
          "</time></div></li>"
        );
      })
      .join("");
  }

  function renderActivity(items) {
    var list = document.getElementById("recActivityList");
    if (!list) return;
    if (!items || !items.length) {
      list.innerHTML = '<li class="rcd-empty rcd-empty--compact"><p>No recent activity</p></li>';
      return;
    }
    list.innerHTML = items
      .map(function (act) {
        return (
          '<li class="rcd-activity-item">' +
          '<span class="material-symbols-outlined">timeline</span>' +
          "<div>" +
          '<p class="mb-0 fw-semibold">' +
          escapeHtml(act.label) +
          "</p>" +
          '<p class="mb-0 text-muted small">' +
          escapeHtml(act.candidate) +
          " · " +
          escapeHtml(act.job_title) +
          "</p>" +
          '<time class="text-muted" style="font-size:0.6875rem">' +
          escapeHtml(act.timestamp) +
          "</time></div></li>"
        );
      })
      .join("");
  }

  function renderAnalytics(analytics) {
    if (window.RecAnalyticsSection) {
      window.RecAnalyticsSection.render(analytics);
    }
  }

  function renderRecentApplications(apps) {
    var tbody = document.getElementById("recRecentApplicationsBody");
    if (!tbody || !apps) return;
    tbody.innerHTML = apps
      .map(function (app) {
        return (
          '<tr data-application-id="' +
          escapeHtml(app.id) +
          '"><td><button type="button" class="rcd-table__link rec-view-candidate" data-application-id="' +
          escapeHtml(app.id) +
          '">' +
          escapeHtml(app.candidate) +
          "</button></td><td>" +
          escapeHtml(app.job_title) +
          "</td><td>" +
          escapeHtml(app.company) +
          '</td><td><span class="rcd-status-pill">' +
          escapeHtml(app.status_label) +
          "</span></td><td>" +
          escapeHtml(app.applied_label) +
          "</td></tr>"
        );
      })
      .join("");
    bindViewCandidateButtons();
  }

  function refreshDashboard(forceRefresh) {
    var page = document.getElementById("recDashboardPage");
    if (!page) return;
    var url = page.getAttribute("data-insights-url");
    if (!url) return;
    var fetchUrl = url + "?live=" + (forceRefresh ? "1" : "0") + buildQuery();
    showSkeleton(true);
    if (window.RecAnalyticsSection) window.RecAnalyticsSection.showSkeleton(true);
    fetch(fetchUrl, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success || !payload.data) return;
        var data = payload.data;
        if (data.api_urls) {
          statusTemplate = data.api_urls.status_template || statusTemplate;
          detailTemplate = data.api_urls.detail_template || detailTemplate;
          notesTemplate = data.api_urls.notes_template || notesTemplate;
          resumeTemplate = data.api_urls.resume_template || resumeTemplate;
        }
        renderStats(data.stats);
        renderPipeline(data.pipeline);
        renderActiveJobs(data.active_jobs);
        renderInterviews(data.upcoming_interviews, data.interviews_today);
        renderDonut(data.candidate_sources);
        renderNotifications(data.notifications);
        renderActivity(data.recent_activity);
        renderAnalytics(data.analytics);
        renderRecentApplications(data.recent_applications);
      })
      .catch(function () {})
      .finally(function () {
        showSkeleton(false);
        if (window.RecAnalyticsSection) window.RecAnalyticsSection.showSkeleton(false);
      });
  }

  function refreshAnalyticsPeriod(period) {
    var page = document.getElementById("recDashboardPage");
    if (!page) return;
    var url = page.getAttribute("data-insights-url");
    if (!url) return;
    var params = new URLSearchParams(buildQuery().replace(/^&/, ""));
    params.set("analytics_period", period);
    params.set("live", "1");
    if (window.RecAnalyticsSection) window.RecAnalyticsSection.showSkeleton(true);
    fetch(url + "?" + params.toString(), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (payload.success && payload.data && payload.data.analytics) {
          renderAnalytics(payload.data.analytics);
        }
      })
      .finally(function () {
        if (window.RecAnalyticsSection) window.RecAnalyticsSection.showSkeleton(false);
      });
  }

  function bindSourceFilters() {
    document.querySelectorAll("[data-source-filter]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var source = btn.getAttribute("data-source-filter");
        var input = document.getElementById("rcFilterSource");
        if (input) input.value = source;
        refreshDashboard(true);
      });
    });
  }

  function bindFilters() {
    var form = document.getElementById("recDashboardFilters");
    var reset = document.getElementById("recDashboardFiltersReset");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        refreshDashboard(true);
      });
    }
    if (reset) {
      reset.addEventListener("click", function () {
        form.reset();
        var src = document.getElementById("rcFilterSource");
        if (src) src.value = "";
        refreshDashboard(true);
      });
    }
    bindSourceFilters();
  }

  function bindPipelineSearch() {
    var input = document.getElementById("recPipelineSearch");
    if (!input || input._bound) return;
    input._bound = true;
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      document.querySelectorAll(".rcd-pipeline-card").forEach(function (card) {
        var text = card.textContent.toLowerCase();
        card.hidden = q && text.indexOf(q) === -1;
      });
    });
  }

  function bindPipelineDragDrop() {
    var dragged = null;
    document.querySelectorAll(".rcd-pipeline-card--draggable").forEach(function (card) {
      if (card._dragBound) return;
      card._dragBound = true;
      card.addEventListener("dragstart", function (e) {
        dragged = card;
        card.classList.add("rcd-pipeline-card--dragging");
        e.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragend", function () {
        card.classList.remove("rcd-pipeline-card--dragging");
        document.querySelectorAll(".rcd-pipeline__col--drag-over").forEach(function (col) {
          col.classList.remove("rcd-pipeline__col--drag-over");
        });
      });
      card.addEventListener("click", function (e) {
        if (card.classList.contains("rcd-pipeline-card--dragging")) return;
        e.preventDefault();
        openCandidateDrawer(card);
      });
    });

    document.querySelectorAll(".rcd-pipeline__col").forEach(function (col) {
      if (col._dropBound) return;
      col._dropBound = true;
      col.addEventListener("dragover", function (e) {
        e.preventDefault();
        col.classList.add("rcd-pipeline__col--drag-over");
      });
      col.addEventListener("dragleave", function () {
        col.classList.remove("rcd-pipeline__col--drag-over");
      });
      col.addEventListener("drop", function (e) {
        e.preventDefault();
        col.classList.remove("rcd-pipeline__col--drag-over");
        if (!dragged) return;
        var appId = dragged.getAttribute("data-application-id");
        var targetStatus = col.getAttribute("data-target-status");
        if (!appId || !targetStatus || !statusTemplate) return;
        var url = statusTemplate.replace("00000000-0000-0000-0000-000000000000", appId);
        fetch(url, {
          method: "PATCH",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ status: targetStatus, notes: "Moved via dashboard pipeline." }),
        })
          .then(function (res) {
            return res.json();
          })
          .then(function (body) {
            if (!body.success) throw new Error(body.error || "Unable to move candidate.");
            dragged.classList.add("rcd-pipeline-card--moving");
            var host = col.querySelector("[data-pipeline-cards]");
            if (host) host.appendChild(dragged);
            else col.appendChild(dragged);
            notify("success", "Candidate moved successfully.");
            refreshDashboard(true);
          })
          .catch(function (err) {
            notify("error", err.message);
          });
      });
    });
  }

  function renderDrawerContent(app) {
    var statusOptions = (app.next_statuses || [])
      .map(function (s) {
        return '<option value="' + escapeHtml(s.value) + '">' + escapeHtml(s.label) + "</option>";
      })
      .join("");
    var statusSelect =
      !app.is_terminal && statusOptions
        ? '<label class="form-label small">Move to</label><select class="form-select form-select-sm rec-drawer-status" data-url="' +
          escapeHtml(app.status_url) +
          '"><option value="">Select status…</option>' +
          statusOptions +
          "</select>"
        : "";
    var resumeBtn = app.has_resume
      ? '<a href="' + escapeHtml(app.resume_url) + '" class="rcd-btn rcd-btn--outline rcd-btn--sm" download>Download Resume</a>'
      : "";
    return (
      '<div class="rcd-drawer-profile">' +
      '<div class="rcd-drawer-profile__head">' +
      '<div class="rcd-pipeline-card__avatar"><span>' +
      escapeHtml(app.initials) +
      "</span></div>" +
      "<div><h6 class=\"mb-0\">" +
      escapeHtml(app.applicant_name) +
      "</h6><p class=\"text-muted mb-0 small\">" +
      escapeHtml(app.job_title) +
      " · " +
      escapeHtml(app.company_name) +
      "</p></div></div>" +
      '<span class="rcd-status-pill mb-3 d-inline-block">' +
      escapeHtml(app.status_label) +
      "</span>" +
      '<dl class="rcd-drawer-meta">' +
      "<dt>Applied</dt><dd>" +
      escapeHtml(app.applied_label) +
      "</dd>" +
      "<dt>Location</dt><dd>" +
      escapeHtml(app.location) +
      "</dd>" +
      "<dt>Expected salary</dt><dd>" +
      escapeHtml(app.expected_salary) +
      "</dd>" +
      "<dt>Notice period</dt><dd>" +
      escapeHtml(app.notice_period) +
      "</dd></dl>" +
      statusSelect +
      '<label class="form-label small mt-2">Recruiter notes</label>' +
      '<textarea class="form-control form-control-sm rec-drawer-notes" rows="3" data-url="' +
      escapeHtml(app.notes_url) +
      '">' +
      escapeHtml(app.recruiter_notes || "") +
      "</textarea>" +
      '<div class="d-flex flex-wrap gap-2 mt-3">' +
      resumeBtn +
      '<button type="button" class="rcd-btn rcd-btn--primary rcd-btn--sm rec-drawer-notes-save">Save Notes</button>' +
      "</div></div>"
    );
  }

  function bindDrawerActions() {
    var body = document.getElementById("recCandidateDrawerBody");
    if (!body) return;
    var statusEl = body.querySelector(".rec-drawer-status");
    if (statusEl && !statusEl._bound) {
      statusEl._bound = true;
      statusEl.addEventListener("change", function () {
        var status = statusEl.value;
        if (!status) return;
        postJson(statusEl.getAttribute("data-url"), "PATCH", { status: status, notes: "" })
          .then(function (body) {
            if (!body.success) throw new Error(body.error || "Status update failed.");
            notify("success", body.message || "Status updated.");
            refreshDashboard(true);
          })
          .catch(function (err) {
            notify("error", err.message);
            statusEl.value = "";
          });
      });
    }
    var saveBtn = body.querySelector(".rec-drawer-notes-save");
    if (saveBtn && !saveBtn._bound) {
      saveBtn._bound = true;
      saveBtn.addEventListener("click", function () {
        var textarea = body.querySelector(".rec-drawer-notes");
        if (!textarea) return;
        postJson(textarea.getAttribute("data-url"), "PATCH", { recruiter_notes: textarea.value.trim() })
          .then(function (body) {
            if (!body.success) throw new Error(body.error || "Unable to save notes.");
            notify("success", body.message || "Notes saved.");
          })
          .catch(function (err) {
            notify("error", err.message);
          });
      });
    }
  }

  function openCandidateDrawerById(applicationId) {
    var drawerEl = document.getElementById("recCandidateDrawer");
    var body = document.getElementById("recCandidateDrawerBody");
    if (!drawerEl || !body || !window.bootstrap || !applicationId) return;
    var url = templateUrl(detailTemplate, applicationId);
    if (!url) return;
    body.innerHTML = '<div class="text-center py-4 text-muted">Loading profile…</div>';
    bootstrap.Offcanvas.getOrCreateInstance(drawerEl).show();
    fetch(url, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success || !payload.data) throw new Error(payload.error || "Unable to load profile.");
        body.innerHTML = renderDrawerContent(payload.data);
        bindDrawerActions();
      })
      .catch(function (err) {
        body.innerHTML = '<p class="text-danger">' + escapeHtml(err.message) + "</p>";
      });
  }

  function openCandidateDrawer(card) {
    var appId = card.getAttribute("data-application-id");
    if (appId) {
      openCandidateDrawerById(appId);
      return;
    }
  }

  function bindViewCandidateButtons() {
    document.querySelectorAll(".rec-view-candidate").forEach(function (btn) {
      if (btn._viewBound) return;
      btn._viewBound = true;
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        openCandidateDrawerById(btn.getAttribute("data-application-id"));
      });
    });
  }

  function bindInterviewActions() {
    document.querySelectorAll(".rec-interview-cancel").forEach(function (btn) {
      if (btn._cancelBound) return;
      btn._cancelBound = true;
      btn.addEventListener("click", async function () {
        var ok = await confirmAction({
          title: "Cancel Interview",
          message: "Are you sure you want to cancel this interview?",
          confirmText: "Cancel Interview",
          cancelText: "Keep Interview",
          variant: "warning",
        });
        if (!ok) return;
        var url = btn.getAttribute("data-url");
        btn.disabled = true;
        postJson(url, "POST", { reason: "Cancelled from dashboard." })
          .then(function (body) {
            if (!body.success) throw new Error(body.error || "Unable to cancel.");
            notify("success", body.message || "Interview cancelled.");
            refreshDashboard(true);
          })
          .catch(function (err) {
            notify("error", err.message);
            btn.disabled = false;
          });
      });
    });
    document.querySelectorAll(".rec-interview-reschedule").forEach(function (btn) {
      if (btn._reschedBound) return;
      btn._reschedBound = true;
      btn.addEventListener("click", async function () {
        var current = btn.getAttribute("data-scheduled") || "";
        var value = await promptAction({
          title: "Reschedule Interview",
          message: "Enter new date and time in YYYY-MM-DDTHH:MM format.",
          placeholder: "YYYY-MM-DDTHH:MM",
          defaultValue: current.slice(0, 16),
          confirmText: "Reschedule",
          cancelText: "Cancel",
          variant: "info",
        });
        if (!value) return;
        var url = btn.getAttribute("data-url");
        btn.disabled = true;
        postJson(url, "PATCH", { scheduled_at: value })
          .then(function (body) {
            if (!body.success) throw new Error(body.error || "Unable to reschedule.");
            notify("success", body.message || "Interview rescheduled.");
            refreshDashboard(true);
          })
          .catch(function (err) {
            notify("error", err.message);
            btn.disabled = false;
          });
      });
    });
  }

  function bindJobActions() {
    var handlers = [
      { sel: ".rec-job-publish", confirmMsg: null },
      { sel: ".rec-job-close", confirmMsg: "Close hiring for this job?" },
      { sel: ".rec-job-pause", confirmMsg: "Pause hiring for this job?" },
      { sel: ".rec-job-duplicate", confirmMsg: null },
      { sel: ".rec-job-delete", confirmMsg: "Delete this job permanently?" },
    ];
    handlers.forEach(function (cfg) {
      document.querySelectorAll(cfg.sel).forEach(function (btn) {
        if (btn._jobBound) return;
        btn._jobBound = true;
        btn.addEventListener("click", async function () {
          if (cfg.confirmMsg) {
            var ok = await confirmAction({
              title: "Confirm Job Action",
              message: cfg.confirmMsg,
              confirmText: "Continue",
              cancelText: "Cancel",
              variant: cfg.sel === ".rec-job-delete" ? "danger" : "warning",
            });
            if (!ok) return;
          }
          var url = btn.getAttribute("data-url");
          if (!url) return;
          btn.disabled = true;
          postJson(url, "POST")
            .then(function (body) {
              if (!body.success) throw new Error(body.error || "Action failed.");
              notify("success", body.message || "Job updated.");
              refreshDashboard(true);
            })
            .catch(function (err) {
              notify("error", err.message);
              btn.disabled = false;
            });
        });
      });
    });
  }

  function bindBentoPress() {
    document.querySelectorAll(".rcd-bento--press").forEach(function (card) {
      card.addEventListener("mousedown", function () {
        card.style.transform = "scale(0.98)";
      });
      card.addEventListener("mouseup mouseleave", function () {
        card.style.transform = "";
      });
    });
  }

  function bindDashboardRefresh() {
    var page = document.getElementById("recDashboardPage");
    if (!page || !page.getAttribute("data-insights-url")) return;
    refreshDashboard(false);
    pollTimer = window.setInterval(function () {
      refreshDashboard(true);
    }, 45000);
  }

  document.addEventListener("DOMContentLoaded", function () {
    apiTemplatesFromPage();
    bindBentoPress();
    bindFilters();
    bindPipelineSearch();
    bindPipelineDragDrop();
    bindJobActions();
    bindInterviewActions();
    bindViewCandidateButtons();
    if (window.RecAnalyticsSection) {
      window.RecAnalyticsSection.bindPeriods(refreshAnalyticsPeriod);
      window.RecAnalyticsSection.bindExport();
    }
    bindDashboardRefresh();
  });
})();
