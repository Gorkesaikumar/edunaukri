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
  var pollTimer;
  var pipelineTotal = 11;
  var feedbackState = { url: "", name: "" };
  var rescheduleState = { url: "", name: "" };
  var whatsAppState = { phone: "", message: "" };
  var emailState = { email: "", subject: "", body: "" };
  var calMonth;
  var calEvents = [];

  function readTemplates() {
    if (!root) return;
    templates = {
      list: root.getAttribute("data-api-list") || "",
      schedule: root.getAttribute("data-schedule-template") || "",
      cancel: root.getAttribute("data-cancel-template") || "",
      reschedule: root.getAttribute("data-reschedule-template") || "",
      feedback: root.getAttribute("data-feedback-template") || "",
      status: root.getAttribute("data-status-template") || "",
      detail: root.getAttribute("data-detail-template") || "",
      appStatus: root.getAttribute("data-application-status-template") || "",
      resume: root.getAttribute("data-resume-template") || "",
    };
    pipelineTotal = parseInt(root.getAttribute("data-pipeline-total") || "11", 10);
    var calScript = document.getElementById("recCalendarEventsData");
    if (calScript) {
      try {
        calEvents = JSON.parse(calScript.textContent || "[]");
      } catch (e) {
        calEvents = [];
      }
    }
  }

  function btnData(btn) {
    var menuBtn = btn.closest(".rcd-interview-actions").querySelector(".rec-interview-actions-btn");
    if (!menuBtn) return null;
    return {
      interviewId: menuBtn.getAttribute("data-interview-id"),
      appId: menuBtn.getAttribute("data-app-id"),
      name: menuBtn.getAttribute("data-name") || "",
      job: menuBtn.getAttribute("data-job") || "",
      company: menuBtn.getAttribute("data-company") || "",
      email: menuBtn.getAttribute("data-email") || "",
      phone: menuBtn.getAttribute("data-phone") || "",
      hasResume: menuBtn.getAttribute("data-has-resume") === "1",
      resumeUrl: menuBtn.getAttribute("data-resume-url"),
      resumePreviewUrl: menuBtn.getAttribute("data-resume-preview-url"),
      detailUrl: menuBtn.getAttribute("data-detail-url"),
      meetUrl: menuBtn.getAttribute("data-meet-url") || "",
      location: menuBtn.getAttribute("data-location") || "",
      cancelUrl: menuBtn.getAttribute("data-cancel-url"),
      rescheduleUrl: menuBtn.getAttribute("data-reschedule-url"),
      feedbackUrl: menuBtn.getAttribute("data-feedback-url"),
      statusUrl: menuBtn.getAttribute("data-status-url"),
      appStatusUrl: menuBtn.getAttribute("data-app-status-url"),
      date: menuBtn.getAttribute("data-date") || "",
      time: menuBtn.getAttribute("data-time") || "",
      round: menuBtn.getAttribute("data-round") || "",
      mode: menuBtn.getAttribute("data-mode") || "",
      interviewer: menuBtn.getAttribute("data-interviewer") || "",
      canCancel: menuBtn.getAttribute("data-can-cancel") === "1",
      canReschedule: menuBtn.getAttribute("data-can-reschedule") === "1",
      canComplete: menuBtn.getAttribute("data-can-complete") === "1",
    };
  }

  function whatsappMessage(item) {
    var linkOrAddr = item.meetUrl || item.location || "TBD";
    return (
      "Hello " +
      item.name +
      ",\n\nYour interview for the position of " +
      item.job +
      " at " +
      item.company +
      " has been scheduled.\n\nInterview: " +
      item.round +
      " (" +
      item.mode +
      ")\nDate: " +
      item.date +
      "\nTime: " +
      item.time +
      "\nInterviewer: " +
      item.interviewer +
      "\nMeeting Link / Address: " +
      linkOrAddr +
      "\n\nPlease join on time.\n\nThank you,\n" +
      item.company
    );
  }

  function emailInvitation(item, reminder) {
    var prefix = reminder ? "Reminder: " : "";
    var linkOrAddr = item.meetUrl || item.location || "TBD";
    var subject = prefix + "Interview Invitation — " + item.job + " at " + item.company;
    var body =
      "Hello " +
      item.name +
      ",\n\n" +
      (reminder ? "This is a friendly reminder about your upcoming interview.\n\n" : "") +
      "Your interview for the position of " +
      item.job +
      " at " +
      item.company +
      " has been scheduled.\n\n" +
      "Interview: " +
      item.round +
      " (" +
      item.mode +
      ")\nDate: " +
      item.date +
      "\nTime: " +
      item.time +
      "\nInterviewer: " +
      item.interviewer +
      "\nMeeting Link / Address: " +
      linkOrAddr +
      "\n\nPlease join on time.\n\nThank you,\n" +
      item.company;
    return { subject: subject, body: body };
  }

  function normalizePhone(phone) {
    return String(phone || "").replace(/\D/g, "");
  }

  function bindActionMenus(container) {
    var scope = container || document;
    scope.querySelectorAll(".rcd-interview-actions").forEach(function (dropdown) {
      if (dropdown._bound) return;
      dropdown._bound = true;

      var map = {
        ".rec-int-action-profile": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (d) openCandidateDrawer(d.appId);
        },
        ".rec-int-action-resume": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (d) openResumeModal(d);
        },
        ".rec-int-action-download": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (!d || !d.hasResume) {
            notify("error", "No resume available.");
            return;
          }
          window.location.href = d.resumeUrl;
        },
        ".rec-int-action-edit": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (d) openRescheduleModal(d);
        },
        ".rec-int-action-cancel": async function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (!d || !d.canCancel) return;
          var ok = await confirmAction({
            title: "Cancel Interview",
            message: "Are you sure you want to cancel this interview?",
            confirmText: "Cancel Interview",
            cancelText: "Keep Interview",
            variant: "warning",
          });
          if (!ok) return;
          postJson(d.cancelUrl, { reason: "Cancelled by recruiter" })
            .then(function (body) {
              notify("success", body.message || "Interview cancelled.");
              refreshInterviews(true);
            })
            .catch(function (err) {
              notify("error", err.message);
            });
        },
        ".rec-int-action-complete": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (!d || !d.canComplete) return;
          patchJson(d.statusUrl, { status: "completed" })
            .then(function (body) {
              notify("success", body.message || "Interview marked completed.");
              refreshInterviews(true);
            })
            .catch(function (err) {
              notify("error", err.message);
            });
        },
        ".rec-int-action-feedback": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (d) openFeedbackModal(d);
        },
        ".rec-int-action-whatsapp": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (d) openWhatsAppModal(d);
        },
        ".rec-int-action-email": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (d) openEmailModal(d, false);
        },
        ".rec-int-action-reminder": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (d) openEmailModal(d, true);
        },
        ".rec-int-action-next": function (e) {
          e.preventDefault();
          var d = btnData(e.target);
          if (d) openCandidateDrawer(d.appId);
        },
      };

      Object.keys(map).forEach(function (sel) {
        var el = dropdown.querySelector(sel);
        if (el) el.addEventListener("click", map[sel]);
      });
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
        ? '<label class="form-label small">Update stage</label><select class="form-select form-select-sm rec-drawer-status" data-url="' +
          escapeHtml(app.status_url) +
          '"><option value="">Select stage…</option>' +
          statusOptions +
          "</select>"
        : "";
    var resumeActions = app.has_resume
      ? '<button type="button" class="rcd-btn rcd-btn--outline rcd-btn--sm rec-drawer-preview-resume" data-preview="' +
        escapeHtml(app.resume_preview_url) +
        '" data-download="' +
        escapeHtml(app.resume_url) +
        '" data-name="' +
        escapeHtml(app.applicant_name) +
        '">View Resume</button>'
      : '<span class="text-muted small">No resume uploaded</span>';

    return (
      '<div class="rcd-drawer-profile">' +
      '<div class="rcd-drawer-profile__head">' +
      avatar +
      '<div><h6 class="mb-0">' +
      escapeHtml(app.applicant_name) +
      '</h6><p class="text-muted mb-0 small">' +
      escapeHtml(app.job_title) +
      "</p></div></div>" +
      '<span class="rcd-status-pill rcd-status-pill--' +
      escapeHtml(app.status_tone || "primary") +
      ' mb-3 d-inline-block">' +
      escapeHtml(app.stage_label || app.status_label) +
      "</span>" +
      '<section class="rcd-drawer-section"><h6>Contact</h6><dl class="rcd-drawer-meta">' +
      "<dt>Email</dt><dd>" +
      escapeHtml(app.email) +
      "</dd><dt>Phone</dt><dd>" +
      escapeHtml(app.phone || "—") +
      "</dd></dl></section>" +
      '<section class="rcd-drawer-section"><h6>Application</h6><dl class="rcd-drawer-meta">' +
      "<dt>Job</dt><dd>" +
      escapeHtml(app.job_title) +
      "</dd><dt>Applied</dt><dd>" +
      escapeHtml(app.applied_label) +
      "</dd></dl>" +
      statusSelect +
      '<div class="d-flex flex-wrap gap-2 mt-3">' +
      resumeActions +
      "</div></div>"
    );
  }

  function bindDrawerActions(body) {
    var statusEl = body.querySelector(".rec-drawer-status");
    if (statusEl) {
      statusEl.addEventListener("change", function () {
        if (!statusEl.value) return;
        patchJson(statusEl.getAttribute("data-url"), { status: statusEl.value, notes: "" })
          .then(function () {
            notify("success", "Stage updated.");
            refreshInterviews(true);
          })
          .catch(function (err) {
            notify("error", err.message);
            statusEl.value = "";
          });
      });
    }
    var previewBtn = body.querySelector(".rec-drawer-preview-resume");
    if (previewBtn) {
      previewBtn.addEventListener("click", function () {
        openResumeModal({
          name: previewBtn.getAttribute("data-name"),
          hasResume: true,
          resumePreviewUrl: previewBtn.getAttribute("data-preview"),
          resumeUrl: previewBtn.getAttribute("data-download"),
        });
      });
    }
  }

  function openResumeModal(app) {
    var modalEl = document.getElementById("recResumeModal");
    var frame = document.getElementById("recResumeFrame");
    var title = document.getElementById("recResumeModalTitle");
    if (!modalEl) return;
    if (title) title.textContent = (app.name || "Candidate") + " — Resume";
    if (frame) frame.src = app.resumePreviewUrl || app.resumeUrl + "?preview=1";
    if (window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function openFeedbackModal(d) {
    feedbackState = { url: d.feedbackUrl, name: d.name };
    var nameEl = document.getElementById("recFeedbackCandidate");
    var errEl = document.getElementById("recFeedbackError");
    if (nameEl) nameEl.textContent = d.name + " — " + d.round;
    if (errEl) errEl.hidden = true;
    document.querySelectorAll(".rec-feedback-rating").forEach(function (el) {
      el.value = "";
    });
    var overall = document.getElementById("recFeedbackOverall");
    var decision = document.getElementById("recFeedbackDecision");
    var notes = document.getElementById("recFeedbackNotes");
    if (overall) overall.value = "";
    if (decision) decision.value = "proceed";
    if (notes) notes.value = "";
    var modalEl = document.getElementById("recFeedbackModal");
    if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function bindFeedbackModal() {
    var submit = document.getElementById("recFeedbackSubmit");
    if (!submit) return;
    submit.addEventListener("click", function () {
      var errEl = document.getElementById("recFeedbackError");
      var payload = { notes: document.getElementById("recFeedbackNotes").value.trim() };
      document.querySelectorAll(".rec-feedback-rating").forEach(function (el) {
        if (el.value) payload[el.getAttribute("data-key")] = parseInt(el.value, 10);
      });
      var overall = document.getElementById("recFeedbackOverall").value;
      if (overall) payload.overall_rating = parseInt(overall, 10);
      payload.decision = document.getElementById("recFeedbackDecision").value;
      submit.disabled = true;
      patchJson(feedbackState.url, payload)
        .then(function (body) {
          notify("success", body.message || "Feedback saved.");
          var modalEl = document.getElementById("recFeedbackModal");
          if (modalEl && window.bootstrap) bootstrap.Modal.getInstance(modalEl).hide();
          refreshInterviews(true);
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

  function openRescheduleModal(d) {
    rescheduleState = { url: d.rescheduleUrl, name: d.name };
    var nameEl = document.getElementById("recRescheduleCandidate");
    var errEl = document.getElementById("recRescheduleError");
    if (nameEl) nameEl.textContent = d.name + " — " + d.round;
    if (errEl) errEl.hidden = true;
    document.getElementById("recRescheduleDate").value = "";
    document.getElementById("recRescheduleTime").value = "";
    var modalEl = document.getElementById("recRescheduleModal");
    if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function bindRescheduleModal() {
    var submit = document.getElementById("recRescheduleSubmit");
    if (!submit) return;
    submit.addEventListener("click", function () {
      var date = document.getElementById("recRescheduleDate").value;
      var time = document.getElementById("recRescheduleTime").value;
      var errEl = document.getElementById("recRescheduleError");
      if (!date || !time) {
        if (errEl) {
          errEl.textContent = "Date and time are required.";
          errEl.hidden = false;
        }
        return;
      }
      submit.disabled = true;
      patchJson(rescheduleState.url, { scheduled_at: date + "T" + time + ":00" })
        .then(function (body) {
          notify("success", body.message || "Interview rescheduled.");
          var modalEl = document.getElementById("recRescheduleModal");
          if (modalEl && window.bootstrap) bootstrap.Modal.getInstance(modalEl).hide();
          refreshInterviews(true);
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

  function openWhatsAppModal(d) {
    whatsAppState.message = whatsappMessage(d);
    whatsAppState.phone = normalizePhone(d.phone);
    document.getElementById("recWhatsAppMessage").value = whatsAppState.message;
    updateWhatsAppLink();
    var modalEl = document.getElementById("recWhatsAppModal");
    if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function updateWhatsAppLink() {
    var send = document.getElementById("recWhatsAppSend");
    var msg = document.getElementById("recWhatsAppMessage").value;
    var base = whatsAppState.phone ? "https://wa.me/" + whatsAppState.phone : "https://web.whatsapp.com/send";
    send.href = base + "?text=" + encodeURIComponent(msg);
  }

  function bindWhatsAppModal() {
    var textarea = document.getElementById("recWhatsAppMessage");
    if (textarea) {
      textarea.addEventListener("input", updateWhatsAppLink);
    }
  }

  function openEmailModal(d, reminder) {
    var inv = emailInvitation(d, reminder);
    emailState.email = d.email;
    emailState.subject = inv.subject;
    emailState.body = inv.body;
    document.getElementById("recEmailSubject").value = inv.subject;
    document.getElementById("recEmailBody").value = inv.body;
    updateEmailLink();
    var modalEl = document.getElementById("recEmailModal");
    if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function updateEmailLink() {
    var send = document.getElementById("recEmailSend");
    var subject = document.getElementById("recEmailSubject").value;
    var body = document.getElementById("recEmailBody").value;
    if (!emailState.email) {
      send.href = "mailto:?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
      return;
    }
    send.href =
      "mailto:" +
      encodeURIComponent(emailState.email) +
      "?subject=" +
      encodeURIComponent(subject) +
      "&body=" +
      encodeURIComponent(body);
  }

  function bindEmailModal() {
    ["recEmailSubject", "recEmailBody"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("input", updateEmailLink);
    });
  }

  function bindScheduleModal() {
    var openBtns = [document.getElementById("recScheduleInterviewBtn"), document.getElementById("recScheduleInterviewEmpty")];
    openBtns.forEach(function (btn) {
      if (!btn) return;
      btn.addEventListener("click", function () {
        var modalEl = document.getElementById("recScheduleModal");
        if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
      });
    });

    var candidateSelect = document.getElementById("recScheduleCandidate");
    var preview = document.getElementById("recScheduleCandidatePreview");
    if (candidateSelect) {
      candidateSelect.addEventListener("change", function () {
        var opt = candidateSelect.options[candidateSelect.selectedIndex];
        if (!opt || !opt.value) {
          if (preview) preview.hidden = true;
          return;
        }
        if (preview) preview.hidden = false;
        var avatar = document.getElementById("recScheduleAvatar");
        var photo = opt.getAttribute("data-photo");
        if (photo && avatar) {
          avatar.innerHTML = '<img src="' + escapeHtml(photo) + '" alt="" class="rcd-applicants-table__photo">';
        } else if (avatar) {
          avatar.innerHTML = "<span>" + escapeHtml((opt.getAttribute("data-name") || "?").charAt(0)) + "</span>";
        }
        document.getElementById("recScheduleName").textContent = opt.getAttribute("data-name") || "";
        document.getElementById("recScheduleJob").textContent = opt.getAttribute("data-job") || "";
        document.getElementById("recScheduleExp").textContent = opt.getAttribute("data-exp") || "—";
        document.getElementById("recScheduleSkills").textContent = opt.getAttribute("data-skills") || "—";
        var resumeBtn = document.getElementById("recSchedulePreviewResume");
        if (resumeBtn) {
          var hasResume = opt.getAttribute("data-resume") === "1";
          resumeBtn.hidden = !hasResume;
          resumeBtn._previewUrl = opt.getAttribute("data-resume-url");
          resumeBtn._name = opt.getAttribute("data-name");
        }
      });
    }

    var previewResume = document.getElementById("recSchedulePreviewResume");
    if (previewResume) {
      previewResume.addEventListener("click", function () {
        openResumeModal({
          name: previewResume._name,
          hasResume: true,
          resumePreviewUrl: previewResume._previewUrl,
        });
      });
    }

    var typeEl = document.getElementById("recScheduleType");
    var meetWrap = document.getElementById("recScheduleMeetWrap");
    var locWrap = document.getElementById("recScheduleLocationWrap");
    function syncTypeFields() {
      if (!typeEl) return;
      var opt = typeEl.options[typeEl.selectedIndex];
      var mode = opt ? opt.getAttribute("data-mode") : "online";
      var walkin = mode === "offline";
      if (meetWrap) meetWrap.hidden = walkin;
      if (locWrap) locWrap.hidden = !walkin;
    }
    if (typeEl) {
      typeEl.addEventListener("change", syncTypeFields);
      syncTypeFields();
    }

    var submit = document.getElementById("recScheduleSubmit");
    if (submit) {
      submit.addEventListener("click", function () {
        var select = document.getElementById("recScheduleCandidate");
        var opt = select.options[select.selectedIndex];
        var errEl = document.getElementById("recScheduleError");
        if (!opt || !opt.value) {
          if (errEl) {
            errEl.textContent = "Please select a candidate.";
            errEl.hidden = false;
          }
          return;
        }
        var date = document.getElementById("recScheduleDate").value;
        var time = document.getElementById("recScheduleTime").value;
        if (!date || !time) {
          if (errEl) {
            errEl.textContent = "Date and time are required.";
            errEl.hidden = false;
          }
          return;
        }
        var roundEl = document.getElementById("recScheduleRound");
        var roundLabel = roundEl.options[roundEl.selectedIndex].text;
        var typeOpt = typeEl.options[typeEl.selectedIndex];
        var mode = typeOpt.getAttribute("data-mode") || "online";
        var interviewer = document.getElementById("recScheduleInterviewer").value.trim();
        var notes = document.getElementById("recScheduleNotes").value.trim();
        if (interviewer) {
          notes = (notes ? notes + "\n" : "") + "Interviewer: " + interviewer;
        }
        submit.disabled = true;
        postJson(opt.getAttribute("data-schedule-url"), {
          scheduled_at: date + "T" + time + ":00",
          mode: mode,
          meet_url: document.getElementById("recScheduleMeet").value.trim(),
          location: document.getElementById("recScheduleLocation").value.trim(),
          interview_type: roundLabel + " — " + typeOpt.text,
          notes: notes,
        })
          .then(function (body) {
            notify("success", body.message || "Interview scheduled.");
            var modalEl = document.getElementById("recScheduleModal");
            if (modalEl && window.bootstrap) bootstrap.Modal.getInstance(modalEl).hide();
            refreshInterviews(false);
            window.setTimeout(function () {
              window.location.reload();
            }, 600);
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
  }

  function renderInterviewCard(item) {
    var pct = pipelineTotal ? Math.round(((item.pipeline_index + 1) / pipelineTotal) * 100) : 0;
    var liveClass = item.is_live ? " rcd-interview-card--live" : "";
    var upcomingClass = item.is_upcoming ? " rcd-interview-card--upcoming" : "";
    var avatar = item.photo_url
      ? '<img src="' + escapeHtml(item.photo_url) + '" alt="" class="rcd-applicants-table__photo">'
      : '<span class="rcd-pipeline-card__avatar"><span>' + escapeHtml(item.initials) + "</span></span>";
    var meetBlock = item.meet_url
      ? '<div class="rcd-interview-card__link-col"><dt>Meeting</dt><dd><a href="' +
        escapeHtml(item.meet_url) +
        '" target="_blank" rel="noopener" class="rcd-interview-card__meet-link">Join link</a></dd></div>'
      : item.location
        ? "<div><dt>Location</dt><dd>" + escapeHtml(item.location) + "</dd></div>"
        : "";
    var liveDot = item.is_live ? '<span class="rcd-interview-item__live" aria-label="In progress"></span>' : "";
    var joinItem = item.meet_url
      ? '<li><a class="dropdown-item" href="' +
        escapeHtml(item.meet_url) +
        '" target="_blank" rel="noopener"><span class="material-symbols-outlined">videocam</span>Join Meeting</a></li>'
      : "";

    return (
      '<article class="rcd-interview-card' +
      liveClass +
      upcomingClass +
      '" id="interview-' +
      escapeHtml(item.id) +
      '">' +
      '<div class="rcd-interview-card__head">' +
      '<div class="rcd-interview-card__when"><span class="rcd-interview-card__date">' +
      escapeHtml(item.date_label) +
      '</span><span class="rcd-interview-card__time">' +
      escapeHtml(item.time_label) +
      "</span>" +
      liveDot +
      '</div><span class="rcd-status-pill rcd-status-pill--' +
      escapeHtml(item.status_tone) +
      '">' +
      escapeHtml(item.status_label) +
      "</span></div>" +
      '<div class="rcd-interview-card__body"><div class="rcd-interview-card__candidate">' +
      avatar +
      '<div class="rcd-interview-card__meta"><strong class="rcd-interview-card__name">' +
      escapeHtml(item.candidate_name) +
      '</strong><span class="text-muted small d-block">' +
      escapeHtml(item.job_title) +
      '</span><span class="rcd-interview-card__round">' +
      escapeHtml(item.round_label) +
      " · " +
      escapeHtml(item.mode_label) +
      "</span></div></div>" +
      '<dl class="rcd-interview-card__details"><div><dt>Interviewer</dt><dd>' +
      escapeHtml(item.interviewer) +
      '</dd></div><div><dt>Stage</dt><dd>' +
      escapeHtml(item.stage_label) +
      "</dd></div>" +
      meetBlock +
      "</dl></div>" +
      '<div class="rcd-interview-card__pipeline"><div class="rcd-interview-card__pipeline-track"><span class="rcd-interview-card__pipeline-fill" style="width:' +
      pct +
      '%"></span></div><span class="rcd-interview-card__pipeline-label">' +
      escapeHtml(item.stage_label) +
      "</span></div>" +
      '<div class="rcd-interview-card__foot"><div class="dropdown rcd-interview-actions">' +
      '<button type="button" class="rcd-btn rcd-btn--soft rcd-btn--xs dropdown-toggle rec-interview-actions-btn" data-bs-toggle="dropdown" data-bs-auto-close="true"' +
      ' data-interview-id="' +
      escapeHtml(item.id) +
      '" data-app-id="' +
      escapeHtml(item.application_id) +
      '" data-name="' +
      escapeHtml(item.candidate_name) +
      '" data-job="' +
      escapeHtml(item.job_title) +
      '" data-company="' +
      escapeHtml(item.company_name) +
      '" data-email="' +
      escapeHtml(item.email) +
      '" data-phone="' +
      escapeHtml(item.phone) +
      '" data-has-resume="' +
      (item.has_resume ? "1" : "0") +
      '" data-resume-url="' +
      escapeHtml(item.resume_url) +
      '" data-resume-preview-url="' +
      escapeHtml(item.resume_preview_url) +
      '" data-detail-url="' +
      escapeHtml(item.detail_url) +
      '" data-meet-url="' +
      escapeHtml(item.meet_url) +
      '" data-location="' +
      escapeHtml(item.location) +
      '" data-cancel-url="' +
      escapeHtml(item.cancel_url) +
      '" data-reschedule-url="' +
      escapeHtml(item.reschedule_url) +
      '" data-feedback-url="' +
      escapeHtml(item.feedback_url) +
      '" data-status-url="' +
      escapeHtml(item.status_url) +
      '" data-app-status-url="' +
      escapeHtml(item.application_status_url) +
      '" data-date="' +
      escapeHtml(item.date_label) +
      '" data-time="' +
      escapeHtml(item.time_label) +
      '" data-round="' +
      escapeHtml(item.round_label) +
      '" data-mode="' +
      escapeHtml(item.mode_label) +
      '" data-interviewer="' +
      escapeHtml(item.interviewer) +
      '" data-can-cancel="' +
      (item.can_cancel ? "1" : "0") +
      '" data-can-reschedule="' +
      (item.can_reschedule ? "1" : "0") +
      '" data-can-complete="' +
      (item.can_complete ? "1" : "0") +
      '">Actions</button>' +
      '<ul class="dropdown-menu dropdown-menu-end rcd-applicant-actions__menu">' +
      '<li><button type="button" class="dropdown-item rec-int-action-profile"><span class="material-symbols-outlined">person</span>View Candidate</button></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-resume"' +
      (item.has_resume ? "" : " disabled") +
      '><span class="material-symbols-outlined">visibility</span>View Resume</button></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-download"' +
      (item.has_resume ? "" : " disabled") +
      '><span class="material-symbols-outlined">download</span>Download Resume</button></li>' +
      joinItem +
      '<li><hr class="dropdown-divider"></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-edit"' +
      (item.can_reschedule ? "" : " disabled") +
      '><span class="material-symbols-outlined">edit_calendar</span>Reschedule</button></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-cancel"' +
      (item.can_cancel ? "" : " disabled") +
      '><span class="material-symbols-outlined">cancel</span>Cancel Interview</button></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-complete"' +
      (item.can_complete ? "" : " disabled") +
      '><span class="material-symbols-outlined">check_circle</span>Mark Completed</button></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-feedback"><span class="material-symbols-outlined">rate_review</span>Add Feedback</button></li>' +
      '<li><hr class="dropdown-divider"></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-whatsapp"><span class="material-symbols-outlined">chat</span>Send WhatsApp</button></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-email"><span class="material-symbols-outlined">mail</span>Send Email</button></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-reminder"><span class="material-symbols-outlined">notifications</span>Send Reminder</button></li>' +
      '<li><hr class="dropdown-divider"></li>' +
      '<li><button type="button" class="dropdown-item rec-int-action-next"><span class="material-symbols-outlined">trending_flat</span>Move to Next Stage</button></li>' +
      "</ul></div></div></article>"
    );
  }

  function updateStats(summary) {
    if (!summary) return;
    summary.forEach(function (stat) {
      var el = document.querySelector('[data-stat="' + stat.key + '"]');
      if (el) el.textContent = stat.value;
    });
  }

  function refreshInterviews(silent) {
    if (!root || !templates.list) return;
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
        if (payload.summary) updateStats(payload.summary);
        if (!payload.interviews) return;
        calEvents = payload.calendar_events || [];
        var list = document.getElementById("recInterviewsList");
        var empty = document.getElementById("recInterviewsEmpty");
        if (payload.interviews.length === 0) {
          if (list) {
            list.innerHTML = "";
            list.hidden = true;
          }
          if (empty) empty.hidden = false;
        } else {
          if (empty) empty.hidden = true;
          if (list) {
            list.hidden = false;
            list.innerHTML = payload.interviews.map(renderInterviewCard).join("");
            bindActionMenus(list);
          }
        }
        if (document.getElementById("recInterviewsCalendarView") && !document.getElementById("recInterviewsCalendarView").hidden) {
          renderCalendar();
        }
      })
      .catch(function () {
        if (!silent) notify("error", "Unable to refresh interviews.");
      });
  }

  function bindViewTabs() {
    document.querySelectorAll(".rec-interviews-tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll(".rec-interviews-tab").forEach(function (t) {
          t.classList.remove("active");
        });
        tab.classList.add("active");
        var view = tab.getAttribute("data-view");
        var listView = document.getElementById("recInterviewsListView");
        var calView = document.getElementById("recInterviewsCalendarView");
        if (view === "calendar") {
          if (listView) listView.hidden = true;
          if (calView) {
            calView.hidden = false;
            renderCalendar();
          }
        } else {
          if (listView) listView.hidden = false;
          if (calView) calView.hidden = true;
        }
      });
    });
  }

  function renderCalendar() {
    var grid = document.getElementById("recCalGrid");
    var title = document.getElementById("recCalTitle");
    if (!grid || !title) return;
    if (!calMonth) calMonth = new Date();
    calMonth.setDate(1);
    var year = calMonth.getFullYear();
    var month = calMonth.getMonth();
    title.textContent = calMonth.toLocaleString(undefined, { month: "long", year: "numeric" });
    var firstDay = new Date(year, month, 1).getDay();
    var daysInMonth = new Date(year, month + 1, 0).getDate();
    var html = '<div class="rcd-cal-weekdays"><span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span></div>';
    html += '<div class="rcd-cal-days">';
    for (var i = 0; i < firstDay; i++) html += '<span class="rcd-cal-day rcd-cal-day--empty"></span>';
    for (var day = 1; day <= daysInMonth; day++) {
      var dateStr = year + "-" + String(month + 1).padStart(2, "0") + "-" + String(day).padStart(2, "0");
      var dayEvents = calEvents.filter(function (ev) {
        return ev.start && ev.start.indexOf(dateStr) === 0;
      });
      var eventsHtml = dayEvents
        .map(function (ev) {
          return (
            '<button type="button" class="rcd-cal-event" data-target="' +
            escapeHtml(ev.url || "") +
            '">' +
            escapeHtml(ev.title) +
            "</button>"
          );
        })
        .join("");
      html +=
        '<div class="rcd-cal-day"><span class="rcd-cal-day__num">' +
        day +
        '</span><div class="rcd-cal-day__events">' +
        eventsHtml +
        "</div></div>";
    }
    html += "</div>";
    grid.innerHTML = html;
    grid.querySelectorAll(".rcd-cal-event").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var target = btn.getAttribute("data-target") || "";
        var id = target.replace("#interview-", "");
        var el = document.getElementById("interview-" + id);
        document.querySelectorAll(".rec-interviews-tab").forEach(function (t) {
          t.classList.remove("active");
        });
        var listTab = document.querySelector('.rec-interviews-tab[data-view="list"]');
        if (listTab) listTab.classList.add("active");
        document.getElementById("recInterviewsListView").hidden = false;
        document.getElementById("recInterviewsCalendarView").hidden = true;
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });
  }

  function bindCalendarNav() {
    var prev = document.getElementById("recCalPrev");
    var next = document.getElementById("recCalNext");
    if (prev) {
      prev.addEventListener("click", function () {
        if (!calMonth) calMonth = new Date();
        calMonth.setMonth(calMonth.getMonth() - 1);
        renderCalendar();
      });
    }
    if (next) {
      next.addEventListener("click", function () {
        if (!calMonth) calMonth = new Date();
        calMonth.setMonth(calMonth.getMonth() + 1);
        renderCalendar();
      });
    }
  }

  function bindPolling() {
    pollTimer = window.setInterval(function () {
      refreshInterviews(true);
    }, 45000);
  }

  document.addEventListener("DOMContentLoaded", function () {
    root = document.getElementById("recInterviewsPage");
    if (!root) return;
    readTemplates();
    bindActionMenus();
    bindScheduleModal();
    bindFeedbackModal();
    bindRescheduleModal();
    bindWhatsAppModal();
    bindEmailModal();
    bindViewTabs();
    bindCalendarNav();
    bindPolling();
  });
})();
