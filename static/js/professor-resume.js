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
              if (typeof window.JSD_refreshDashboard === "function") {
                window.JSD_refreshDashboard();
              } else {
                window.location.reload();
              }
            },
            onError: function (errorMessage) {
              if (typeof window.JSD_refreshDashboard === "function") {
                window.JSD_refreshDashboard();
              } else {
                window.setTimeout(function () { window.location.reload(); }, 800);
              }
            },
          });
        } else {
          notify("success", "Resume uploaded successfully.");
          window.setTimeout(function () { window.location.reload(); }, 900);
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
      },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success) throw new Error(payload.error || "Unable to delete resume.");
        notify("success", "Resume removed successfully.");
        window.setTimeout(function () {
          window.location.reload();
        }, 700);
      })
      .catch(function (err) {
        notify("error", err.message);
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
        message: "Apply parsed resume data to your profile?",
        confirmText: "Apply Data",
        cancelText: "Cancel",
        variant: "info",
      });
      if (!ok) return;
      btn.disabled = true;
      var body = new FormData();
      fetch(urls().autofill, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: body,
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (payload) {
          if (!payload.success) throw new Error(payload.error || "Unable to apply resume data.");
          notify("success", payload.message || "Profile updated from resume.");
          window.setTimeout(function () {
            window.location.reload();
          }, 800);
        })
        .catch(function (err) {
          notify("error", err.message);
          btn.disabled = false;
        });
    });
  }

  function initDashboardModals() {
    var btnMatch = document.getElementById("btnOpenMatchModal");
    var btnTrust = document.getElementById("btnOpenTrustModal");
    
    function fetchAndRenderDashboardData(modalId, renderFn, loadingText) {
      var modalEl = document.getElementById(modalId);
      if (!modalEl) return;
      var myModal = new bootstrap.Modal(modalEl);
      myModal.show();
      
      var bodyEl = document.getElementById(modalId + "Body");
      bodyEl.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="text-muted mt-3">' + loadingText + '</p></div>';
      
      fetch(urls().portal, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json"
        }
      })
      .then(function(res) { return res.json(); })
      .then(function(payload) {
        if (payload.success && payload.data) {
          bodyEl.innerHTML = renderFn(payload.data);
          
          var btnView = document.getElementById("btnViewTrustReport");
          if (btnView) {
            btnView.addEventListener("click", function () {
              myModal.hide();
              openFullTrustReportModal();
            });
          }
        } else {
          bodyEl.innerHTML = '<div class="alert alert-danger">Failed to load data.</div>';
        }
      })
      .catch(function(err) {
        bodyEl.innerHTML = '<div class="alert alert-danger">Error loading data.</div>';
      });
    }

    if (btnMatch) {
      btnMatch.addEventListener("click", function() {
        fetchAndRenderDashboardData("matchDashboardModal", renderMatchScoreHtml, "Loading Resume Match Score...");
      });
    }

    if (btnTrust) {
      btnTrust.addEventListener("click", function() {
        fetchAndRenderDashboardData("trustDashboardModal", renderTrustAnalysisHtml, "Loading Resume Trust Analysis...");
      });
    }
  }

  function renderMatchScoreHtml(data) {
    if (!data.match_diagnostics) return '<div class="alert alert-info">No match score data available.</div>';
    
    var html = '<div class="jsd-res-match-container">';
    if (data.trust_report.status === "FAILED" || data.trust_report.trust_score === null || !data.trust_report.has_analysis) {
        html += '<div class="jsd-res-score-ring mb-3" style="--score: 0; border: 2px dashed #dc3545;">';
        html += '<strong style="color: #dc3545; font-size: 1.1rem;">N/A</strong></div>';
        html += '<div class="jsd-res-match-content w-100">';
        html += '<h3 class="text-danger fw-bold fs-6 mb-1"><i class="bi bi-x-circle-fill"></i> Not Available</h3>';
        html += '<p class="text-secondary small mb-2" style="line-height: 1.5;">' + (data.match_diagnostics.reason || "The Resume Match Score could not be calculated because the uploaded document failed the Resume Trust Analysis.") + '</p>';
        if (data.match_diagnostics.possible_reasons) {
            html += '<div class="p-2 bg-light rounded border mb-2"><p class="fw-bold small text-muted mb-1">Possible Reasons:</p><ul class="mb-0 small text-danger ps-3">';
            for (var i=0; i<data.match_diagnostics.possible_reasons.length; i++) {
                html += '<li>' + data.match_diagnostics.possible_reasons[i] + '</li>';
            }
            html += '</ul></div>';
        }
        html += '<p class="mb-0 small text-muted"><i class="bi bi-info-circle"></i> ' + (data.match_diagnostics.recommendation || "Upload a properly formatted academic CV before requesting a Resume Match Score.") + '</p>';
        html += '</div>';
    } else {
        html += '<div class="jsd-res-score-ring mb-3" style="--score: ' + data.match_score + ';">';
        html += '<strong>' + data.match_score + '%</strong></div>';
        html += '<div class="jsd-res-match-content w-100">';
        html += '<h3 class="mb-2">' + (data.match_score >= 80 ? "Excellent Match" : (data.match_score >= 60 ? "Good Match" : "Needs Improvement")) + '</h3>';
        html += '<p class="mb-2 text-dark small">' + (data.match_diagnostics.reason || data.match_explanation) + '</p>';
        
        html += '<div class="d-flex flex-wrap gap-3 my-2 p-2 bg-light rounded border">';
        html += '<div><span class="text-muted small d-block fw-semibold mb-1">Extracted Qualifications &amp; Focus</span><div class="d-flex flex-wrap gap-1">';
        if (data.match_diagnostics.detected_skills && data.match_diagnostics.detected_skills.length > 0) {
            for (var j=0; j<data.match_diagnostics.detected_skills.length; j++) {
                html += '<span class="badge bg-success-subtle text-success border border-success-subtle"><i class="bi bi-check-lg"></i> ' + data.match_diagnostics.detected_skills[j] + '</span>';
            }
        } else {
            html += '<span class="badge bg-secondary">Academic Focus</span>';
        }
        html += '</div></div>';
        
        if (data.match_diagnostics.missing_skills && data.match_diagnostics.missing_skills.length > 0) {
            html += '<div><span class="text-muted small d-block fw-semibold mb-1">Recommended Academic Enhancements</span><div class="d-flex flex-wrap gap-1">';
            for (var k=0; k<data.match_diagnostics.missing_skills.length; k++) {
                html += '<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle"><i class="bi bi-exclamation-triangle"></i> ' + data.match_diagnostics.missing_skills[k] + '</span>';
            }
            html += '</div></div>';
        }
        html += '</div>';

        html += '<div class="d-flex flex-wrap align-items-center justify-content-between mt-2 pt-2 border-top gap-2">';
        html += '<span class="small text-muted"><i class="bi bi-briefcase"></i> Matched Faculty Roles: <strong>' + (data.match_diagnostics.matched_active_jobs || 12) + '</strong></span>';
        html += '<span class="small text-muted"><i class="bi bi-lightbulb"></i> ' + (data.match_diagnostics.recommendation || "") + '</span>';
        html += '</div></div>';
    }
    html += '</div>';
    return html;
  }

  function renderTrustAnalysisHtml(data) {
    if (!data.trust_report) return '<div class="alert alert-info">No trust analysis data available.</div>';
    var tr = data.trust_report;
    var html = '<div id="trustAnalysisContent">';
    
    html += '<div class="row align-items-center mb-3"><div class="col-md-4 text-center">';
    if (tr.status === "FAILED" || tr.trust_score === null) {
        html += '<div class="jsd-res-score-ring m-auto" data-score="0" style="--score: 0; border: 2px dashed #dc3545;"><strong style="color: #dc3545; font-size: 1.1rem;">N/A</strong></div>';
        html += '<div class="mt-2"><span class="badge bg-secondary text-white" style="font-size: 0.8rem; font-weight: 700; padding: 0.35em 0.65em; border-radius: 4px;">NOT EVALUATED</span></div>';
    } else {
        html += '<div class="jsd-res-score-ring m-auto" data-score="' + tr.trust_score + '" style="--score: ' + tr.trust_score + ';"><strong>' + tr.trust_score + '%</strong></div>';
        var rRisk = (tr.risk_level || "LOW").toLowerCase();
        html += '<div class="mt-2"><span class="badge badge-risk-' + rRisk + '" style="font-size: 0.8rem; font-weight: 700; padding: 0.35em 0.65em; border-radius: 4px;">' + (tr.risk_level || "LOW") + ' RISK</span></div>';
    }
    html += '</div><div class="col-md-8"><dl class="jsd-res-data-grid mt-3 mt-md-0" style="grid-template-columns: repeat(2, 1fr); gap: 0.75rem;">';
    html += '<div class="jsd-res-data-item"><dt>Status</dt><dd style="text-transform: uppercase;">' + (tr.status === "FAILED" ? '<span class="text-danger fw-bold"><i class="bi bi-x-circle-fill"></i> ANALYSIS INCOMPLETE</span>' : (tr.status || "SUCCESS")) + '</dd></div>';
    html += '<div class="jsd-res-data-item"><dt>Issues Found</dt><dd>' + (tr.warning_count || 0) + '</dd></div>';
    html += '<div class="jsd-res-data-item"><dt>Resume Version</dt><dd>v' + (tr.resume_version || 1) + '</dd></div>';
    html += '<div class="jsd-res-data-item"><dt>Analysis Duration</dt><dd>' + (tr.analysis_duration_ms || 0) + ' ms</dd></div>';
    html += '<div class="jsd-res-data-item" style="grid-column: span 2;"><dt>Last Analysis</dt><dd>' + (tr.created_at || "—") + '</dd></div>';
    html += '</dl></div></div>';
    
    if (tr.passed_checks || tr.missing_sections || tr.failed_checks) {
        html += '<div class="mt-3 pt-3 border-top"><div class="row g-2 mb-3">';
        if (tr.passed_checks && tr.passed_checks.length > 0) {
            html += '<div class="col-md-6"><div class="p-2 bg-success-subtle rounded border border-success-subtle h-100"><p class="fw-bold small text-success mb-1"><i class="bi bi-check-circle-fill"></i> Passed Checks (' + tr.passed_checks.length + ')</p><div class="d-flex flex-wrap gap-1">';
            for(var p=0; p<tr.passed_checks.length; p++) html += '<span class="badge bg-white text-success border border-success-subtle small"><i class="bi bi-check"></i> ' + tr.passed_checks[p] + '</span>';
            html += '</div></div></div>';
        }
        var hasMissing = (tr.missing_sections && tr.missing_sections.length > 0);
        var hasFailed = (tr.failed_checks && tr.failed_checks.length > 0);
        if (hasMissing || hasFailed) {
            html += '<div class="col-md-6"><div class="p-2 bg-warning-subtle rounded border border-warning-subtle h-100"><p class="fw-bold small text-warning-emphasis mb-1"><i class="bi bi-exclamation-triangle-fill"></i> Missing Sections / Issues</p><div class="d-flex flex-wrap gap-1">';
            if (hasMissing) for(var m=0; m<tr.missing_sections.length; m++) html += '<span class="badge bg-white text-danger border border-danger-subtle small"><i class="bi bi-x"></i> ' + tr.missing_sections[m] + '</span>';
            if (hasFailed) for(var f=0; f<tr.failed_checks.length; f++) html += '<span class="badge bg-white text-danger border border-danger-subtle small"><i class="bi bi-x"></i> ' + tr.failed_checks[f] + '</span>';
            html += '</div></div></div>';
        }
        html += '</div></div>';
    }
    html += '<div class="p-3 bg-light rounded border mb-3"><p class="small text-muted mb-1" style="font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Recommendation</p>';
    html += '<p class="mb-0 text-dark small">';
    if (tr.status === "FAILED") {
        html += '<span class="text-danger fw-medium"><i class="bi bi-exclamation-triangle-fill"></i> ' + (tr.recommendation_message || "Resume could not be analyzed. Please upload a valid candidate resume.") + '</span>';
    } else {
        html += (tr.recommendation_message || "Resume passed all automated checks.");
    }
    html += '</p></div>';
    
    html += '<div class="d-flex gap-2">';
    html += '<button type="button" class="jsd-btn jsd-btn--primary btn-sm" id="btnViewTrustReport"><i class="bi bi-file-earmark-text"></i> View Full Report</button>';
    html += '</div></div>';
    return html;
  }

  function openFullTrustReportModal() {
    var myModal = new bootstrap.Modal(document.getElementById("trustReportModal"));
    var bodyEl = document.getElementById("trustReportModalBody");
    bodyEl.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">Loading full report...</p></div>';
    myModal.show();

    fetch("/api/resume-trust/report/", {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json"
      }
    })
      .then(function (res) { return res.json(); })
      .then(function (payload) {
        if (payload.success && payload.data) {
          if (bodyEl) {
            bodyEl.innerHTML = buildFullReportHtml(payload.data);
          }
        } else {
          notify("error", payload.error || "Unable to load trust report.");
          bodyEl.innerHTML = '<div class="alert alert-danger">Unable to load report.</div>';
        }
      })
      .catch(function (err) {
        notify("error", "Failed to retrieve trust report.");
        bodyEl.innerHTML = '<div class="alert alert-danger">Error retrieving report.</div>';
      });
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

  // Expose reload hook for AIProgressModal
  window.JSD_refreshDashboard = function () {
    window.location.reload();
  };

  document.addEventListener("DOMContentLoaded", function () {
    initScoreRing();
    initUpload();
    initAutofill();
    initDashboardModals();
  });
})();
