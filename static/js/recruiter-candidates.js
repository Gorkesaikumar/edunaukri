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
  var resumeZoom = 1;
  var notesState = { url: "", name: "" };
  var interviewState = { url: "", name: "" };
  var pollTimer;

  function readTemplates() {
    if (!root) return;
    templates = {
      list: root.getAttribute("data-api-list") || "",
      status: root.getAttribute("data-status-template") || "",
      notes: root.getAttribute("data-notes-template") || "",
      resume: root.getAttribute("data-resume-template") || "",
      detail: root.getAttribute("data-detail-template") || "",
      interview: root.getAttribute("data-interview-template") || "",
      messages: root.getAttribute("data-messages-url") || "",
    };
  }

  function appDataFromBtn(btn) {
    var menuBtn = btn.closest(".rcd-applicant-actions").querySelector(".rec-applicant-actions-btn");
    if (!menuBtn) return null;
    return {
      id: menuBtn.getAttribute("data-app-id"),
      name: menuBtn.getAttribute("data-app-name") || "",
      job: menuBtn.getAttribute("data-app-job") || "",
      hasResume: menuBtn.getAttribute("data-has-resume") === "1",
      statusUrl: menuBtn.getAttribute("data-status-url"),
      notesUrl: menuBtn.getAttribute("data-notes-url"),
      resumeUrl: menuBtn.getAttribute("data-resume-url"),
      resumePreviewUrl: menuBtn.getAttribute("data-resume-preview-url"),
      detailUrl: menuBtn.getAttribute("data-detail-url"),
      interviewUrl: menuBtn.getAttribute("data-interview-url"),
      emailUrl: menuBtn.getAttribute("data-email-url"),
      messagesUrl: menuBtn.getAttribute("data-messages-url"),
    };
  }

  function bindActionMenus(container) {
    var scope = container || document;
    scope.querySelectorAll(".rcd-applicant-actions").forEach(function (dropdown) {
      if (dropdown._bound) return;
      dropdown._bound = true;

      dropdown.querySelector(".rec-action-profile").addEventListener("click", function (e) {
        e.preventDefault();
        var app = appDataFromBtn(e.target);
        if (app) openCandidateDrawer(app.id);
      });

      dropdown.querySelector(".rec-action-resume").addEventListener("click", function (e) {
        e.preventDefault();
        var app = appDataFromBtn(e.target);
        if (app) openResumeModal(app);
      });

      dropdown.querySelector(".rec-action-download").addEventListener("click", function (e) {
        e.preventDefault();
        var app = appDataFromBtn(e.target);
        if (!app || !app.hasResume) {
          notify("error", "No resume available.");
          return;
        }
        window.location.href = app.resumeUrl;
      });

      dropdown.querySelector(".rec-action-shortlist").addEventListener("click", function (e) {
        e.preventDefault();
        var app = appDataFromBtn(e.target);
        if (app) updateStatus(app.statusUrl, "shortlisted");
      });

      dropdown.querySelector(".rec-action-reject").addEventListener("click", async function (e) {
        e.preventDefault();
        var app = appDataFromBtn(e.target);
        if (!app) return;
        var ok = await confirmAction({
          title: "Reject Candidate",
          message: "Are you sure you want to reject this candidate?",
          confirmText: "Reject Candidate",
          cancelText: "Cancel",
          variant: "danger",
        });
        if (!ok) return;
        updateStatus(app.statusUrl, "rejected");
      });

      dropdown.querySelector(".rec-action-interview").addEventListener("click", function (e) {
        e.preventDefault();
        var app = appDataFromBtn(e.target);
        if (app) openInterviewModal(app.interviewUrl, app.name);
      });

      dropdown.querySelector(".rec-action-next").addEventListener("click", function (e) {
        e.preventDefault();
        var app = appDataFromBtn(e.target);
        if (!app) return;
        openCandidateDrawer(app.id);
      });

      dropdown.querySelector(".rec-action-notes").addEventListener("click", function (e) {
        e.preventDefault();
        var app = appDataFromBtn(e.target);
        if (app) openNotesModal(app.notesUrl, app.name);
      });
    });
  }

  function updateStatus(url, status) {
    if (!url || !status) return;
    patchJson(url, { status: status, notes: "" })
      .then(function (body) {
        notify("success", body.message || "Status updated.");
        refreshApplicants(true);
      })
      .catch(function (err) {
        notify("error", err.message);
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
        ? '<label class="form-label small">Update status</label><select class="form-select form-select-sm rec-drawer-status" data-url="' +
          escapeHtml(app.status_url) +
          '"><option value="">Select status…</option>' +
          statusOptions +
          "</select>"
        : "";
    var resumeActions = app.has_resume
      ? '<button type="button" class="rcd-btn rcd-btn--outline rcd-btn--sm rec-drawer-preview-resume" data-name="' +
        escapeHtml(app.applicant_name) +
        '" data-job="' +
        escapeHtml(app.job_title) +
        '" data-preview="' +
        escapeHtml(app.resume_preview_url) +
        '" data-download="' +
        escapeHtml(app.resume_url) +
        '">View Resume</button>'
      : '<span class="text-muted small">No resume uploaded</span>';
    var skills = (app.skills || [])
      .map(function (s) {
        return '<span class="rcd-skill-chip">' + escapeHtml(s) + "</span>";
      })
      .join("");
    var links = [];
    if (app.linkedin_url) links.push('<a href="' + escapeHtml(app.linkedin_url) + '" target="_blank" rel="noopener">LinkedIn</a>');
    if (app.github_url) links.push('<a href="' + escapeHtml(app.github_url) + '" target="_blank" rel="noopener">GitHub</a>');
    if (app.portfolio_url) links.push('<a href="' + escapeHtml(app.portfolio_url) + '" target="_blank" rel="noopener">Portfolio</a>');

    return (
      '<div class="rcd-drawer-profile">' +
      '<div class="rcd-drawer-profile__head">' +
      avatar +
      '<div><h6 class="mb-0">' +
      escapeHtml(app.applicant_name) +
      '</h6><p class="text-muted mb-0 small">' +
      escapeHtml(app.headline || app.job_title) +
      "</p></div></div>" +
      '<span class="rcd-status-pill rcd-status-pill--' +
      escapeHtml(app.status_tone || "primary") +
      ' mb-3 d-inline-block">' +
      escapeHtml(app.stage_label || app.status_label) +
      "</span>" +
      '<section class="rcd-drawer-section"><h6>Personal</h6><dl class="rcd-drawer-meta">' +
      "<dt>Email</dt><dd>" +
      escapeHtml(app.email) +
      "</dd><dt>Phone</dt><dd>" +
      escapeHtml(app.phone || "—") +
      "</dd><dt>Address</dt><dd>" +
      escapeHtml(app.address || app.location) +
      "</dd></dl></section>" +
      '<section class="rcd-drawer-section"><h6>Professional</h6><dl class="rcd-drawer-meta">' +
      "<dt>Experience</dt><dd>" +
      escapeHtml(String(app.experience_years)) +
      " yrs</dd><dt>Company</dt><dd>" +
      escapeHtml(app.current_company) +
      "</dd><dt>Education</dt><dd>" +
      escapeHtml(app.education) +
      "</dd></dl>" +
      (skills ? '<div class="rcd-drawer-skills">' + skills + "</div>" : "") +
      (links.length ? '<p class="small mt-2">' + links.join(" · ") + "</p>" : "") +
      "</section>" +
      (app.cover_letter ? '<section class="rcd-drawer-section"><h6>Cover Letter</h6><div class="small text-muted" style="white-space: pre-wrap;">' + escapeHtml(app.cover_letter) + '</div></section>' : '') +
      '<section class="rcd-drawer-section"><h6>Application</h6><dl class="rcd-drawer-meta">' +
      "<dt>Job</dt><dd>" +
      escapeHtml(app.applied_job || app.job_title) +
      "</dd><dt>Applied</dt><dd>" +
      escapeHtml(app.applied_label) +
      "</dd><dt>Stage</dt><dd>" +
      escapeHtml(app.current_stage || app.status_label) +
      "</dd></dl>" +
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
      '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--sm rec-drawer-schedule" data-url="' +
      escapeHtml(app.interview_schedule_url) +
      '" data-name="' +
      escapeHtml(app.applicant_name) +
      '">Schedule Interview</button></div></div>"
    );
  }

  function bindDrawerActions(body) {
    var statusEl = body.querySelector(".rec-drawer-status");
    if (statusEl) {
      statusEl.addEventListener("change", function () {
        if (!statusEl.value) return;
        patchJson(statusEl.getAttribute("data-url"), { status: statusEl.value, notes: "" })
          .then(function () {
            notify("success", "Status updated.");
            refreshApplicants(true);
          })
          .catch(function (err) {
            notify("error", err.message);
            statusEl.value = "";
          });
      });
    }
    var saveBtn = body.querySelector(".rec-drawer-notes-save");
    if (saveBtn) {
      saveBtn.addEventListener("click", function () {
        var textarea = body.querySelector(".rec-drawer-notes");
        patchJson(textarea.getAttribute("data-url"), { recruiter_notes: textarea.value.trim() })
          .then(function (body) {
            notify("success", body.message || "Notes saved.");
          })
          .catch(function (err) {
            notify("error", err.message);
          });
      });
    }
    var previewBtn = body.querySelector(".rec-drawer-preview-resume");
    if (previewBtn) {
      previewBtn.addEventListener("click", function () {
        openResumeModal({
          name: previewBtn.getAttribute("data-name"),
          job: previewBtn.getAttribute("data-job"),
          hasResume: true,
          resumePreviewUrl: previewBtn.getAttribute("data-preview"),
          resumeUrl: previewBtn.getAttribute("data-download"),
        });
      });
    }
    var schedBtn = body.querySelector(".rec-drawer-schedule");
    if (schedBtn) {
      schedBtn.addEventListener("click", function () {
        openInterviewModal(schedBtn.getAttribute("data-url"), schedBtn.getAttribute("data-name"));
      });
    }
  }

  function openResumeModal(app) {
    var modalEl = document.getElementById("recResumeModal");
    var frame = document.getElementById("recResumeFrame");
    var empty = document.getElementById("recResumeEmpty");
    var viewport = document.getElementById("recResumeViewport");
    var toolbar = document.getElementById("recResumeToolbar");
    var title = document.getElementById("recResumeModalTitle");
    var jobEl = document.getElementById("recResumeModalJob");
    var download = document.getElementById("recResumeDownload");
    if (!modalEl) return;

    if (title) title.textContent = app.name || "Resume";
    if (jobEl) jobEl.textContent = app.job ? "Applied for " + app.job : "";

    if (!app.hasResume) {
      if (empty) empty.hidden = false;
      if (viewport) viewport.hidden = true;
      if (toolbar) toolbar.hidden = true;
      if (frame) frame.src = "about:blank";
    } else {
      if (empty) empty.hidden = true;
      if (viewport) viewport.hidden = false;
      if (toolbar) toolbar.hidden = false;
      resumeZoom = 1;
      applyResumeZoom();
      if (frame) frame.src = app.resumePreviewUrl || app.resumeUrl + "?preview=1";
      if (download) download.href = app.resumeUrl;
    }
    if (window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function applyResumeZoom() {
    var frame = document.getElementById("recResumeFrame");
    if (frame) {
      frame.style.transform = "scale(" + resumeZoom + ")";
      frame.style.transformOrigin = "top center";
      frame.style.height = Math.min(95 / resumeZoom, 95) + "vh";
    }
  }

  function bindResumeControls() {
    var zoomIn = document.getElementById("recResumeZoomIn");
    var zoomOut = document.getElementById("recResumeZoomOut");
    var printBtn = document.getElementById("recResumePrint");
    var fsBtn = document.getElementById("recResumeFullscreen");
    if (zoomIn) {
      zoomIn.addEventListener("click", function () {
        resumeZoom = Math.min(2, resumeZoom + 0.15);
        applyResumeZoom();
      });
    }
    if (zoomOut) {
      zoomOut.addEventListener("click", function () {
        resumeZoom = Math.max(0.5, resumeZoom - 0.15);
        applyResumeZoom();
      });
    }
    if (printBtn) {
      printBtn.addEventListener("click", function () {
        var frame = document.getElementById("recResumeFrame");
        if (frame && frame.contentWindow) frame.contentWindow.print();
      });
    }
    if (fsBtn) {
      fsBtn.addEventListener("click", function () {
        var viewport = document.getElementById("recResumeViewport");
        if (viewport && viewport.requestFullscreen) viewport.requestFullscreen();
      });
    }
  }

  function openNotesModal(url, name) {
    notesState = { url: url, name: name || "" };
    var nameEl = document.getElementById("recNotesCandidateName");
    var textarea = document.getElementById("recNotesTextarea");
    var errEl = document.getElementById("recNotesError");
    if (nameEl) nameEl.textContent = name || "";
    if (textarea) textarea.value = "";
    if (errEl) errEl.hidden = true;
    var modalEl = document.getElementById("recNotesModal");
    if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function bindNotesModal() {
    var save = document.getElementById("recNotesSave");
    if (!save) return;
    save.addEventListener("click", function () {
      var textarea = document.getElementById("recNotesTextarea");
      var errEl = document.getElementById("recNotesError");
      save.disabled = true;
      patchJson(notesState.url, { recruiter_notes: textarea.value.trim() })
        .then(function (body) {
          notify("success", body.message || "Notes saved.");
          var modalEl = document.getElementById("recNotesModal");
          if (modalEl && window.bootstrap) bootstrap.Modal.getInstance(modalEl).hide();
        })
        .catch(function (err) {
          if (errEl) {
            errEl.textContent = err.message;
            errEl.hidden = false;
          }
        })
        .finally(function () {
          save.disabled = false;
        });
    });
  }

  function openInterviewModal(url, name) {
    interviewState = { url: url, name: name || "" };
    var nameEl = document.getElementById("recInterviewCandidateName");
    if (nameEl) nameEl.textContent = name || "—";
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
          refreshApplicants(true);
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

  function updateStats(analytics) {
    if (!analytics) return;
    analytics.forEach(function (stat) {
      var el = document.querySelector('[data-stat="' + stat.key + '"]');
      if (el) el.textContent = stat.value;
    });
  }

  function refreshApplicants(silent) {
    if (!root || !templates.list) return;
    var skeleton = document.getElementById("recApplicantsSkeleton");
    var wrap = document.getElementById("recApplicantsTableWrap");
    if (!silent && skeleton) skeleton.hidden = false;

    var url = new URL(templates.list, window.location.origin);
    var params = new URLSearchParams(window.location.search);
    params.forEach(function (value, key) {
      url.searchParams.set(key, value);
    });

    fetch(url.toString(), { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (payload.analytics) updateStats(payload.analytics);
      })
      .catch(function () {})
      .finally(function () {
        if (skeleton) skeleton.hidden = true;
      });
  }

  function bindPolling() {
    pollTimer = window.setInterval(function () {
      refreshApplicants(true);
    }, 45000);
  }

  document.addEventListener("DOMContentLoaded", function () {
    root = document.getElementById("recCandidatesPage");
    if (!root) return;
    readTemplates();
    bindActionMenus();
    bindResumeControls();
    bindNotesModal();
    bindInterviewModal();
    bindPolling();
  });
})();
