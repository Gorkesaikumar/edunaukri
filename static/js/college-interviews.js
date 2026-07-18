(function () {
  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute("content")) return meta.getAttribute("content");
    var m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function notify(kind, message) {
    if (window.EduNotify && typeof window.EduNotify.show === "function") {
      window.EduNotify.show({ type: kind, message: message });
    }
  }

  function confirmAction(options) {
    if (!window.EduNotify || typeof window.EduNotify.confirm !== "function") {
      return Promise.resolve(false);
    }
    return window.EduNotify.confirm(options);
  }

  function request(url, method, payload) {
    return fetch(url, {
      method: method,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: payload ? JSON.stringify(payload) : undefined,
    }).then(function (res) {
      return res.json().then(function (body) {
        if (!res.ok || !body.success) {
          throw new Error((body && body.error) || "Request failed.");
        }
        return body;
      });
    });
  }

  function isoFromDateTime(dateValue, timeValue) {
    return dateValue + "T" + (timeValue || "09:00");
  }

  function channelToMode(channel) {
    var key = (channel || "").toLowerCase();
    if (key === "walk_in") return "In-person";
    if (key === "phone") return "Phone";
    if (key === "video" || key === "google_meet" || key === "zoom" || key === "microsoft_teams") return "Online";
    return "Online";
  }

  function channelLabel(channel) {
    var labels = {
      walk_in: "Walk-in",
      video: "Video Interview",
      phone: "Phone Interview",
      google_meet: "Google Meet",
      zoom: "Zoom",
      microsoft_teams: "Microsoft Teams",
    };
    return labels[channel] || "Video Interview";
  }

  function inferChannel(mode, platform) {
    var p = (platform || "").toLowerCase().trim();
    var m = (mode || "").toLowerCase().trim();
    if (p.indexOf("google") !== -1 || p.indexOf("meet") !== -1) return "google_meet";
    if (p.indexOf("zoom") !== -1) return "zoom";
    if (p.indexOf("teams") !== -1) return "microsoft_teams";
    if (p.indexOf("phone") !== -1) return "phone";
    if (p.indexOf("walk") !== -1 || p.indexOf("in-person") !== -1) return "walk_in";
    if (m.indexOf("phone") !== -1) return "phone";
    if (m.indexOf("in-person") !== -1 || m.indexOf("offline") !== -1) return "walk_in";
    return "video";
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("icdInterviewsPage");
    if (!root) return;

    var scheduleTemplate = root.getAttribute("data-api-schedule-template");
    var rescheduleTemplate = root.getAttribute("data-api-reschedule-template");
    var cancelTemplate = root.getAttribute("data-api-cancel-template");
    var completeTemplate = root.getAttribute("data-api-complete-template");

    var modalEl = document.getElementById("icdInterviewModal");
    var modal = modalEl ? new bootstrap.Modal(modalEl) : null;
    var modalTitle = document.getElementById("icdInterviewModalTitle");
    var candidateLabel = document.getElementById("icdInterviewCandidate");
    var errorBox = document.getElementById("icdInterviewError");
    var submitBtn = document.getElementById("icdInterviewSubmit");
    var dateInput = document.getElementById("icdInterviewDate");
    var timeInput = document.getElementById("icdInterviewTime");
    var typeInput = document.getElementById("icdInterviewType");
    var channelInput = document.getElementById("icdInterviewChannel");
    var linkInput = document.getElementById("icdInterviewLink");
    var locationInput = document.getElementById("icdInterviewLocation");
    var interviewerInput = document.getElementById("icdInterviewInterviewer");
    var durationInput = document.getElementById("icdInterviewDuration");
    var notesInput = document.getElementById("icdInterviewNotes");
    var linkWrap = document.getElementById("icdInterviewLinkWrap");
    var locationWrap = document.getElementById("icdInterviewLocationWrap");

    var currentAction = "schedule";
    var currentApplicationId = "";

    function toggleInterviewFields() {
      if (!channelInput) return;
      var channel = (channelInput.value || "").toLowerCase();
      var isOffline = channel === "walk_in";
      var isPhone = channel === "phone";
      // Show location for walk-in, show link for online/video modes
      if (linkWrap) linkWrap.style.display = (isOffline || isPhone) ? "none" : "";
      if (locationWrap) locationWrap.style.display = isOffline ? "" : "none";
    }
    if (channelInput) {
      channelInput.addEventListener("change", toggleInterviewFields);
    }

    var candidateInitialsEl = document.getElementById("icdInterviewCandidateInitials");

    function parseDateLabel(label) {
      if (!label || label === "TBD") return "";
      var date = new Date(label);
      if (Number.isNaN(date.getTime())) return "";
      return date.toISOString().slice(0, 10);
    }

    function parseTimeLabel(label) {
      if (!label) return "";
      var d = new Date("2000-01-01 " + label);
      if (Number.isNaN(d.getTime())) return "";
      var h = String(d.getHours()).padStart(2, "0");
      var m = String(d.getMinutes()).padStart(2, "0");
      return h + ":" + m;
    }

    document.querySelectorAll(".icd-int-open").forEach(function (btn) {
      btn.addEventListener("click", function () {
        currentAction = btn.getAttribute("data-action") || "schedule";
        currentApplicationId = btn.getAttribute("data-application-id") || "";
        modalTitle.textContent = currentAction === "reschedule" ? "Reschedule Interview" : "Schedule Interview";
        var candidateName = btn.getAttribute("data-candidate") || "";
        if (candidateLabel) candidateLabel.textContent = candidateName;
        if (candidateInitialsEl) {
          var parts = candidateName.trim().split(/\s+/);
          candidateInitialsEl.textContent = parts.length >= 2
            ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
            : candidateName.slice(0, 2).toUpperCase();
        }
        dateInput.value = parseDateLabel(btn.getAttribute("data-date"));
        timeInput.value = parseTimeLabel(btn.getAttribute("data-time"));
        typeInput.value = btn.getAttribute("data-interview-type") || "";
        var platform = btn.getAttribute("data-meeting-platform") || "";
        channelInput.value = inferChannel(btn.getAttribute("data-mode"), platform);
        if (linkInput) linkInput.value = btn.getAttribute("data-meeting-link") || "";
        if (locationInput) locationInput.value = btn.getAttribute("data-location") || "";
        interviewerInput.value = btn.getAttribute("data-interviewer-name") || "";
        durationInput.value = btn.getAttribute("data-duration") || "45";
        notesInput.value = btn.getAttribute("data-notes") || "";
        toggleInterviewFields();
        errorBox.hidden = true;
        errorBox.textContent = "";
        if (modal) modal.show();
      });
    });

    if (submitBtn) {
      submitBtn.addEventListener("click", function () {
        if (!currentApplicationId) return;
        var dateValue = (dateInput.value || "").trim();
        var timeValue = (timeInput.value || "").trim();
        if (!dateValue || !timeValue) {
          errorBox.hidden = false;
          errorBox.textContent = "Date and time are required.";
          return;
        }
        var payload = {
          scheduled_at: isoFromDateTime(dateValue, timeValue),
          interview_type: (typeInput.value || "").trim(),
          mode: channelToMode(channelInput.value),
          meeting_platform: channelLabel(channelInput.value),
          meet_url: (linkInput.value || "").trim(),
          location: (locationInput.value || "").trim(),
          interviewer_name: (interviewerInput.value || "").trim(),
          duration_minutes: parseInt(durationInput.value || "45", 10),
          notes: (notesInput.value || "").trim(),
        };
        var template = currentAction === "reschedule" ? rescheduleTemplate : scheduleTemplate;
        var url = template.replace(
          "00000000-0000-0000-0000-000000000000",
          currentApplicationId
        );
        submitBtn.disabled = true;
        request(url, currentAction === "reschedule" ? "PATCH" : "POST", payload)
          .then(function (body) {
            notify("success", body.message || "Interview saved.");
            window.location.reload();
          })
          .catch(function (err) {
            errorBox.hidden = false;
            errorBox.textContent = err.message || "Could not save interview.";
          })
          .finally(function () {
            submitBtn.disabled = false;
          });
      });
    }

    document.querySelectorAll(".icd-int-complete").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var applicationId = btn.getAttribute("data-application-id");
        if (!applicationId) return;
        var ok = await confirmAction({
          title: "Mark Interview Completed",
          message: "Mark this interview as completed?",
          confirmText: "Mark Completed",
          cancelText: "Cancel",
          variant: "info",
        });
        if (!ok) return;
        var url = completeTemplate.replace("00000000-0000-0000-0000-000000000000", applicationId);
        btn.disabled = true;
        request(url, "POST")
          .then(function (body) {
            notify("success", body.message || "Interview marked completed.");
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message || "Could not update interview.");
          })
          .finally(function () {
            btn.disabled = false;
          });
      });
    });

    document.querySelectorAll(".icd-int-cancel").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var applicationId = btn.getAttribute("data-application-id");
        if (!applicationId) return;
        var ok = await confirmAction({
          title: "Cancel Interview",
          message: "Cancel this interview and move candidate back to pending scheduling?",
          confirmText: "Cancel Interview",
          cancelText: "Keep Interview",
          variant: "warning",
        });
        if (!ok) return;
        var url = cancelTemplate.replace("00000000-0000-0000-0000-000000000000", applicationId);
        btn.disabled = true;
        request(url, "POST", { reason: "Interview cancelled by institution recruiter." })
          .then(function (body) {
            notify("success", body.message || "Interview cancelled.");
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message || "Could not cancel interview.");
          })
          .finally(function () {
            btn.disabled = false;
          });
      });
    });

    /* ── Select and Reject Candidates ── */
    var selectTemplate = root.getAttribute("data-api-select-template");
    var rejectTemplate = root.getAttribute("data-api-reject-template");

    var selectModalEl = document.getElementById("icdSelectModal");
    var selectModal = selectModalEl ? new bootstrap.Modal(selectModalEl) : null;
    var rejectModalEl = document.getElementById("icdRejectModal");
    var rejectModal = rejectModalEl ? new bootstrap.Modal(rejectModalEl) : null;
    
    var selectAppId = "";
    var rejectAppId = "";

    document.querySelectorAll(".icd-int-select").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selectAppId = btn.getAttribute("data-application-id");
        if (!selectAppId) return;
        document.getElementById("icdSelectNotes").value = "";
        document.getElementById("icdSelectError").hidden = true;
        if (selectModal) selectModal.show();
      });
    });

    document.querySelectorAll(".icd-int-reject").forEach(function (btn) {
      btn.addEventListener("click", function () {
        rejectAppId = btn.getAttribute("data-application-id");
        if (!rejectAppId) return;
        document.getElementById("icdRejectNotes").value = "";
        document.getElementById("icdRejectError").hidden = true;
        if (rejectModal) rejectModal.show();
      });
    });

    var selectSubmitBtn = document.getElementById("icdSelectSubmit");
    if (selectSubmitBtn) {
      selectSubmitBtn.addEventListener("click", function () {
        if (!selectAppId) return;
        var url = selectTemplate.replace("00000000-0000-0000-0000-000000000000", selectAppId);
        var notes = (document.getElementById("icdSelectNotes").value || "").trim();
        selectSubmitBtn.disabled = true;
        request(url, "POST", { notes: notes })
          .then(function (body) {
            notify("success", body.message || "Candidate selected.");
            window.location.reload();
          })
          .catch(function (err) {
            var errBox = document.getElementById("icdSelectError");
            errBox.hidden = false;
            errBox.textContent = err.message || "Could not select candidate.";
          })
          .finally(function () {
            selectSubmitBtn.disabled = false;
          });
      });
    }

    var rejectSubmitBtn = document.getElementById("icdRejectSubmit");
    if (rejectSubmitBtn) {
      rejectSubmitBtn.addEventListener("click", function () {
        if (!rejectAppId) return;
        var reason = (document.getElementById("icdRejectNotes").value || "").trim();
        if (!reason) {
          var errBox = document.getElementById("icdRejectError");
          errBox.hidden = false;
          errBox.textContent = "Rejection reason is required.";
          return;
        }
        var url = rejectTemplate.replace("00000000-0000-0000-0000-000000000000", rejectAppId);
        rejectSubmitBtn.disabled = true;
        request(url, "POST", { status: "rejected", rejection_reason: reason })
          .then(function (body) {
            notify("success", body.message || "Candidate rejected.");
            window.location.reload();
          })
          .catch(function (err) {
            var errBox = document.getElementById("icdRejectError");
            errBox.hidden = false;
            errBox.textContent = err.message || "Could not reject candidate.";
          })
          .finally(function () {
            rejectSubmitBtn.disabled = false;
          });
      });
    }

    /* ── Profile modal for pending schedule cards ── */
    var profileModalEl = document.getElementById("icdInterviewProfileModal");
    var profileModal = profileModalEl ? new bootstrap.Modal(profileModalEl) : null;
    var profileBody = document.getElementById("icdInterviewProfileBody");

    document.querySelectorAll(".icd-pending-profile").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var url = btn.getAttribute("data-profile-url");
        if (!url || !profileModal) return;
        if (profileBody) {
          profileBody.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div></div>';
        }
        profileModal.show();
        fetch(url, {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        })
          .then(function (res) { return res.json(); })
          .then(function (data) {
            if (profileBody) {
              profileBody.innerHTML = data.html || "<p class='text-muted text-center py-4'>No profile data available.</p>";
            }
          })
          .catch(function () {
            if (profileBody) profileBody.innerHTML = "<p class='text-danger text-center py-4'>Failed to load profile.</p>";
          });
      });
    });

    (function renderCalendarStrip() {
      var grid = document.getElementById("icdInterviewCalendarGrid");
      var payloadEl = document.getElementById("icdInterviewCalendarData");
      if (!grid || !payloadEl) return;
      var data = [];
      try {
        data = JSON.parse(payloadEl.textContent || "[]");
      } catch (e) {
        data = [];
      }
      var today = new Date();
      today.setHours(0, 0, 0, 0);

      var byDate = {};
      data.forEach(function (item) {
        if (!item || !item.scheduled_at || item.status !== "interview_scheduled") return;
        var d = new Date(item.scheduled_at);
        if (Number.isNaN(d.getTime())) return;
        d.setHours(0, 0, 0, 0);
        var key = d.toISOString().slice(0, 10);
        if (!byDate[key]) byDate[key] = { count: 0, titles: [] };
        byDate[key].count += 1;
        if (item.candidate_name) byDate[key].titles.push(item.candidate_name);
      });

      var parts = [];
      for (var i = 0; i < 7; i++) {
        var day = new Date(today.getTime());
        day.setDate(today.getDate() + i);
        var key = day.toISOString().slice(0, 10);
        var entry = byDate[key] || { count: 0, titles: [] };
        var dayLabel = day.toLocaleDateString(undefined, { weekday: "short" });
        var dateLabel = day.toLocaleDateString(undefined, { month: "short", day: "numeric" });
        var meta = entry.count ? entry.titles.slice(0, 2).join(", ") : "No interviews";
        var activeClass = entry.count > 0 ? " icd-int-day--active" : " icd-int-day--empty";
        parts.push(
          '<article class="icd-int-day' + activeClass + '">' +
            '<p class="icd-int-day__label">' + dayLabel + " · " + dateLabel + "</p>" +
            '<p class="icd-int-day__count">' + entry.count + "</p>" +
            '<p class="icd-int-day__meta">' + meta + "</p>" +
          "</article>"
        );
      }
      grid.innerHTML = parts.join("");
    })();
  });
})();
