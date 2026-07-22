/**
 * ai-progress-modal.js
 * Shared AI Resume Analysis Progress Modal controller.
 * Used by both IT Jobseeker and Faculty Professor resume dashboards.
 */
(function (global) {
  "use strict";

  var POLL_INTERVAL_MS   = 1800;
  var MAX_POLL_ATTEMPTS  = 40;          // ~72 s max
  var STALL_THRESHOLD_MS = 35000;       // show "taking longer" after 35 s
  var PROGRESS_API       = "/api/resume-trust/progress/";

  // Ordered stage definitions (mirrors backend ANALYSIS_STAGES)
  var STAGES = [
    { key: "UPLOAD_COMPLETED",        label: "Resume uploaded successfully",              pct: 12  },
    { key: "PDF_VALIDATED",           label: "File integrity & PDF readability verified",  pct: 24  },
    { key: "TEXT_EXTRACTED",          label: "Text extracted from document",               pct: 36  },
    { key: "RESUME_DETECTED",         label: "Resume structure & layout detected",         pct: 48  },
    { key: "AI_ANALYSIS_STARTED",     label: "Identifying candidate information",          pct: 57  },
    { key: "SKILLS_ANALYZED",         label: "Detecting skills & technical stack",         pct: 66  },
    { key: "EDUCATION_ANALYZED",      label: "Detecting education & qualifications",       pct: 72  },
    { key: "EXPERIENCE_ANALYZED",     label: "Detecting work experience & projects",       pct: 78  },
    { key: "TRUST_ANALYSIS_COMPLETED","label":"Performing Resume Trust Analysis",          pct: 87  },
    { key: "MATCH_SCORE_COMPLETED",   label: "Calculating Resume Match Score",             pct: 93  },
    { key: "PROFILE_UPDATED",         label: "Synchronizing profile information",          pct: 96  },
    { key: "ANALYSIS_COMPLETED",      label: "Analysis complete",                          pct: 100 },
  ];

  var _modal        = null;   // Bootstrap Modal instance
  var _pollTimer    = null;
  var _attempt      = 0;
  var _startMs      = 0;
  var _localPct     = 0;      // local animation pct (always moves forward)
  var _onComplete   = null;   // callback(trustScore, riskLevel)
  var _onError      = null;   // callback(errorMessage)
  var _beUnloadHandler = null;

  /* ------------------------------------------------------------------ */
  /*  DOM helpers                                                         */
  /* ------------------------------------------------------------------ */
  function el(id) { return document.getElementById(id); }

  function riskClass(level) {
    var map = { LOW: "text-success", MEDIUM: "text-warning", HIGH: "text-danger", CRITICAL: "text-danger" };
    return map[(level || "").toUpperCase()] || "text-muted";
  }

  /* ------------------------------------------------------------------ */
  /*  Build modal HTML (injected once into document body)                */
  /* ------------------------------------------------------------------ */
  function ensureModalDOM() {
    if (el("aiAnalysisProgressModal")) return;

    var stageHTML = STAGES.map(function (s, i) {
      return (
        '<li class="ai-stage-item" id="ai-stage-' + s.key + '" role="listitem">' +
          '<span class="ai-stage-icon ai-stage-icon--wait" aria-hidden="true"></span>' +
          '<span class="ai-stage-label">' + s.label + "</span>" +
        "</li>"
      );
    }).join("");

    var html = [
      '<div class="modal fade" id="aiAnalysisProgressModal" tabindex="-1"',
      '     aria-labelledby="aiAnalysisProgressModalLabel" aria-modal="true" role="dialog"',
      '     data-bs-backdrop="static" data-bs-keyboard="false">',
      '  <div class="modal-dialog modal-dialog-centered modal-lg">',
      '    <div class="modal-content ai-pm-card">',

      /* === PROCESSING VIEW === */
      '      <div id="ai-pm-processing">',
      '        <div class="ai-pm-header">',
      '          <div class="ai-scan-wrap">',
      '            <div class="ai-pulse-ring ai-pulse-ring--1"></div>',
      '            <div class="ai-pulse-ring ai-pulse-ring--2"></div>',
      '            <div class="ai-pulse-ring ai-pulse-ring--3"></div>',
      '            <div class="ai-brain-icon" aria-hidden="true">',
      '              <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">',
      '                <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-1.66Z"/>',
      '                <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-1.66Z"/>',
      '              </svg>',
      '            </div>',
      '          </div>',
      '          <h2 class="ai-pm-title" id="aiAnalysisProgressModalLabel">AI Resume Analysis in Progress</h2>',
      '          <p class="ai-pm-subtitle">Please wait while our AI engine analyzes your resume.<br>',
      '            <strong>Do not close this window.</strong></p>',
      '          <p class="ai-pm-eta" id="ai-pm-eta">',
      '            <i class="bi bi-clock me-1"></i>Usually takes <strong>10–30 seconds</strong> depending on resume size.',
      '          </p>',
      '        </div>',

      '        <div class="ai-pm-body">',
      '          <div class="ai-pm-progress-wrap" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" id="ai-pm-progress-wrap">',
      '            <div class="d-flex justify-content-between align-items-center mb-1">',
      '              <span class="ai-pm-progress-label">Resume Analysis</span>',
      '              <span class="ai-pm-progress-pct" id="ai-pm-pct">0%</span>',
      '            </div>',
      '            <div class="ai-pm-progress-track">',
      '              <div class="ai-pm-progress-bar" id="ai-pm-bar" style="width:0%"></div>',
      '            </div>',
      '          </div>',
      '          <ul class="ai-stage-list" id="ai-stage-list" aria-label="Analysis stages">' + stageHTML + "</ul>",
      '        </div>',
      '      </div>',

      /* === SUCCESS VIEW === */
      '      <div id="ai-pm-success" style="display:none;">',
      '        <div class="ai-pm-result-header ai-pm-result-header--success">',
      '          <div class="ai-pm-result-icon ai-pm-result-icon--success" aria-hidden="true">',
      '            <i class="bi bi-patch-check-fill"></i>',
      '          </div>',
      '          <h2 class="ai-pm-title">Analysis Complete</h2>',
      '          <p class="ai-pm-subtitle">Your resume has been successfully analyzed.</p>',
      '        </div>',
      '        <div class="ai-pm-body">',
      '          <ul class="ai-result-checklist">',
      '            <li><i class="bi bi-check-circle-fill text-success"></i> Resume successfully parsed</li>',
      '            <li><i class="bi bi-check-circle-fill text-success"></i> AI Resume Analysis completed</li>',
      '            <li><i class="bi bi-check-circle-fill text-success"></i> Resume Trust Analysis completed</li>',
      '            <li><i class="bi bi-check-circle-fill text-success"></i> Resume Match Score generated</li>',
      '            <li><i class="bi bi-check-circle-fill text-success"></i> Profile updated successfully</li>',
      '          </ul>',
      '          <div class="ai-result-scores" id="ai-result-scores">',
      '            <div class="ai-score-pill" id="ai-score-trust">',
      '              <span class="ai-score-pill__label">Trust Score</span>',
      '              <span class="ai-score-pill__value" id="ai-score-trust-val">—</span>',
      '            </div>',
      '            <div class="ai-score-pill" id="ai-score-risk">',
      '              <span class="ai-score-pill__label">Risk Level</span>',
      '              <span class="ai-score-pill__value" id="ai-score-risk-val">—</span>',
      '            </div>',
      '          </div>',
      '          <div class="ai-pm-actions">',
      '            <button type="button" class="jsd-btn jsd-btn--primary" id="ai-pm-view-report">',
      '              <i class="bi bi-shield-check me-1"></i>View Trust Report',
      '            </button>',
      '            <button type="button" class="jsd-btn jsd-btn--outline" id="ai-pm-go-dashboard">',
      '              <i class="bi bi-house me-1"></i>Go to Dashboard',
      '            </button>',
      '          </div>',
      '        </div>',
      '      </div>',

      /* === ERROR VIEW === */
      '      <div id="ai-pm-error" style="display:none;">',
      '        <div class="ai-pm-result-header ai-pm-result-header--error">',
      '          <div class="ai-pm-result-icon ai-pm-result-icon--error" aria-hidden="true">',
      '            <i class="bi bi-exclamation-octagon-fill"></i>',
      '          </div>',
      '          <h2 class="ai-pm-title">Resume Analysis Failed</h2>',
      '          <p class="ai-pm-subtitle ai-pm-error-reason" id="ai-pm-error-reason">Unable to analyze the uploaded document.</p>',
      '        </div>',
      '        <div class="ai-pm-body">',
      '          <div class="ai-pm-actions">',
      '            <button type="button" class="jsd-btn jsd-btn--primary" id="ai-pm-upload-another">',
      '              <i class="bi bi-cloud-upload me-1"></i>Upload Another Resume',
      '            </button>',
      '            <button type="button" class="jsd-btn jsd-btn--outline" id="ai-pm-try-again">',
      '              <i class="bi bi-arrow-clockwise me-1"></i>Try Again',
      '            </button>',
      '            <button type="button" class="jsd-btn jsd-btn--outline text-muted" id="ai-pm-continue-anyway">',
      '              Continue Anyway',
      '            </button>',
      '          </div>',
      '        </div>',
      '      </div>',

      '    </div>',
      '  </div>',
      '</div>',
    ].join("\n");

    var wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    document.body.appendChild(wrapper.firstElementChild);
    _wireStaticButtons();
  }

  /* ------------------------------------------------------------------ */
  /*  Wire static action buttons                                         */
  /* ------------------------------------------------------------------ */
  function _wireStaticButtons() {
    var btnViewReport = el("ai-pm-view-report");
    var btnGo        = el("ai-pm-go-dashboard");
    var btnUpload    = el("ai-pm-upload-another");
    var btnTry       = el("ai-pm-try-again");
    var btnContinue  = el("ai-pm-continue-anyway");

    if (btnViewReport) {
      btnViewReport.addEventListener("click", function () {
        _closeModal();
        var trustBtn = el("btnViewTrustReport") || el("btnViewTrustReportProf");
        if (trustBtn) trustBtn.click();
      });
    }
    if (btnGo) {
      btnGo.addEventListener("click", function () {
        _closeModal(true);
      });
    }
    if (btnUpload) {
      btnUpload.addEventListener("click", function () {
        _closeModal();
        var uploadBtn = el("jsdResumeUploadBtn");
        if (uploadBtn) uploadBtn.click();
      });
    }
    if (btnTry) {
      btnTry.addEventListener("click", function () {
        _closeModal();
        var uploadBtn = el("jsdResumeUploadBtn");
        if (uploadBtn) uploadBtn.click();
      });
    }
    if (btnContinue) {
      btnContinue.addEventListener("click", function () {
        _closeModal(true);
      });
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Show modal                                                         */
  /* ------------------------------------------------------------------ */
  function open(callbacks) {
    ensureModalDOM();
    _onComplete = (callbacks && callbacks.onComplete) || null;
    _onError    = (callbacks && callbacks.onError) || null;
    _attempt    = 0;
    _startMs    = Date.now();
    _localPct   = 0;

    _resetToProcessingView();

    var modalEl = el("aiAnalysisProgressModal");
    _modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl, { backdrop: "static", keyboard: false });
    _modal.show();

    // Trap page navigation
    _beUnloadHandler = function (e) {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", _beUnloadHandler);

    // Immediately mark first stage done
    _markStageCompleted("UPLOAD_COMPLETED");
    _setProgress(12);

    // Start polling
    _poll();
  }

  /* ------------------------------------------------------------------ */
  /*  Reset UI to processing view                                        */
  /* ------------------------------------------------------------------ */
  function _resetToProcessingView() {
    var pv = el("ai-pm-processing");
    var sv = el("ai-pm-success");
    var ev = el("ai-pm-error");
    if (pv) pv.style.display = "";
    if (sv) sv.style.display = "none";
    if (ev) ev.style.display = "none";

    // Reset all stage icons
    STAGES.forEach(function (s) {
      var li = el("ai-stage-" + s.key);
      if (!li) return;
      li.className = "ai-stage-item";
      var ico = li.querySelector(".ai-stage-icon");
      if (ico) { ico.className = "ai-stage-icon ai-stage-icon--wait"; ico.innerHTML = ""; }
    });
    _setProgress(0);
  }

  /* ------------------------------------------------------------------ */
  /*  Progress bar update                                                */
  /* ------------------------------------------------------------------ */
  function _setProgress(pct) {
    pct = Math.min(100, Math.max(0, pct));
    _localPct = Math.max(_localPct, pct); // only ever increases
    var bar  = el("ai-pm-bar");
    var pctEl = el("ai-pm-pct");
    var wrap  = el("ai-pm-progress-wrap");
    if (bar)  bar.style.width  = _localPct + "%";
    if (pctEl) pctEl.textContent = _localPct + "%";
    if (wrap)  wrap.setAttribute("aria-valuenow", _localPct);
  }

  /* ------------------------------------------------------------------ */
  /*  Stage helpers                                                      */
  /* ------------------------------------------------------------------ */
  function _markStageCompleted(key) {
    var li = el("ai-stage-" + key);
    if (!li) return;
    li.className = "ai-stage-item ai-stage-item--completed";
    var ico = li.querySelector(".ai-stage-icon");
    if (ico) { ico.className = "ai-stage-icon ai-stage-icon--done"; ico.innerHTML = "✓"; }
  }

  function _markStageActive(key) {
    var li = el("ai-stage-" + key);
    if (!li) return;
    li.className = "ai-stage-item ai-stage-item--active";
    var ico = li.querySelector(".ai-stage-icon");
    if (ico) { ico.className = "ai-stage-icon ai-stage-icon--spin"; ico.innerHTML = ""; }
    // Scroll stage into view inside modal
    li.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function _applyStages(completedKeys, currentKey) {
    STAGES.forEach(function (s) {
      if (completedKeys.indexOf(s.key) !== -1) {
        _markStageCompleted(s.key);
      } else if (s.key === currentKey) {
        _markStageActive(s.key);
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /*  Polling logic                                                      */
  /* ------------------------------------------------------------------ */
  function _poll() {
    clearTimeout(_pollTimer);
    _attempt++;

    // "Taking longer" message
    var elapsed = Date.now() - _startMs;
    var etaEl = el("ai-pm-eta");
    if (etaEl && elapsed > STALL_THRESHOLD_MS) {
      etaEl.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>' +
        'This analysis is taking longer than usual. <strong>Please wait</strong> while we complete the verification.';
    }

    fetch(PROGRESS_API, {
      headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (!data.success) { _handleError("Resume analysis service unavailable."); return; }

        var status = (data.status || "").toUpperCase();

        // Prevent race condition: if the backend returned a FAILED or COMPLETED result
        // from an *older* analysis (before we opened this modal), ignore it and keep polling.
        // The new analysis row might not be created until step 4 of the pipeline.
        if (data.created_at_ms) {
          // Give a 2000ms buffer in case of slight clock skew
          if (data.created_at_ms < _startMs - 2000) {
            status = "PROCESSING"; // Force it to keep waiting
          }
        }

        if (status === "COMPLETED") {
          _applyStages(data.completed_keys || [], null);
          _setProgress(100);
          _showSuccess(data.trust_score, data.risk_level);
          return;
        }

        if (status === "FAILED") {
          _handleError(data.error_message || "Resume analysis could not be completed.");
          return;
        }

        // Still processing
        _applyStages(data.completed_keys || [], data.current_stage);
        _setProgress(data.percentage || _localPct + 3);

        if (_attempt < MAX_POLL_ATTEMPTS) {
          _pollTimer = setTimeout(_poll, POLL_INTERVAL_MS);
        } else {
          // Timed out — still refresh UI
          _applyStages([].concat(STAGES.map(function(s){ return s.key; })), null);
          _setProgress(100);
          _showSuccess(null, null);
        }
      })
      .catch(function () {
        if (_attempt < MAX_POLL_ATTEMPTS) {
          _pollTimer = setTimeout(_poll, POLL_INTERVAL_MS);
        }
      });
  }

  /* ------------------------------------------------------------------ */
  /*  Success view                                                       */
  /* ------------------------------------------------------------------ */
  function _showSuccess(trustScore, riskLevel) {
    clearTimeout(_pollTimer);
    _removeBeforeUnload();

    var pv = el("ai-pm-processing");
    var sv = el("ai-pm-success");
    if (pv) pv.style.display = "none";
    if (sv) sv.style.display = "";

    var trustEl = el("ai-score-trust-val");
    var riskEl  = el("ai-score-risk-val");
    if (trustEl) {
      trustEl.textContent = trustScore != null ? trustScore + "%" : "—";
    }
    if (riskEl && riskLevel) {
      riskEl.textContent  = riskLevel;
      riskEl.className    = "ai-score-pill__value " + riskClass(riskLevel);
    }

    if (_onComplete) _onComplete(trustScore, riskLevel);
  }

  /* ------------------------------------------------------------------ */
  /*  Error view                                                         */
  /* ------------------------------------------------------------------ */
  function _handleError(message) {
    clearTimeout(_pollTimer);
    _removeBeforeUnload();

    var pv = el("ai-pm-processing");
    var ev = el("ai-pm-error");
    if (pv) pv.style.display = "none";
    if (ev) ev.style.display = "";

    var reasonEl = el("ai-pm-error-reason");
    if (reasonEl) reasonEl.textContent = message || "Unable to analyze the uploaded document.";

    if (_onError) _onError(message);
  }

  /* ------------------------------------------------------------------ */
  /*  Close modal                                                        */
  /* ------------------------------------------------------------------ */
  function _closeModal(andRefresh) {
    _removeBeforeUnload();
    clearTimeout(_pollTimer);
    if (_modal) {
      _modal.hide();
      _modal = null;
    }
    if (andRefresh) {
      // Delegate to the page-level refresh if available
      if (typeof global.JSD_refreshDashboard === "function") {
        global.JSD_refreshDashboard();
      } else {
        window.location.reload();
      }
    }
  }

  function _removeBeforeUnload() {
    if (_beUnloadHandler) {
      window.removeEventListener("beforeunload", _beUnloadHandler);
      _beUnloadHandler = null;
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Public API                                                         */
  /* ------------------------------------------------------------------ */
  global.AIProgressModal = {
    open: open,
  };

})(window);
