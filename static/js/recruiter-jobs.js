(function () {
  "use strict";

  function csrf() {
    if (window.REC_PORTAL && window.REC_PORTAL.csrfToken) return window.REC_PORTAL.csrfToken;
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
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

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function templateUrl(template, id) {
    if (!template || !id) return "";
    return template.replace("00000000-0000-0000-0000-000000000000", id);
  }

  function parseResponse(res) {
    return res.json().then(function (body) {
      if (!res.ok || body.success === false) {
        throw new Error(body.error || body.message || "Request failed.");
      }
      return body;
    });
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(payload || {}),
    }).then(parseResponse);
  }

  function patchJson(url, payload) {
    return fetch(url, {
      method: "PATCH",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(payload || {}),
    }).then(parseResponse);
  }

  var root;
  var templates = {};
  var applicantsState = { jobId: "", url: "", page: 1, q: "", status: "" };
  var interviewState = { url: "", appName: "" };
  var pollTimer;

  function readTemplates() {
    if (!root) return;
    templates = {
      list: root.getAttribute("data-api-list") || "",
      publish: root.getAttribute("data-publish-template") || "",
      close: root.getAttribute("data-close-template") || "",
      pause: root.getAttribute("data-pause-template") || "",
      reopen: root.getAttribute("data-reopen-template") || "",
      duplicate: root.getAttribute("data-duplicate-template") || "",
      archive: root.getAttribute("data-archive-template") || "",
      delete: root.getAttribute("data-delete-template") || "",
      applicants: root.getAttribute("data-applicants-template") || "",
      status: root.getAttribute("data-status-template") || "",
      notes: root.getAttribute("data-notes-template") || "",
      resume: root.getAttribute("data-resume-template") || "",
      detail: root.getAttribute("data-detail-template") || "",
      interview: root.getAttribute("data-interview-template") || "",
    };
  }

  function bindJobActions(container) {
    var scope = container || document;
    var handlers = [
      { sel: ".rec-job-publish", confirmMsg: null },
      { sel: ".rec-job-close", confirmMsg: "Close hiring for this job?" },
      { sel: ".rec-job-pause", confirmMsg: "Pause hiring for this job?" },
      { sel: ".rec-job-reopen", confirmMsg: "Reopen and publish this job?" },
      { sel: ".rec-job-duplicate", confirmMsg: null },
      { sel: ".rec-job-archive", confirmMsg: "Archive this job?" },
      { sel: ".rec-job-delete", confirmMsg: "Delete this job permanently? This cannot be undone." },
    ];
    handlers.forEach(function (cfg) {
      scope.querySelectorAll(cfg.sel).forEach(function (btn) {
        if (btn._jobBound) return;
        btn._jobBound = true;
        btn.addEventListener("click", async function (e) {
          e.preventDefault();
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
          postJson(url)
            .then(function (body) {
              notify("success", body.message || "Job updated.");
              refreshJobs(true);
            })
            .catch(function (err) {
              notify("error", err.message);
              btn.disabled = false;
            });
        });
      });
    });
  }

  function bindViewApplicants(container) {
    var scope = container || document;
    scope.querySelectorAll(".rec-view-applicants").forEach(function (btn) {
      if (btn._appsBound) return;
      btn._appsBound = true;
      btn.addEventListener("click", function () {
        openApplicantsPanel(
          btn.getAttribute("data-job-id"),
          btn.getAttribute("data-job-title"),
          btn.getAttribute("data-applicants-url")
        );
      });
    });
  }

  function openApplicantsPanel(jobId, jobTitle, url) {
    applicantsState = { jobId: jobId, url: url, page: 1, q: "", status: "" };
    var titleEl = document.getElementById("recApplicantsJobTitle");
    if (titleEl) titleEl.textContent = jobTitle || "";
    var searchEl = document.getElementById("recApplicantsSearch");
    var statusEl = document.getElementById("recApplicantsStatusFilter");
    if (searchEl) searchEl.value = "";
    if (statusEl) statusEl.value = "";
    var panel = document.getElementById("recApplicantsPanel");
    if (panel && window.bootstrap) {
      bootstrap.Offcanvas.getOrCreateInstance(panel).show();
    }
    loadApplicants();
  }

  function loadApplicants() {
    var listEl = document.getElementById("recApplicantsList");
    var emptyEl = document.getElementById("recApplicantsEmpty");
    var loadingEl = document.getElementById("recApplicantsLoading");
    if (!listEl || !applicantsState.url) return;
    if (loadingEl) loadingEl.hidden = false;
    if (emptyEl) emptyEl.hidden = true;
    listEl.innerHTML = "";

    var url = new URL(applicantsState.url, window.location.origin);
    if (applicantsState.q) url.searchParams.set("q", applicantsState.q);
    if (applicantsState.status) url.searchParams.set("status", applicantsState.status);
    url.searchParams.set("page", String(applicantsState.page));

    fetch(url.toString(), { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (loadingEl) loadingEl.hidden = true;
        var apps = payload.applications || [];
        if (!apps.length) {
          if (emptyEl) emptyEl.hidden = false;
          return;
        }
        listEl.innerHTML = apps.map(renderApplicantRow).join("");
        bindApplicantRowActions(listEl);
      })
      .catch(function (err) {
        if (loadingEl) loadingEl.hidden = true;
        listEl.innerHTML = '<p class="text-danger p-3">' + escapeHtml(err.message) + "</p>";
      });
  }

  function renderApplicantRow(app) {
    var avatar = app.photo_url
      ? '<img src="' + escapeHtml(app.photo_url) + '" alt="" class="rcd-applicant-row__photo">'
      : '<span class="rcd-pipeline-card__avatar"><span>' + escapeHtml(app.initials) + "</span></span>";
    var resumeBadge = app.has_resume
      ? '<span class="rcd-applicant-row__resume-badge" title="Resume available"><span class="material-symbols-outlined">description</span></span>'
      : "";
    return (
      '<article class="rcd-applicant-row" data-application-id="' +
      escapeHtml(app.id) +
      '">' +
      '<div class="rcd-applicant-row__main">' +
      avatar +
      '<div class="rcd-applicant-row__info">' +
      "<strong>" +
      escapeHtml(app.applicant_name) +
      "</strong>" +
      resumeBadge +
      '<span class="text-muted small d-block">' +
      escapeHtml(app.email) +
      "</span>" +
      '<span class="text-muted small">' +
      escapeHtml(app.skills_label) +
      "</span>" +
      "</div>" +
      '<span class="rcd-status-pill">' +
      escapeHtml(app.status_label) +
      "</span>" +
      "</div>" +
      '<div class="rcd-applicant-row__meta">' +
      "<span>Applied " +
      escapeHtml(app.applied_label) +
      "</span>" +
      "<span>" +
      escapeHtml(app.location) +
      "</span>" +
      "<span>" +
      escapeHtml(String(app.experience_years)) +
      " yrs</span>" +
      "</div>" +
      '<div class="rcd-applicant-row__actions">' +
      '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-view-profile" data-application-id="' +
      escapeHtml(app.id) +
      '">Profile</button>' +
      (app.has_resume
        ? '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-preview-resume" data-preview-url="' +
          escapeHtml(app.resume_preview_url) +
          '" data-download-url="' +
          escapeHtml(app.resume_url) +
          '">Resume</button>'
        : "") +
      '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-shortlist" data-url="' +
      escapeHtml(app.status_url) +
      '">Shortlist</button>' +
      '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-reject" data-url="' +
      escapeHtml(app.status_url) +
      '">Reject</button>' +
      '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs rec-schedule-interview" data-url="' +
      escapeHtml(app.interview_schedule_url) +
      '" data-name="' +
      escapeHtml(app.applicant_name) +
      '">Interview</button>' +
      "</div></article>"
    );
  }

  function bindApplicantRowActions(container) {
    container.querySelectorAll(".rec-view-profile").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openCandidateDrawer(btn.getAttribute("data-application-id"));
      });
    });
    container.querySelectorAll(".rec-preview-resume").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openResumePreview(btn.getAttribute("data-preview-url"), btn.getAttribute("data-download-url"));
      });
    });
    container.querySelectorAll(".rec-shortlist").forEach(function (btn) {
      btn.addEventListener("click", function () {
        updateApplicationStatus(btn.getAttribute("data-url"), "shortlisted", btn);
      });
    });
    container.querySelectorAll(".rec-reject").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var ok = await confirmAction({
          title: "Reject Candidate",
          message: "Are you sure you want to reject this candidate?",
          confirmText: "Reject Candidate",
          cancelText: "Cancel",
          variant: "danger",
        });
        if (!ok) return;
        updateApplicationStatus(btn.getAttribute("data-url"), "rejected", btn);
      });
    });
    container.querySelectorAll(".rec-schedule-interview").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openInterviewModal(btn.getAttribute("data-url"), btn.getAttribute("data-name"));
      });
    });
  }

  function updateApplicationStatus(url, status, btn) {
    if (!url) return;
    if (btn) btn.disabled = true;
    patchJson(url, { status: status, notes: "" })
      .then(function (body) {
        notify("success", body.message || "Status updated.");
        loadApplicants();
        refreshJobs(true);
      })
      .catch(function (err) {
        notify("error", err.message);
        if (btn) btn.disabled = false;
      });
  }

  function openCandidateDrawer(applicationId) {
    var drawerEl = document.getElementById("recCandidateDrawer");
    var body = document.getElementById("recCandidateDrawerBody");
    if (!drawerEl || !body || !applicationId) return;
    var url = templateUrl(templates.detail, applicationId);
    body.innerHTML = '<div class="text-center py-4 text-muted">Loading profile…</div>';
    if (window.bootstrap) bootstrap.Offcanvas.getOrCreateInstance(drawerEl).show();
    fetch(url, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.data) throw new Error(payload.error || "Unable to load profile.");
        body.innerHTML = renderDrawerContent(payload.data);
        bindDrawerActions(body);
      })
      .catch(function (err) {
        body.innerHTML = '<p class="text-danger">' + escapeHtml(err.message) + "</p>";
      });
  }

  function renderDrawerContent(app) {
    var avatar = app.photo_url
      ? '<img src="' + escapeHtml(app.photo_url) + '" alt="" class="rcd-drawer-profile__photo">'
      : '<div class="rcd-pipeline-card__avatar"><span>' + escapeHtml(app.initials) + "</span></div>";
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
    var resumeActions = app.has_resume
      ? '<button type="button" class="rcd-btn rcd-btn--outline rcd-btn--sm rec-preview-resume" data-preview-url="' +
        escapeHtml(app.resume_preview_url) +
        '" data-download-url="' +
        escapeHtml(app.resume_url) +
        '">Preview Resume</button>' +
        '<a href="' +
        escapeHtml(app.resume_url) +
        '" class="rcd-btn rcd-btn--soft rcd-btn--sm" download>Download</a>'
      : '<span class="text-muted small">No resume uploaded</span>';
    var experiences = (app.experiences || [])
      .map(function (exp) {
        return "<li>" + escapeHtml(exp.title) + " at " + escapeHtml(exp.company) + "</li>";
      })
      .join("");
    var education = (app.education_rows || [])
      .map(function (edu) {
        return "<li>" + escapeHtml(edu.degree) + " — " + escapeHtml(edu.institution) + "</li>";
      })
      .join("");
    var skills = (app.skills || []).map(function (s) {
      return '<span class="rcd-skill-chip">' + escapeHtml(s) + "</span>";
    }).join("");
    var links = [];
    if (app.linkedin_url) links.push('<a href="' + escapeHtml(app.linkedin_url) + '" target="_blank" rel="noopener">LinkedIn</a>');
    if (app.github_url) links.push('<a href="' + escapeHtml(app.github_url) + '" target="_blank" rel="noopener">GitHub</a>');
    if (app.portfolio_url) links.push('<a href="' + escapeHtml(app.portfolio_url) + '" target="_blank" rel="noopener">Portfolio</a>');

    return (
      '<div class="rcd-drawer-profile">' +
      '<div class="rcd-drawer-profile__head">' +
      avatar +
      "<div><h6 class=\"mb-0\">" +
      escapeHtml(app.applicant_name) +
      "</h6><p class=\"text-muted mb-0 small\">" +
      escapeHtml(app.headline || app.job_title) +
      "</p></div></div>" +
      '<span class="rcd-status-pill mb-3 d-inline-block">' +
      escapeHtml(app.status_label) +
      "</span>" +
      '<section class="rcd-drawer-section"><h6>Personal</h6><dl class="rcd-drawer-meta">' +
      "<dt>Email</dt><dd>" + escapeHtml(app.email) + "</dd>" +
      "<dt>Phone</dt><dd>" + escapeHtml(app.phone || "—") + "</dd>" +
      "<dt>Location</dt><dd>" + escapeHtml(app.location) + "</dd>" +
      "<dt>Address</dt><dd>" + escapeHtml(app.address || "—") + "</dd></dl></section>" +
      '<section class="rcd-drawer-section"><h6>Professional</h6><dl class="rcd-drawer-meta">' +
      "<dt>Experience</dt><dd>" + escapeHtml(String(app.experience_years)) + " yrs</dd>" +
      "<dt>Current company</dt><dd>" + escapeHtml(app.current_company) + "</dd>" +
      "<dt>Education</dt><dd>" + escapeHtml(app.education) + "</dd></dl>" +
      (experiences ? "<ul class=\"small ps-3\">" + experiences + "</ul>" : "") +
      (skills ? '<div class="rcd-drawer-skills">' + skills + "</div>" : "") +
      (links.length ? '<p class="small mt-2">' + links.join(" · ") + "</p>" : "") +
      "</section>" +
      '<section class="rcd-drawer-section"><h6>Application</h6><dl class="rcd-drawer-meta">' +
      "<dt>Applied</dt><dd>" + escapeHtml(app.applied_label) + "</dd>" +
      "<dt>Job</dt><dd>" + escapeHtml(app.applied_job || app.job_title) + "</dd>" +
      "<dt>Stage</dt><dd>" + escapeHtml(app.current_stage || app.status_label) + "</dd></dl>" +
      statusSelect +
      '<label class="form-label small mt-2">Recruiter notes</label>' +
      '<textarea class="form-control form-control-sm rec-drawer-notes" rows="3" data-url="' +
      escapeHtml(app.notes_url) +
      '">' +
      escapeHtml(app.recruiter_notes || "") +
      "</textarea>" +
      '<div class="d-flex flex-wrap gap-2 mt-3">' +
      resumeActions +
      '<button type="button" class="rcd-btn rcd-btn--primary rcd-btn--sm rec-drawer-notes-save">Save Notes</button>' +
      '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--sm rec-schedule-interview" data-url="' +
      escapeHtml(app.interview_schedule_url) +
      '" data-name="' +
      escapeHtml(app.applicant_name) +
      '">Schedule Interview</button>' +
      "</div></div>"
    );
  }

  function bindDrawerActions(body) {
    var statusEl = body.querySelector(".rec-drawer-status");
    if (statusEl && !statusEl._bound) {
      statusEl._bound = true;
      statusEl.addEventListener("change", function () {
        var status = statusEl.value;
        if (!status) return;
        patchJson(statusEl.getAttribute("data-url"), { status: status, notes: "" })
          .then(function () {
            notify("success", "Status updated.");
            loadApplicants();
            refreshJobs(true);
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
        patchJson(textarea.getAttribute("data-url"), { recruiter_notes: textarea.value.trim() })
          .then(function (body) {
            notify("success", body.message || "Notes saved.");
          })
          .catch(function (err) {
            notify("error", err.message);
          });
      });
    }
    body.querySelectorAll(".rec-preview-resume").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openResumePreview(btn.getAttribute("data-preview-url"), btn.getAttribute("data-download-url"));
      });
    });
    body.querySelectorAll(".rec-schedule-interview").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openInterviewModal(btn.getAttribute("data-url"), btn.getAttribute("data-name"));
      });
    });
  }

  function openResumePreview(previewUrl, downloadUrl) {
    var modalEl = document.getElementById("recResumeModal");
    var frame = document.getElementById("recResumeFrame");
    var download = document.getElementById("recResumeDownload");
    var openTab = document.getElementById("recResumeOpenTab");
    if (!modalEl || !frame || !previewUrl) return;
    frame.src = previewUrl;
    if (download) download.href = downloadUrl || previewUrl.replace("preview=1", "");
    if (openTab) openTab.href = previewUrl;
    if (window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function bindResumePrint() {
    var btn = document.getElementById("recResumePrint");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var frame = document.getElementById("recResumeFrame");
      if (frame && frame.contentWindow) frame.contentWindow.print();
    });
  }

  function openInterviewModal(url, name) {
    interviewState = { url: url, appName: name || "" };
    var nameEl = document.getElementById("recInterviewCandidateName");
    if (nameEl) nameEl.textContent = name || "—";
    var errEl = document.getElementById("recInterviewError");
    if (errEl) errEl.hidden = true;
    var modalEl = document.getElementById("recInterviewModal");
    if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function bindInterviewModal() {
    var modeEl = document.getElementById("recInterviewMode");
    var meetWrap = document.getElementById("recInterviewMeetWrap");
    var locWrap = document.getElementById("recInterviewLocationWrap");
    if (modeEl) {
      modeEl.addEventListener("change", function () {
        var online = modeEl.value === "online";
        if (meetWrap) meetWrap.hidden = !online;
        if (locWrap) locWrap.hidden = online;
      });
    }
    var submit = document.getElementById("recInterviewSubmit");
    if (!submit) return;
    submit.addEventListener("click", function () {
      var date = document.getElementById("recInterviewDate").value;
      var time = document.getElementById("recInterviewTime").value;
      var errEl = document.getElementById("recInterviewError");
      if (!date || !time) {
        if (errEl) {
          errEl.textContent = "Date and time are required.";
          errEl.hidden = false;
        }
        return;
      }
      submit.disabled = true;
      postJson(interviewState.url, {
        scheduled_at: date + "T" + time + ":00",
        mode: document.getElementById("recInterviewMode").value,
        meet_url: document.getElementById("recInterviewMeet").value.trim(),
        location: document.getElementById("recInterviewLocation").value.trim(),
        interview_type: document.getElementById("recInterviewType").value.trim(),
        notes: document.getElementById("recInterviewNotes").value.trim(),
      })
        .then(function (body) {
          notify("success", body.message || "Interview scheduled.");
          var modalEl = document.getElementById("recInterviewModal");
          if (modalEl && window.bootstrap) bootstrap.Modal.getInstance(modalEl).hide();
          loadApplicants();
          refreshJobs(true);
        })
        .catch(function (err) {
          if (errEl) {
            errEl.textContent = err.message;
            errEl.hidden = false;
          }
        })
        .finally(function () {
          submit.disabled = false;
        });
    });
  }

  function bindApplicantFilters() {
    var searchEl = document.getElementById("recApplicantsSearch");
    var statusEl = document.getElementById("recApplicantsStatusFilter");
    var debounce;
    if (searchEl) {
      searchEl.addEventListener("input", function () {
        clearTimeout(debounce);
        debounce = setTimeout(function () {
          applicantsState.q = searchEl.value.trim();
          applicantsState.page = 1;
          loadApplicants();
        }, 350);
      });
    }
    if (statusEl) {
      statusEl.addEventListener("change", function () {
        applicantsState.status = statusEl.value;
        applicantsState.page = 1;
        loadApplicants();
      });
    }
  }

  function refreshJobs(silent) {
    if (!root || !templates.list) return;
    var skeleton = document.getElementById("recJobsSkeleton");
    var wrap = document.getElementById("recJobsTableWrap");
    if (!silent && skeleton) skeleton.hidden = false;
    if (!silent && wrap) wrap.style.opacity = "0.55";

    var url = new URL(templates.list, window.location.origin);
    var status = root.getAttribute("data-current-status") || "";
    var q = root.getAttribute("data-current-q") || "";
    var page = root.getAttribute("data-current-page") || "1";
    if (status) url.searchParams.set("status", status);
    if (q) url.searchParams.set("q", q);
    url.searchParams.set("page", page);

    fetch(url.toString(), { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.data) return;
        updateStats(payload.data.stats);
      })
      .catch(function () {})
      .finally(function () {
        if (skeleton) skeleton.hidden = true;
        if (wrap) wrap.style.opacity = "";
      });
  }

  function updateStats(stats) {
    if (!stats) return;
    Object.keys(stats).forEach(function (key) {
      var el = document.querySelector('[data-stat="' + key + '"]');
      if (el) el.textContent = stats[key];
    });
  }

  function bindCreatedToast() {
    if (window.location.search.indexOf("created=1") !== -1) {
      notify("success", "Job draft created successfully.");
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, "", window.location.pathname + window.location.hash);
      }
    }
  }

  function bindPolling() {
    pollTimer = window.setInterval(function () {
      refreshJobs(true);
    }, 45000);
  }

  document.addEventListener("DOMContentLoaded", function () {
    root = document.getElementById("recJobsPage");
    if (!root) return;
    readTemplates();
    bindCreatedToast();
    bindJobActions();
    bindViewApplicants();
    bindApplicantFilters();
    bindInterviewModal();
    bindResumePrint();
    bindPolling();
  });
})();
