(function () {
  "use strict";
  var resumeZoom = 1;

  function csrfToken(root) {
    return (
      root.getAttribute("data-csrf") ||
      document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") ||
      ""
    );
  }

  function notify(type, message) {
    if (window.EduNotify && typeof window.EduNotify.toast === "function") {
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
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function bindStatusSelect(select, token) {
    select.addEventListener("change", function () {
      var url = select.getAttribute("data-status-url");
      if (!url) return;
      fetch(url, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": token,
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
        body: JSON.stringify({ status: select.value }),
      })
        .then(function (res) {
          return res.json().then(function (payload) {
            if (!res.ok || !payload.success) throw new Error(payload.error || "Update failed.");
            notify("success", payload.message || "Status updated.");
            window.location.reload();
          });
        })
        .catch(function (err) {
          notify("error", err.message);
        });
    });
  }

  function postStatus(url, token, status) {
    return fetch(url, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
      body: JSON.stringify({ status: status }),
    }).then(function (res) {
      return res.json().then(function (payload) {
        if (!res.ok || !payload.success) throw new Error(payload.error || "Update failed.");
        return payload;
      });
    });
  }

  function bindQuickStatus(btn, token) {
    btn.addEventListener("click", async function () {
      var nextStatus = btn.getAttribute("data-next-status");
      var url = btn.getAttribute("data-status-url");
      if (!nextStatus || !url) return;
      if (nextStatus === "rejected") {
        var ok = await confirmAction({
          title: "Reject Application",
          message: "Are you sure you want to reject this application?",
          confirmText: "Reject",
          cancelText: "Cancel",
          variant: "danger",
        });
        if (!ok) return;
      }
      btn.disabled = true;
      postStatus(url, token, nextStatus)
        .then(function (payload) {
          notify("success", payload.message || "Status updated.");
          window.location.reload();
        })
        .catch(function (err) {
          notify("error", err.message);
          btn.disabled = false;
        });
    });
  }

  function bindNotesSave(btn, root, token) {
    btn.addEventListener("click", function () {
      var card = btn.closest("[data-application-id]");
      var scope = card || root;
      var url = btn.getAttribute("data-notes-url") || root.getAttribute("data-notes-url");
      var collegeNotes = scope.querySelector('[data-notes-field="college_notes"]');
      var internalRemarks = scope.querySelector('[data-notes-field="internal_remarks"]');
      var ratingField = scope.querySelector("[data-college-rating]");
      var ratingValue = ratingField ? ratingField.value : "";
      fetch(url, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": token,
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
        body: JSON.stringify({
          college_notes: collegeNotes ? collegeNotes.value : "",
          internal_remarks: internalRemarks ? internalRemarks.value : "",
          college_rating: ratingValue,
        }),
      })
        .then(function (res) {
          return res.json().then(function (payload) {
            if (!res.ok || !payload.success) throw new Error(payload.error || "Save failed.");
            notify("success", payload.message || "Notes saved.");
          });
        })
        .catch(function (err) {
          notify("error", err.message);
        });
    });
  }

  function isPreviewSupported(mimeType, filename) {
    var mime = String(mimeType || "").toLowerCase();
    var name = String(filename || "").toLowerCase();
    if (mime.indexOf("pdf") !== -1) return true;
    if (name.endsWith(".pdf")) return true;
    return false;
  }

  function applyResumeZoom() {
    var frame = document.getElementById("icdResumeFrame");
    if (!frame) return;
    frame.style.transform = "scale(" + resumeZoom + ")";
    frame.style.transformOrigin = "top center";
    frame.style.height = Math.min(95 / resumeZoom, 95) + "vh";
  }

  function openResumeModal(payload) {
    var modalEl = document.getElementById("icdResumeModal");
    var title = document.getElementById("icdResumeModalTitle");
    var subtitle = document.getElementById("icdResumeModalSubtitle");
    var toolbar = document.getElementById("icdResumeToolbar");
    var viewport = document.getElementById("icdResumeViewport");
    var frame = document.getElementById("icdResumeFrame");
    var unsupported = document.getElementById("icdResumeUnsupported");
    var unsupportedText = document.getElementById("icdResumeUnsupportedText");
    var unsupportedDownload = document.getElementById("icdResumeUnsupportedDownload");
    var missing = document.getElementById("icdResumeMissing");
    var download = document.getElementById("icdResumeDownload");
    if (!modalEl) return;

    if (title) title.textContent = payload.candidate ? payload.candidate + " - Resume" : "Candidate Resume";
    if (subtitle) subtitle.textContent = payload.job ? "Applied for " + payload.job : "";
    if (download) download.href = payload.downloadUrl || "#";
    if (unsupportedDownload) unsupportedDownload.href = payload.downloadUrl || "#";
    if (frame) frame.src = "about:blank";

    var hasResume = !!(payload.previewUrl || payload.downloadUrl);
    var previewable = hasResume && isPreviewSupported(payload.mimeType, payload.fileName);
    if (missing) missing.hidden = hasResume;
    if (unsupported) unsupported.hidden = !hasResume || previewable;
    if (viewport) viewport.hidden = !hasResume || !previewable;
    if (toolbar) toolbar.hidden = !hasResume;

    if (!hasResume) {
      if (window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
      return;
    }

    if (previewable) {
      resumeZoom = 1;
      applyResumeZoom();
      if (frame) frame.src = payload.previewUrl || payload.downloadUrl;
    } else if (unsupportedText) {
      unsupportedText.innerHTML =
        "Preview is not available for <strong>" +
        escapeHtml(payload.fileName || "this format") +
        "</strong>. Download to view or print.";
    }

    if (window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function bindResumeControls() {
    var zoomIn = document.getElementById("icdResumeZoomIn");
    var zoomOut = document.getElementById("icdResumeZoomOut");
    var printBtn = document.getElementById("icdResumePrint");
    var fsBtn = document.getElementById("icdResumeFullscreen");
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
        var frame = document.getElementById("icdResumeFrame");
        if (frame && frame.contentWindow) {
          try {
            frame.contentWindow.focus();
            frame.contentWindow.print();
          } catch (e) {}
        }
      });
    }
    if (fsBtn) {
      fsBtn.addEventListener("click", function () {
        var viewport = document.getElementById("icdResumeViewport");
        if (viewport && viewport.requestFullscreen) viewport.requestFullscreen();
      });
    }
  }

  function bindOfferModal(token) {
    var modalEl = document.getElementById("icdOfferModal");
    if (!modalEl) return;
    var titleEl = document.getElementById("icdOfferModalTitle");
    var candidateEl = document.getElementById("icdOfferCandidate");
    var offerUrlEl = document.getElementById("icdOfferLetterUrl");
    var offerNotesEl = document.getElementById("icdOfferNotes");
    var errorEl = document.getElementById("icdOfferError");
    var submitBtn = document.getElementById("icdOfferSubmit");
    var modal = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    var active = { statusUrl: "", notesUrl: "" };

    function buildRemarks(url, note) {
      var parts = [];
      if (url) parts.push("Offer Letter URL: " + url);
      if (note) parts.push("Offer Note: " + note);
      return parts.join("\n");
    }

    document.querySelectorAll("[data-open-offer-modal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        active.statusUrl = btn.getAttribute("data-status-url") || "";
        active.notesUrl = btn.getAttribute("data-notes-url") || "";
        var candidate = btn.getAttribute("data-candidate") || "Candidate";
        var vacancy = btn.getAttribute("data-vacancy") || "";
        var existingUrl = btn.getAttribute("data-existing-offer-url") || "";
        if (titleEl) titleEl.textContent = "Send Offer";
        if (candidateEl) candidateEl.textContent = candidate + (vacancy ? " — " + vacancy : "");
        if (offerUrlEl) offerUrlEl.value = existingUrl;
        if (offerNotesEl) offerNotesEl.value = "";
        if (errorEl) {
          errorEl.hidden = true;
          errorEl.textContent = "";
        }
        if (modal) modal.show();
      });
    });

    if (submitBtn) {
      submitBtn.addEventListener("click", function () {
        if (!active.statusUrl || !active.notesUrl) return;
        var offerUrl = (offerUrlEl && offerUrlEl.value ? offerUrlEl.value.trim() : "");
        var offerNote = (offerNotesEl && offerNotesEl.value ? offerNotesEl.value.trim() : "");
        if (!offerUrl && !offerNote) {
          if (errorEl) {
            errorEl.hidden = false;
            errorEl.textContent = "Add an offer letter URL or offer note before sending.";
          }
          return;
        }
        submitBtn.disabled = true;
        postStatus(active.statusUrl, token, "offer_released")
          .then(function () {
            return fetch(active.notesUrl, {
              method: "PATCH",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": token,
                "X-Requested-With": "XMLHttpRequest",
              },
              credentials: "same-origin",
              body: JSON.stringify({
                internal_remarks: buildRemarks(offerUrl, offerNote),
              }),
            });
          })
          .then(function (res) {
            return res.json().then(function (payload) {
              if (!res.ok || !payload.success) throw new Error(payload.error || "Unable to save offer details.");
              notify("success", "Offer released successfully.");
              if (modal) modal.hide();
              window.location.reload();
            });
          })
          .catch(function (err) {
            if (errorEl) {
              errorEl.hidden = false;
              errorEl.textContent = err.message || "Could not release offer.";
            }
          })
          .finally(function () {
            submitBtn.disabled = false;
          });
      });
    }
  }

  /* ── NEW: Notes Modal ── */
  function bindNotesModal(token) {
    var modalEl = document.getElementById("icdNotesModal");
    if (!modalEl) return;
    var subtitleEl = document.getElementById("icdNotesModalSubtitle");
    var ratingEl = document.getElementById("icdNotesRating");
    var collegeEl = document.getElementById("icdNotesCollege");
    var internalEl = document.getElementById("icdNotesInternal");
    var errorEl = document.getElementById("icdNotesError");
    var submitBtn = document.getElementById("icdNotesSubmit");
    var modal = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    var activeNotesUrl = "";

    document.querySelectorAll("[data-open-notes-modal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeNotesUrl = btn.getAttribute("data-notes-url") || "";
        var candidate = btn.getAttribute("data-candidate") || "Candidate";
        if (subtitleEl) subtitleEl.textContent = candidate;
        if (ratingEl) ratingEl.value = btn.getAttribute("data-college-rating") || "";
        if (collegeEl) collegeEl.value = btn.getAttribute("data-college-notes") || "";
        if (internalEl) internalEl.value = btn.getAttribute("data-internal-remarks") || "";
        if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
        if (modal) modal.show();
      });
    });

    if (submitBtn) {
      submitBtn.addEventListener("click", function () {
        if (!activeNotesUrl) return;
        submitBtn.disabled = true;
        fetch(activeNotesUrl, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
            "X-Requested-With": "XMLHttpRequest",
          },
          credentials: "same-origin",
          body: JSON.stringify({
            college_notes: collegeEl ? collegeEl.value : "",
            internal_remarks: internalEl ? internalEl.value : "",
            college_rating: ratingEl ? ratingEl.value : "",
          }),
        })
          .then(function (res) {
            return res.json().then(function (payload) {
              if (!res.ok || !payload.success) throw new Error(payload.error || "Save failed.");
              notify("success", "Notes saved successfully.");
              if (modal) modal.hide();
            });
          })
          .catch(function (err) {
            if (errorEl) { errorEl.hidden = false; errorEl.textContent = err.message; }
          })
          .finally(function () { submitBtn.disabled = false; });
      });
    }
  }

  /* ── NEW: Schedule Interview Modal ── */
  function bindScheduleModal(token) {
    var modalEl = document.getElementById("icdScheduleModal");
    if (!modalEl) return;
    
    var subtitleEl = document.getElementById("icdScheduleSubtitle");
    var modeSelect = document.getElementById("icdSchedMode");
    var onlineFields = document.getElementById("icdSchedOnlineFields");
    var offlineFields = document.getElementById("icdSchedOfflineFields");
    var errorEl = document.getElementById("icdSchedError");
    var submitBtn = document.getElementById("icdSchedSubmit");
    
    var modal = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    var activeAppId = "";

    // Handle field toggling
    if (modeSelect) {
      modeSelect.addEventListener("change", function () {
        var isOnline = modeSelect.value === "ONLINE";
        var isOffline = modeSelect.value === "OFFLINE";
        if (onlineFields) onlineFields.style.display = isOnline ? "block" : "none";
        if (offlineFields) offlineFields.style.display = isOffline ? "block" : "none";
      });
    }

    document.querySelectorAll("[data-open-schedule-modal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeAppId = btn.getAttribute("data-application-id") || "";
        var candidate = btn.getAttribute("data-candidate") || "Candidate";
        var vacancy = btn.getAttribute("data-vacancy") || "";
        if (subtitleEl) subtitleEl.textContent = candidate + (vacancy ? " — " + vacancy : "");
        if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
        
        // Reset form
        var form = document.getElementById("icdScheduleForm");
        if (form) form.reset();
        
        // Setup defaults
        var now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset() + 60);
        var dateStr = now.toISOString().slice(0, 16);
        document.getElementById("icdSchedDate").value = dateStr;
        if (modeSelect) modeSelect.dispatchEvent(new Event("change"));

        if (modal) modal.show();
      });
    });

    if (submitBtn) {
      submitBtn.addEventListener("click", function () {
        if (!activeAppId) return;
        var form = document.getElementById("icdScheduleForm");
        if (form && !form.checkValidity()) {
          form.reportValidity();
          return;
        }

        var payload = {
          scheduled_at: document.getElementById("icdSchedDate").value,
          interview_type: document.getElementById("icdSchedType").value,
          mode: modeSelect.value,
          meeting_platform: document.getElementById("icdSchedPlatform").value,
          meet_url: document.getElementById("icdSchedLink").value,
          location: document.getElementById("icdSchedLocation").value,
          interviewer_name: document.getElementById("icdSchedInterviewer").value,
          notes: document.getElementById("icdSchedNotes").value,
          duration_minutes: document.getElementById("icdSchedDuration").value
        };

        submitBtn.disabled = true;
        // Determine base URL dynamically (e.g. /academic/college/)
        var baseUrl = window.location.pathname.split("/applications")[0];
        var url = baseUrl + "/api/interviews/" + activeAppId + "/schedule/";

        fetch(url, {
          method: "POST", // The API uses POST
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
            "X-Requested-With": "XMLHttpRequest",
          },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        })
          .then(function (res) {
            return res.json().then(function (data) {
              if (!res.ok || !data.success) throw new Error(data.error || "Unable to schedule interview.");
              notify("success", "Interview scheduled successfully.");
              if (modal) modal.hide();
              window.location.reload();
            });
          })
          .catch(function (err) {
            if (errorEl) { errorEl.hidden = false; errorEl.textContent = err.message; }
          })
          .finally(function () { submitBtn.disabled = false; });
      });
    }
  }

  /* ── NEW: Shortlist Modal ── */
  function bindShortlistModal(token) {
    var modalEl = document.getElementById("icdShortlistModal");
    if (!modalEl) return;
    var nameEl = document.getElementById("icdShortlistCandidateName");
    var vacancyEl = document.getElementById("icdShortlistVacancyTitle");
    var errorEl = document.getElementById("icdShortlistError");
    var submitBtn = document.getElementById("icdShortlistSubmit");
    var modal = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    var activeUrl = "";
    var activeAppId = "";

    document.querySelectorAll("[data-open-shortlist-modal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeUrl = btn.getAttribute("data-status-url") || "";
        activeAppId = btn.getAttribute("data-application-id") || "";
        if (nameEl) nameEl.textContent = btn.getAttribute("data-candidate") || "the candidate";
        if (vacancyEl) vacancyEl.textContent = btn.getAttribute("data-vacancy") || "the applied";
        if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
        if (modal) modal.show();
      });
    });

    if (submitBtn) {
      submitBtn.addEventListener("click", function () {
        if (!activeUrl) return;
        submitBtn.disabled = true;
        // Set application status to SHORTLISTED — the dedicated shortlist stage
        postStatus(activeUrl, token, "shortlisted")
          .then(function (payload) {
            notify("success", "Candidate shortlisted successfully.");
            if (modal) modal.hide();

            // 1. Update KPI Strip Counts
            var underReviewValEl = document.querySelector('.ats-kpi-card--secondary .ats-kpi-card__value');
            if (underReviewValEl) {
              var val = parseInt(underReviewValEl.textContent) || 0;
              underReviewValEl.textContent = Math.max(0, val - 1);
            }
            var shortlistedValEl = document.querySelector('.ats-kpi-card--success .ats-kpi-card__value');
            if (shortlistedValEl) {
              var val = parseInt(shortlistedValEl.textContent) || 0;
              shortlistedValEl.textContent = val + 1;
            }

            // 2. Update/Animate DOM Candidate list card
            var cardEl = document.querySelector('[data-application-id="' + activeAppId + '"]');
            var urlParams = new URLSearchParams(window.location.search);
            var statusFilter = urlParams.get('status') || '';

            if (statusFilter === 'review' || statusFilter === 'applied') {
              if (cardEl) {
                cardEl.style.transition = 'all 0.4s ease';
                cardEl.style.opacity = '0';
                cardEl.style.transform = 'translateY(-10px)';
                setTimeout(function () {
                  cardEl.remove();
                  var listEl = document.querySelector('.ats-list');
                  if (listEl && !listEl.querySelector('.ats-card')) {
                    window.location.reload();
                  }
                }, 400);
              }
            } else {
              if (cardEl) {
                var badgeEl = cardEl.querySelector('.ats-badge');
                if (badgeEl) {
                  badgeEl.className = 'ats-badge ats-badge--icd-badge--success';
                  badgeEl.textContent = 'Shortlisted';
                }
                var shortlistBtn = cardEl.querySelector('[data-open-shortlist-modal]');
                if (shortlistBtn) {
                  var li = shortlistBtn.closest('li');
                  if (li) li.remove();
                }
              }
            }
            submitBtn.disabled = false;
          })
          .catch(function (err) {
            if (errorEl) { errorEl.hidden = false; errorEl.textContent = err.message; }
            submitBtn.disabled = false;
          });
      });
    }
  }

  /* ── NEW: Reject Modal ── */
  function bindRejectModal(token) {
    var modalEl = document.getElementById("icdRejectModal");
    if (!modalEl) return;
    var nameEl = document.getElementById("icdRejectCandidateName");
    var vacancyEl = document.getElementById("icdRejectVacancyTitle");
    var errorEl = document.getElementById("icdRejectError");
    var submitBtn = document.getElementById("icdRejectSubmit");
    var codeEl = document.getElementById("icdRejectReasonCode");
    var notesEl = document.getElementById("icdRejectNotes");
    var modal = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    var activeUrl = "";

    document.querySelectorAll("[data-open-reject-modal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeUrl = btn.getAttribute("data-status-url") || "";
        if (nameEl) nameEl.textContent = btn.getAttribute("data-candidate") || "the candidate";
        if (vacancyEl) vacancyEl.textContent = btn.getAttribute("data-vacancy") || "the applied";
        if (codeEl) codeEl.value = "";
        if (notesEl) notesEl.value = "";
        if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
        if (modal) modal.show();
      });
    });

    if (submitBtn) {
      submitBtn.addEventListener("click", function () {
        if (!activeUrl) return;
        submitBtn.disabled = true;
        var payload = { status: "rejected" };
        
        var rejectionReason = [];
        if (codeEl && codeEl.value) rejectionReason.push(codeEl.options[codeEl.selectedIndex].text);
        if (notesEl && notesEl.value) rejectionReason.push(notesEl.value);
        if (rejectionReason.length > 0) payload.rejection_reason = rejectionReason.join(" - ");

        fetch(activeUrl, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
            "X-Requested-With": "XMLHttpRequest",
          },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        })
          .then(function (res) {
            return res.json().then(function (data) {
              if (!res.ok || !data.success) throw new Error(data.error || "Update failed.");
              notify("success", "Candidate rejected.");
              if (modal) modal.hide();
              window.location.reload();
            });
          })
          .catch(function (err) {
            if (errorEl) { errorEl.hidden = false; errorEl.textContent = err.message; }
            submitBtn.disabled = false;
          });
      });
    }
  }

  /* ── NEW: Contact Modal ── */
  function bindContactModal() {
    var modalEl = document.getElementById("icdContactModal");
    if (!modalEl) return;
    var nameEl = document.getElementById("icdContactCandidateName");
    var emailEl = document.getElementById("icdContactEmail");
    var phoneEl = document.getElementById("icdContactPhone");
    var emailBtn = document.getElementById("icdContactEmailBtn");
    var phoneBtn = document.getElementById("icdContactPhoneBtn");
    var modal = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;

    document.querySelectorAll("[data-open-contact-modal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var name = btn.getAttribute("data-candidate") || "Candidate";
        var email = btn.getAttribute("data-email") || "";
        var phone = btn.getAttribute("data-phone") || "";
        
        if (nameEl) nameEl.textContent = name;
        
        if (emailEl) {
            emailEl.textContent = email || "Not provided";
            emailEl.parentElement.parentElement.style.display = email ? "flex" : "none";
        }
        if (phoneEl) {
            phoneEl.textContent = phone || "Not provided";
            phoneEl.parentElement.parentElement.style.display = phone ? "flex" : "none";
        }
        
        if (emailBtn && email) emailBtn.href = "mailto:" + email;
        if (phoneBtn && phone) phoneBtn.href = "tel:" + phone;
        
        if (modal) modal.show();
      });
    });
    
    // Copy to clipboard handlers
    function setupCopy(btn, targetEl) {
        if (!btn || !targetEl) return;
        btn.addEventListener("click", function(e) {
            e.preventDefault();
            var text = targetEl.textContent;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(function() {
                    var oldText = btn.textContent;
                    btn.textContent = "Copied!";
                    setTimeout(function() { btn.textContent = oldText; }, 2000);
                });
            }
        });
    }
    setupCopy(emailBtn, emailEl);
    setupCopy(phoneBtn, phoneEl);
  }

  /* ── NEW: Profile Modal ── */
  function bindProfileModal(token) {
    var modalEl = document.getElementById("icdProfileModal");
    if (!modalEl) return;
    var contentEl = document.getElementById("icdProfileModalContent");
    var modal = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    
    var loaderHtml = `
      <div class="modal-body text-center p-5">
          <div class="spinner-border text-primary" role="status"></div>
          <p class="text-muted mt-3 mb-0">Loading Candidate Profile...</p>
      </div>`;

    document.querySelectorAll("[data-open-profile-modal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var url = btn.getAttribute("data-profile-url");
        if (!url) return;
        if (contentEl) contentEl.innerHTML = loaderHtml;
        if (modal) modal.show();
        
        fetch(url, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": token
          }
        })
        .then(function(res) { return res.json(); })
        .then(function(data) {
          if (data.success && data.html) {
            if (contentEl) contentEl.innerHTML = data.html;
          } else {
            throw new Error(data.error || "Failed to load profile.");
          }
        })
        .catch(function(err) {
          if (contentEl) {
            contentEl.innerHTML = `
              <div class="modal-body text-center p-5">
                <i class="bi bi-exclamation-triangle text-danger fs-1"></i>
                <h5 class="mt-3">Error Loading Profile</h5>
                <p class="text-muted">${err.message}</p>
                <button type="button" class="btn btn-outline-secondary mt-2" data-bs-dismiss="modal">Close</button>
              </div>`;
          }
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var listPage = document.getElementById("icdApplicationsPage");
    var detailPage = document.getElementById("icdApplicationDetail");
    var page = listPage || detailPage;
    if (!page) return;
    var token = csrfToken(page);

    page.querySelectorAll(".icd-status-select").forEach(function (select) {
      bindStatusSelect(select, token);
    });
    page.querySelectorAll("[data-quick-status]").forEach(function (btn) {
      bindQuickStatus(btn, token);
    });
    var detailStatus = document.getElementById("icdDetailStatus");
    if (detailStatus) bindStatusSelect(detailStatus, token);

    page.querySelectorAll("[data-save-notes]").forEach(function (btn) {
      bindNotesSave(btn, page, token);
    });
    page.querySelectorAll("[data-open-resume-modal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openResumeModal({
          candidate: btn.getAttribute("data-resume-candidate") || "",
          job: btn.getAttribute("data-resume-job") || "",
          previewUrl: btn.getAttribute("data-resume-preview") || "",
          downloadUrl: btn.getAttribute("data-resume-download") || "",
          fileName: btn.getAttribute("data-resume-file-name") || "",
          mimeType: btn.getAttribute("data-resume-mime-type") || "",
        });
      });
    });
    bindResumeControls();
    bindOfferModal(token);
    bindNotesModal(token);
    bindScheduleModal(token);
    bindShortlistModal(token);
    bindRejectModal(token);
    bindContactModal(token);
    bindProfileModal(token);
  });
})();
