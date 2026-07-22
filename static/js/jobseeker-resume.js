(function () {
  "use strict";

  var MAX_BYTES = 5 * 1024 * 1024;
  var ALLOWED_EXT = { pdf: true, docx: true };
  var ALLOWED_MIME = {
    "application/pdf": true,
    "application/x-pdf": true,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": true,
  };

  var uploading = false;

  function cfg() {
    return window.JSD_RESUME || {};
  }

  function getCsrfToken() {
    if (cfg().csrfToken) return cfg().csrfToken;
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
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

  function root() {
    return document.getElementById("jsdResumePage");
  }

  function urls() {
    var el = root();
    return {
      upload: el ? el.getAttribute("data-upload-url") : "",
      delete: el ? el.getAttribute("data-delete-url") : "",
      autofill: el ? el.getAttribute("data-autofill-url") : "",
      portal: el ? el.getAttribute("data-portal-api-url") : "",
    };
  }

  function validateResumeFile(file) {
    var ext = file.name.indexOf(".") >= 0 ? file.name.split(".").pop().toLowerCase() : "";
    if (!ALLOWED_EXT[ext]) return "Only PDF and DOCX resume files are allowed.";
    if (file.size > MAX_BYTES) return "Resume size cannot exceed 5 MB.";
    if (file.size <= 0) return "The selected file is empty.";
    var mime = (file.type || "").toLowerCase();
    if (mime && !ALLOWED_MIME[mime]) return "Invalid resume file type. Upload a PDF or DOCX file.";
    return "";
  }

  function showError(message) {
    var el = document.getElementById("jsdResumeError");
    if (!el) return;
    el.textContent = message;
    el.hidden = !message;
  }

  function showSelected(name) {
    var el = document.getElementById("jsdResumeSelected");
    if (!el) return;
    el.textContent = name ? "Selected: " + name : "";
    el.hidden = !name;
  }

  function setProgress(pct, visible) {
    var wrap = document.getElementById("jsdResumeProgress");
    var bar = document.getElementById("jsdResumeProgressBar");
    var text = document.getElementById("jsdResumeProgressText");
    if (!wrap || !bar) return;
    wrap.hidden = !visible;
    bar.style.width = Math.min(100, Math.max(0, pct)) + "%";
    if (text) text.textContent = visible ? (pct >= 100 ? "Processing…" : "Uploading… " + pct + "%") : "";
  }

  function uploadResume(file) {
    var url = urls().upload;
    if (!url) return;
    uploading = true;
    setProgress(0, true);

    // Disable upload buttons to prevent duplicate submission
    var uploadBtn  = document.getElementById("jsdResumeUploadBtn");
    var replaceBtn = document.getElementById("jsdResumeReplaceBtn");
    if (uploadBtn)  uploadBtn.disabled  = true;
    if (replaceBtn) replaceBtn.disabled = true;

    var fd = new FormData();
    fd.append("file", file);
    fd.append("resume", file);
    var xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);
    xhr.setRequestHeader("X-CSRFToken", getCsrfToken());
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    xhr.upload.addEventListener("progress", function (e) {
      if (!e.lengthComputable) return;
      setProgress(Math.round((e.loaded / e.total) * 100), true);
    });
    xhr.addEventListener("load", function () {
      uploading = false;
      setProgress(100, false);
      if (uploadBtn)  uploadBtn.disabled  = false;
      if (replaceBtn) replaceBtn.disabled = false;

      var payload;
      try {
        payload = JSON.parse(xhr.responseText || "{}");
      } catch (err) {
        showError("Unable to upload your resume. Please try again.");
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300 && payload.success) {
        // Launch AI Analysis Progress Modal immediately
        if (window.AIProgressModal) {
          window.AIProgressModal.open({
            onComplete: function (trustScore, riskLevel) {
              refreshDashboardUI(function () {
                notify("success", "Resume analysis complete. Your dashboard has been updated.");
                checkAndDisplayTrustWarningPopup();
              });
            },
            onError: function (errorMessage) {
              refreshDashboardUI(function () {
                checkAndDisplayTrustWarningPopup();
              });
            },
          });
        } else {
          // Fallback: no modal — just poll and refresh
          notify("success", "Resume uploaded. Running AI analysis...");
          pollTrustAnalysisAndRefresh();
        }
        return;
      }
      showError((payload && payload.error) || "Unable to upload your resume. Please try again.");
    });
    xhr.addEventListener("error", function () {
      uploading = false;
      setProgress(0, false);
      if (uploadBtn)  uploadBtn.disabled  = false;
      if (replaceBtn) replaceBtn.disabled = false;
      showError("Network error. Please check your connection and try again.");
    });
    xhr.send(fd);
  }

  function deleteResume() {
    var url = urls().delete;
    if (!url) return;
    fetch(url, {
      method: "DELETE",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
      },
    })
      .then(function (res) {
        return res.text().then(function (text) {
          var payload = {};
          try {
            payload = text ? JSON.parse(text) : {};
          } catch (e) {
            throw new Error("Invalid response from server.");
          }
          if (!res.ok || !payload.success) {
            throw new Error((payload && (payload.message || payload.error)) || "Unable to delete resume.");
          }
          return payload;
        });
      })
      .then(function (payload) {
        notify("success", payload.message || "Resume removed successfully.");
        refreshDashboardUI();
      })
      .catch(function (err) {
        notify("error", err.message || "Unable to delete resume.");
      });
  }

  function handleFile(file) {
    showError("");
    var validation = validateResumeFile(file);
    if (validation) {
      showError(validation);
      return;
    }
    showSelected(file.name);
    uploadResume(file);
  }

  function initScoreRing() {
    document.querySelectorAll(".jsd-res-score-ring").forEach(function (el) {
      var score = parseInt(el.getAttribute("data-score") || "0", 10);
      el.style.setProperty("--score", String(Math.min(100, Math.max(0, score))));
    });
  }

  function initUpload() {
    var input = document.getElementById("jsdResumeInput");
    var uploadBtn = document.getElementById("jsdResumeUploadBtn");
    var replaceBtn = document.getElementById("jsdResumeReplaceBtn");
    var deleteBtn = document.getElementById("jsdResumeDeleteBtn");
    var dropzone = document.getElementById("jsdResumeDropzone");

    function openPicker() {
      if (uploading || !input) return;
      showError("");
      input.click();
    }

    if (uploadBtn) uploadBtn.addEventListener("click", openPicker);
    if (replaceBtn) replaceBtn.addEventListener("click", openPicker);

    if (input) {
      input.addEventListener("change", function () {
        var file = input.files && input.files[0];
        input.value = "";
        if (file) handleFile(file);
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", async function () {
        if (uploading) return;
        var ask = await confirmAction({
          title: "Delete Resume",
          message: "Remove your resume? This action cannot be undone.",
          confirmText: "Delete Resume",
          cancelText: "Cancel",
          variant: "danger",
        });
        if (!ask) return;
        deleteResume();
      });
    }

    if (dropzone) {
      dropzone.addEventListener("click", function (e) {
        if (e.target.closest("button")) return;
        openPicker();
      });
      dropzone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropzone.classList.add("is-dragover");
      });
      dropzone.addEventListener("dragleave", function () {
        dropzone.classList.remove("is-dragover");
      });
      dropzone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropzone.classList.remove("is-dragover");
        var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
        if (file) handleFile(file);
      });
    }
  }

  function initAutofill() {
    var btn = document.getElementById("jsdResumeAutofillBtn");
    if (!btn) return;
    btn.addEventListener("click", async function () {
      var ok = await confirmAction({
        title: "Apply Parsed Resume Data",
        message: "Apply parsed resume data to your Job Seeker profile?",
        confirmText: "Apply to Profile",
        cancelText: "Cancel",
        variant: "info",
      });
      if (!ok) return;

      btn.disabled = true;
      var originalHtml = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Applying...';

      var body = new FormData();
      fetch(urls().autofill, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json",
        },
        body: body,
      })
        .then(function (res) {
          return res.text().then(function (text) {
            var payload = {};
            try {
              payload = text ? JSON.parse(text) : {};
            } catch (e) {
              throw new Error("Invalid server response format.");
            }
            if (!res.ok || payload.success === false) {
              var errorMsg =
                payload.message ||
                (payload.errors && (payload.errors.detail || payload.errors.error)) ||
                "Unable to apply resume data to profile.";
              throw new Error(errorMsg);
            }
            return payload;
          });
        })
        .then(function (payload) {
          var msg = payload.message || "Profile updated successfully from resume.";
          if (payload.updated_sections && payload.updated_sections.length > 0) {
            msg += " (Updated: " + payload.updated_sections.join(", ") + ")";
          }
          notify("success", msg);
          refreshDashboardUI();
        })
        .catch(function (err) {
          notify("error", err.message || "Unable to apply resume data.");
          btn.disabled = false;
          btn.innerHTML = originalHtml;
        });
    });
  }

  function refreshDashboardUI(callback) {
    fetch(window.location.href)
      .then(function (res) {
        return res.text();
      })
      .then(function (html) {
        var parser = new DOMParser();
        var doc = parser.parseFromString(html, "text/html");

        var oldLayout = document.querySelector(".jsd-res-layout");
        var newLayout = doc.querySelector(".jsd-res-layout");
        if (oldLayout && newLayout) {
          oldLayout.innerHTML = newLayout.innerHTML;
        }

        var oldSummary = document.querySelector(".jsd-res-summary");
        var newSummary = doc.querySelector(".jsd-res-summary");
        if (oldSummary && newSummary) {
          oldSummary.innerHTML = newSummary.innerHTML;
        }

        initScoreRing();
        initUpload();
        initAutofill();
        initTrustAnalysisHandlers();
        checkAndDisplayTrustWarningPopup();

        if (callback) callback();
      })
      .catch(function (err) {
        console.error("Failed to refresh dashboard UI dynamically:", err);
      });
  }

  function pollTrustAnalysisAndRefresh() {
    var maxAttempts = 15;
    var attempt = 0;

    var contentEl = document.getElementById("trustAnalysisContent");
    var loadingEl = document.getElementById("trustAnalysisLoading");
    if (contentEl) contentEl.style.opacity = "0.4";
    if (loadingEl) loadingEl.style.display = "block";

    function check() {
      attempt++;
      fetch("/api/resume-trust/report/", {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json"
        }
      })
        .then(function (res) { return res.json(); })
        .then(function (payload) {
          if (payload.success && payload.data && payload.data.has_analysis) {
            var status = (payload.data.status || "").toUpperCase();
            if (status !== "PENDING" && status !== "PROCESSING") {
              refreshDashboardUI(function () {
                notify("success", "Trust analysis complete.");
              });
              return;
            }
          }
          if (attempt < maxAttempts) {
            window.setTimeout(check, 2000);
          } else {
            refreshDashboardUI();
          }
        })
        .catch(function () {
          if (attempt < maxAttempts) {
            window.setTimeout(check, 2000);
          } else {
            refreshDashboardUI();
          }
        });
    }

    window.setTimeout(check, 1500);
  }

  function initTrustAnalysisHandlers() {
    var btnView = document.getElementById("btnViewTrustReport");
    var btnRefresh = document.getElementById("btnRefreshTrustAnalysis");

    if (btnView) {
      btnView.addEventListener("click", function () {
        btnView.disabled = true;
        var origHtml = btnView.innerHTML;
        btnView.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Loading...';

        fetch("/api/resume-trust/report/", {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json"
          }
        })
          .then(function (res) { return res.json(); })
          .then(function (payload) {
            btnView.disabled = false;
            btnView.innerHTML = origHtml;
            if (payload.success && payload.data) {
              var bodyEl = document.getElementById("trustReportModalBody");
              if (bodyEl) {
                bodyEl.innerHTML = buildFullReportHtml(payload.data);
              }
              var myModal = new bootstrap.Modal(document.getElementById("trustReportModal"));
              myModal.show();
            } else {
              notify("error", payload.error || "Unable to load trust report.");
            }
          })
          .catch(function (err) {
            btnView.disabled = false;
            btnView.innerHTML = origHtml;
            notify("error", "Failed to retrieve trust report.");
          });
      });
    }

    if (btnRefresh) {
      btnRefresh.addEventListener("click", function () {
        btnRefresh.disabled = true;
        var origHtml = btnRefresh.innerHTML;
        btnRefresh.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Scanning...';

        var contentEl = document.getElementById("trustAnalysisContent");
        var loadingEl = document.getElementById("trustAnalysisLoading");
        if (contentEl) contentEl.style.opacity = "0.4";
        if (loadingEl) loadingEl.style.display = "block";

        fetch("/api/resume-trust/analyze/", {
          method: "POST",
          headers: {
            "X-CSRFToken": getCsrfToken(),
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
            "Content-Type": "application/json"
          },
          body: JSON.stringify({})
        })
          .then(function (res) { return res.json(); })
          .then(function (payload) {
            btnRefresh.disabled = false;
            btnRefresh.innerHTML = origHtml;
            if (contentEl) contentEl.style.opacity = "1";
            if (loadingEl) loadingEl.style.display = "none";

            if (payload.success) {
              notify("success", "Trust analysis completed successfully.");
              refreshDashboardUI();
            } else {
              notify("error", payload.error || "Trust scan failed.");
            }
          })
          .catch(function (err) {
            btnRefresh.disabled = false;
            btnRefresh.innerHTML = origHtml;
            if (contentEl) contentEl.style.opacity = "1";
            if (loadingEl) loadingEl.style.display = "none";
            notify("error", "Network error running trust scan.");
          });
      });
    }
  }

  function buildFullReportHtml(report) {
    if (!report || !report.has_analysis) {
      return '<div class="alert alert-info">No trust analysis report available.</div>';
    }

    var scoreClass = "badge-risk-low";
    if (report.risk_level === "MEDIUM") scoreClass = "badge-risk-medium";
    if (report.risk_level === "HIGH") scoreClass = "badge-risk-high";
    if (report.risk_level === "CRITICAL") scoreClass = "badge-risk-critical";

    var html = "";
    
    html += '<div class="row align-items-center mb-4">';
    html += '  <div class="col-md-6">';
    html += '    <div class="d-flex align-items-center gap-3">';
    html += '      <div class="jsd-res-score-ring" style="--score: ' + report.trust_score + '; width: 4.5rem; height: 4.5rem;">';
    html += '        <strong style="font-size: 1.25rem;">' + report.trust_score + '%</strong>';
    html += '      </div>';
    html += '      <div>';
    html += '        <h4 class="mb-1 fw-bold text-dark" style="font-size: 1.1rem;">Trust Score</h4>';
    html += '        <span class="badge ' + scoreClass + '" style="font-size: 0.75rem; font-weight: 700; padding: 0.3em 0.6em; border-radius: 4px;">' + report.risk_level + ' RISK</span>';
    html += '      </div>';
    html += '    </div>';
    html += '  </div>';
    html += '  <div class="col-md-6 text-md-end mt-3 mt-md-0">';
    html += '    <p class="mb-1 text-muted small"><strong>Scan Status:</strong> <span style="text-transform: uppercase;">' + report.status + '</span></p>';
    html += '    <p class="mb-1 text-muted small"><strong>Scanned On:</strong> ' + (report.created_at || "—") + '</p>';
    html += '    <p class="mb-0 text-muted small"><strong>Version:</strong> v' + report.resume_version + ' · <strong>Duration:</strong> ' + report.analysis_duration_ms + ' ms</p>';
    html += '  </div>';
    html += '</div>';

    html += '<div class="p-3 bg-light rounded border mb-4">';
    html += '  <h6 class="fw-bold mb-2 small text-uppercase text-muted" style="letter-spacing: 0.05em;">AI Assessment &amp; Action Recommendation</h6>';
    html += '  <p class="mb-0 text-dark small" style="line-height: 1.5;">' + (report.recommendation_message || report.ai_explanation) + '</p>';
    if (report.ai_explanation && report.recommendation_message) {
      html += '  <p class="mt-2 mb-0 text-muted small" style="line-height: 1.5; font-style: italic;">' + report.ai_explanation + '</p>';
    }
    html += '</div>';

    html += '<h5 class="fw-bold text-dark mb-3" style="font-size: 1rem;"><i class="bi bi-exclamation-circle text-warning"></i> Identified Warnings &amp; Potential Issues (' + report.warning_count + ')</h5>';

    if (!report.warnings || report.warnings.length === 0) {
      html += '<div class="alert alert-success d-flex align-items-center gap-2 py-3 mb-4">';
      html += '  <i class="bi bi-patch-check-fill fs-5"></i>';
      html += '  <div class="small fw-semibold">No trust flags or suspicious patterns were detected in this resume.</div>';
      html += '</div>';
    } else {
      html += '<div class="mb-4">';
      report.warnings.forEach(function (w) {
        var sevClass = "badge-risk-low";
        if (w.severity === "MEDIUM") sevClass = "badge-risk-medium";
        if (w.severity === "HIGH") sevClass = "badge-risk-high";
        if (w.severity === "CRITICAL") sevClass = "badge-risk-critical";

        html += '<div class="trust-warning-card">';
        html += '  <div class="d-flex align-items-start justify-content-between gap-3 flex-wrap mb-2">';
        html += '    <div class="d-flex align-items-center gap-2">';
        html += '      <span class="trust-category-pill">' + (w.category || "General") + '</span>';
        html += '      <h6 class="mb-0 fw-bold text-dark small">' + w.title + '</h6>';
        html += '    </div>';
        html += '    <span class="badge ' + sevClass + '" style="font-size: 0.65rem; padding: 0.25em 0.5em; border-radius: 4px;">' + w.severity + '</span>';
        html += '  </div>';
        html += '  <p class="mb-2 text-muted small" style="line-height: 1.4;">' + w.description + '</p>';
        if (w.evidence_snippet) {
          html += '  <div class="p-2 bg-dark text-white rounded font-monospace small mb-2" style="font-size: 0.75rem; border-left: 3px solid var(--jsd-primary); white-space: pre-wrap; word-break: break-all;">';
          html += '    Evidence: ' + w.evidence_snippet;
          html += '  </div>';
        }
        if (w.recommendation) {
          html += '  <p class="mb-0 text-success small" style="font-size: 0.8rem; font-weight: 600;"><i class="bi bi-lightbulb-fill"></i> Recommendation: ' + w.recommendation + '</p>';
        }
        html += '</div>';
      });
      html += '</div>';
    }

    if (report.category_scores && Object.keys(report.category_scores).length > 0) {
      html += '<h5 class="fw-bold text-dark mb-3" style="font-size: 1rem;"><i class="bi bi-bar-chart-line text-primary"></i> Category Risk Breakdown</h5>';
      html += '<div class="table-responsive">';
      html += '<table class="table table-bordered table-sm small align-middle mb-0">';
      html += '  <thead class="table-light">';
      html += '    <tr>';
      html += '      <th class="fw-bold py-2">Category</th>';
      html += '      <th class="text-center fw-bold py-2">Flags</th>';
      html += '      <th class="text-center fw-bold py-2">Raw Penalty</th>';
      html += '      <th class="text-center fw-bold py-2">Weighted Penalty</th>';
      html += '    </tr>';
      html += '  </thead>';
      html += '  <tbody>';
      for (var cat in report.category_scores) {
        var score = report.category_scores[cat];
        html += '    <tr>';
        html += '      <td class="fw-semibold py-2">' + cat + '</td>';
        html += '      <td class="text-center py-2">' + score.warning_count + '</td>';
        html += '      <td class="text-center py-2">' + score.raw_penalty + '</td>';
        html += '      <td class="text-center py-2">' + score.weighted_penalty + '</td>';
        html += '    </tr>';
      }
      html += '  </tbody>';
      html += '</table>';
      html += '</div>';
    }

    return html;
  }

  function checkAndDisplayTrustWarningPopup() {
    var modalEl = document.getElementById("trustWarningModal");
    var unverifiedModalEl = document.getElementById("unverifiedResumeModal");

    fetch("/api/resume-trust/report/", {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json"
      }
    })
      .then(function (res) { return res.json(); })
      .then(function (payload) {
        if (!payload.success || !payload.data) return;
        var data = payload.data;
        var fileId = data.stored_file_id || data.id || "v" + (data.resume_version || 1);

        // 1. Check Unverified / Failed Resume Popup
        if ((data.status === "FAILED" || data.show_unverified_popup) && unverifiedModalEl) {
          var unverifiedDismissKey = "edunaukri_trust_unverified_dismiss_" + fileId;
          if (localStorage.getItem(unverifiedDismissKey) !== "true") {
            var unverifiedModal = bootstrap.Modal.getInstance(unverifiedModalEl) || new bootstrap.Modal(unverifiedModalEl);
            unverifiedModal.show();

            var dismissUnverified = function () {
              localStorage.setItem(unverifiedDismissKey, "true");
              unverifiedModal.hide();
            };

            var btnUploadNew = document.getElementById("btnUnverifiedUploadNew");
            var btnContinue = document.getElementById("btnUnverifiedContinueAnyway");
            var btnCancel = document.getElementById("btnUnverifiedCancel");
            var btnClose = document.getElementById("btnUnverifiedModalClose");

            if (btnUploadNew) {
              btnUploadNew.onclick = function () {
                dismissUnverified();
                var uploadBtn = document.getElementById("jsdResumeUploadBtn");
                if (uploadBtn) uploadBtn.click();
              };
            }
            if (btnContinue) btnContinue.onclick = dismissUnverified;
            if (btnCancel) btnCancel.onclick = dismissUnverified;
            if (btnClose) btnClose.onclick = dismissUnverified;
            return;
          }
        }

        // 2. Check Low Score Warning Popup
        if (!modalEl || !data.has_analysis) return;
        var threshold = data.popup_trust_threshold || 70;
        
        if (data.trust_score >= threshold && !data.show_warning_popup) return;

        var dismissKey = "edunaukri_trust_warn_dismiss_" + fileId;

        if (localStorage.getItem(dismissKey) === "true") return;

        var warningModal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        warningModal.show();

        var btnReview = document.getElementById("btnWarningReviewResume");
        var btnUpload = document.getElementById("btnWarningUploadNew");
        var btnContinue = document.getElementById("btnWarningContinueAnyway");
        var btnClose = document.getElementById("btnWarningModalClose");

        function dismiss() {
          localStorage.setItem(dismissKey, "true");
          warningModal.hide();
        }

        if (btnReview) {
          btnReview.onclick = function () {
            dismiss();
            var btnView = document.getElementById("btnViewTrustReport");
            if (btnView) btnView.click();
          };
        }

        if (btnUpload) {
          btnUpload.onclick = function () {
            dismiss();
            var uploadBtn = document.getElementById("jsdResumeUploadBtn");
            if (uploadBtn) uploadBtn.click();
          };
        }

        if (btnContinue) {
          btnContinue.onclick = function () {
            dismiss();
          };
        }

        if (btnClose) {
          btnClose.onclick = function () {
            dismiss();
          };
        }
      })
      .catch(function (err) {
        console.error("Error checking trust warning popup status:", err);
      });
  }

  // Expose refreshDashboardUI globally so the AIProgressModal can call it
  window.JSD_refreshDashboard = function () {
    refreshDashboardUI(function () {
      checkAndDisplayTrustWarningPopup();
    });
  };

  document.addEventListener("DOMContentLoaded", function () {
    initScoreRing();
    initUpload();
    initAutofill();
    initTrustAnalysisHandlers();
    checkAndDisplayTrustWarningPopup();
  });
})();
