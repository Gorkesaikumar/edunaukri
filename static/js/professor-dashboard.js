(function () {
  "use strict";

  var cfg = window.FJD_SAVED_VACANCIES || {};
  var csrfToken =
    cfg.csrfToken ||
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") ||
    "";

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  function notify(type, message) {
    if (window.EduNotify && typeof window.EduNotify.toast === "function") {
      window.EduNotify.toast(type, message);
    }
  }

  function initNotificationsPage() {
    document.querySelectorAll(".fjd-notif-page-mark-form").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (!window.fetch) return;
        e.preventDefault();
        var fd = new FormData(form);
        var item = form.closest(".fjd-notif-list__item");
        fetch(form.action, {
          method: "POST",
          body: fd,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        }).then(function (res) {
          if (!res.ok) return;
          if (item) {
            item.classList.remove("fjd-notif-list__item--unread");
            form.remove();
          }
        });
      });
    });

    var markAllForm = document.getElementById("fjdNotifMarkAllForm");
    if (markAllForm) {
      markAllForm.addEventListener("submit", function (e) {
        if (!window.fetch) return;
        e.preventDefault();
        var fd = new FormData(markAllForm);
        fetch(markAllForm.action, {
          method: "POST",
          body: fd,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        }).then(function (res) {
          if (!res.ok) return;
          document.querySelectorAll(".fjd-notif-list__item--unread").forEach(function (item) {
            item.classList.remove("fjd-notif-list__item--unread");
            var form = item.querySelector(".fjd-notif-page-mark-form");
            if (form) form.remove();
          });
          markAllForm.remove();
        });
      });
    }
  }

  function showResumeRequiredModal() {
    var dashCfg = window.FJD_DASHBOARD || {};
    var modal = document.getElementById("jmResumeRequiredModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "jmResumeRequiredModal";
      modal.style.position = "fixed";
      modal.style.top = "0";
      modal.style.left = "0";
      modal.style.width = "100%";
      modal.style.height = "100%";
      modal.style.zIndex = "9999";
      modal.style.display = "flex";
      modal.style.alignItems = "center";
      modal.style.justifyContent = "center";
      modal.innerHTML = `
        <div role="dialog" aria-labelledby="jmResumeModalTitle" style="max-width: 480px; width: 100%; margin: 20px; padding: 24px; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; text-align: center; position: relative; z-index: 10000;">
            <div style="width: 48px; height: 48px; margin: 0 auto 16px; border-radius: 50%; background: #fef3c7; color: #d97706; border: 1px solid #fde68a; display: flex; align-items: center; justify-content: center; font-size: 20px;">
                <i class="bi bi-file-earmark-text"></i>
            </div>
            <h3 id="jmResumeModalTitle" style="margin-top: 0; font-size: 20px; font-weight: 600; color: #1e293b;">Upload Resume Required</h3>
            <p style="margin-top: 8px; color: #475569; font-size: 14px; line-height: 1.5;">Before applying for this job, you need to upload your latest resume. Once your resume is uploaded successfully, you can continue with your application.</p>
            <div style="display: flex; gap: 12px; justify-content: center; margin-top: 24px;">
                <button type="button" class="fjd-btn fjd-btn--outline" onclick="document.getElementById('jmResumeRequiredModal').style.display = 'none';">Cancel</button>
                <a href="${dashCfg.resumeUrl || '#'}?next=${encodeURIComponent(window.location.href)}" class="fjd-btn fjd-btn--primary">Upload Resume</a>
            </div>
        </div>
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.4); cursor: pointer;" onclick="document.getElementById('jmResumeRequiredModal').style.display = 'none';"></div>
      `;
      document.body.appendChild(modal);
    }
    modal.style.display = "flex";
  }

  function initApplyForms() {
    var form = document.getElementById("professorApplyForm");
    if (!form) return;
    form.addEventListener("submit", function (event) {
      if (!window.fetch) return;
      event.preventDefault();
      fetch(form.action, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken || getCookie("csrftoken"),
        },
        body: new FormData(form),
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (payload) {
          if (payload.success) {
            if (payload.redirect_url) {
              window.location.href = payload.redirect_url;
            } else {
              window.location.reload();
            }
          } else if (payload.code === "RESUME_REQUIRED") {
            showResumeRequiredModal();
          } else if (payload.message || payload.error) {
            notify("error", payload.message || payload.error);
          }
        })
        .catch(function () {
          form.submit();
        });
    });
  }

  async function toggleSavedVacancy(vacancyId, button) {
    const formData = new FormData();
    formData.append("vacancy_id", vacancyId);

    const response = await fetch(cfg.toggleUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken || getCookie("csrftoken"),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: formData,
      credentials: "same-origin",
    });

    const payload = await response.json();
    if (!response.ok || !payload.success) {
      throw new Error(payload.error || "Unable to update saved job.");
    }

    const saved = payload.data?.is_saved;
    button.classList.toggle("is-saved", saved);
    button.setAttribute("aria-pressed", saved ? "true" : "false");
    const icon = button.querySelector("i");
    if (icon) {
      icon.className = saved ? "bi bi-bookmark-fill" : "bi bi-bookmark";
    }

    document.querySelectorAll("[data-saved-jobs-count]").forEach(function (el) {
      el.textContent = payload.data.saved_count;
      el.classList.toggle("d-none", !payload.data.saved_count);
    });

    notify("success", saved ? "Job saved." : "Job removed from saved list.");
  }

  function initDashboardLiveRefresh() {
    var statsRow = document.getElementById("fjdStatsRow");
    if (!statsRow) return;
    var dashCfg = window.FJD_DASHBOARD || {};
    var url = statsRow.getAttribute("data-insights-url") || dashCfg.insightsUrl;
    if (!url) return;

    function refresh(forceLive) {
      fetch(url + (forceLive ? "?live=1" : ""), {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (payload) {
          if (!payload.success || !payload.data) return;
          if (payload.data.stats) {
            payload.data.stats.forEach(function (stat) {
              var card = document.querySelector('.fjd-stat[data-stat-key="' + stat.key + '"]');
              if (!card) return;
              var valueEl = card.querySelector("[data-stat-value]");
              if (valueEl) valueEl.textContent = stat.value;
            });
          }
          document.querySelectorAll("[data-saved-jobs-count]").forEach(function (el) {
            if (payload.data.saved_jobs_count != null) {
              el.textContent = payload.data.saved_jobs_count;
              el.classList.toggle("d-none", !payload.data.saved_jobs_count);
            }
          });
        })
        .catch(function () {});
    }

    refresh(true);
    window.setInterval(function () {
      if (document.visibilityState === "visible") {
        refresh(true);
      }
    }, 60000);
  }

  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-save-vacancy-toggle]");
    if (!button) return;
    event.preventDefault();
    const vacancyId = button.getAttribute("data-vacancy-id");
    if (!vacancyId || !cfg.toggleUrl) return;

    button.disabled = true;
    toggleSavedVacancy(vacancyId, button)
      .catch(function (err) {
        notify("error", err.message || "Save failed.");
      })
      .finally(function () {
        button.disabled = false;
      });
  });

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof window.initPortalDashboardHeader === "function") {
      window.initPortalDashboardHeader();
    }
    initNotificationsPage();
    initDashboardLiveRefresh();
    initProfileCompletionWorkflow();
    initRecentApplicationsSearch();
    initJobsSkeleton();
    initApplyForms();

    document.querySelectorAll(".fjd-progress__bar").forEach(function (bar) {
      const width = bar.style.width;
      bar.style.width = "0%";
      requestAnimationFrame(function () {
        bar.style.width = width;
      });
    });
  });

  function initRecentApplicationsSearch() {
    var searchInput = document.getElementById("fjdAppSearch");
    if (!searchInput) return;
    var rows = document.querySelectorAll(".fjd-table tbody tr");
    var noResults = document.getElementById("fjdNoAppResults");

    searchInput.addEventListener("input", function () {
      var query = searchInput.value.toLowerCase().trim();
      var visibleCount = 0;
      rows.forEach(function (row) {
        var text = row.textContent.toLowerCase();
        if (text.indexOf(query) !== -1) {
          row.style.display = "";
          visibleCount++;
        } else {
          row.style.display = "none";
        }
      });
      if (noResults) {
        noResults.style.display = visibleCount === 0 && rows.length > 0 ? "block" : "none";
      }
    });
  }

  function initJobsSkeleton() {
    var skeleton = document.getElementById("fjdJobsSkeleton");
    var grid = document.getElementById("fjdRecommendedJobs");
    if (!skeleton || !grid) return;
    
    // Briefly show skeleton on load or during dynamic filter transitions
    if (grid.children.length === 0) {
      skeleton.style.display = "grid";
    }
  }

  var CELEBRATION_DURATION_MS = 2600;
  var FADE_OUT_DURATION_MS = 550;

  function initProfileCompletionWorkflow() {
    var triggers = document.querySelectorAll(".fjd-celebration-trigger");
    triggers.forEach(function (hero) {
      if (hero.getAttribute("data-play-celebration") === "true") {
        runCelebration(hero);
      } else if (hero.id === "jsdHeroCard") {
        initHeroProgressAnimation();
      }
    });
  }

  function initHeroProgressAnimation() {
    var bar = document.getElementById("jsdHeroProgressBar");
    var valueEl = document.getElementById("jsdHeroCompletion");
    if (!bar || !valueEl) return;
    var target = parseInt(valueEl.getAttribute("data-target") || "0", 10);
    bar.classList.add("jsd-progress__bar--animated");
    bar.style.width = "0%";
    window.requestAnimationFrame(function () {
      window.setTimeout(function () {
        bar.classList.remove("jsd-progress__bar--animated");
        bar.style.width = Math.min(100, Math.max(0, target)) + "%";
      }, 120);
    });
  }

  function runCelebration(hero) {
    var message = hero.getAttribute("data-celebration-message") || "🎉 Congratulations!";
    var markUrl = hero.getAttribute("data-mark-animation-url") || "";
    var canvas = hero.querySelector("canvas.fjd-confetti-canvas") || document.getElementById("jsdHeroConfetti");

    // Resize canvas to full viewport since it's position:fixed
    if (canvas) {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }

    // Fire confetti blast across full screen
    startConfetti(canvas, CELEBRATION_DURATION_MS);

    // Show success toast after a short delay
    window.setTimeout(function () {
      notify("success", message);
    }, 400);

    // Mark as shown and clean up
    window.setTimeout(function () {
      markCelebrationShown(markUrl).finally(function () {
        if (hero && hero.parentNode) {
          hero.remove();
        }
      });
    }, CELEBRATION_DURATION_MS);
  }

  function markCelebrationShown(url) {
    if (!url || !window.fetch) return Promise.resolve();
    return fetch(url, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken || getCookie("csrftoken"),
      },
      credentials: "same-origin",
    }).catch(function () {});
  }

  function fadeOutHeroCard(hero) {
    var startHeight = hero.offsetHeight;
    hero.style.maxHeight = startHeight + "px";
    hero.classList.remove("jsd-hero--celebrating");
    hero.classList.add("jsd-hero--removing");
    window.requestAnimationFrame(function () {
      hero.classList.add("jsd-hero--removed");
    });
    window.setTimeout(function () {
      hero.remove();
    }, FADE_OUT_DURATION_MS + 50);
  }

  function startConfetti(canvas, durationMs) {
    if (!canvas || !canvas.getContext) return null;
    var ctx = canvas.getContext("2d");
    var W = canvas.width;
    var H = canvas.height;
    var colors = ["#6366f1", "#8b5cf6", "#22c55e", "#f59e0b", "#ec4899", "#0ea5e9", "#f97316", "#14b8a6"];
    var particles = [];
    var count = Math.min(200, Math.floor((W * H) / 3000));

    // Spawn from multiple origins: left, center-left, center, center-right, right
    var origins = [0.15, 0.35, 0.5, 0.65, 0.85];
    var perOrigin = Math.floor(count / origins.length);

    origins.forEach(function (ox) {
      for (var i = 0; i < perOrigin; i++) {
        particles.push({
          x: W * ox + (Math.random() - 0.5) * W * 0.08,
          y: H * 0.55,
          vx: (Math.random() - 0.5) * 12,
          vy: Math.random() * -14 - 6,
          size: Math.random() * 7 + 3,
          color: colors[Math.floor(Math.random() * colors.length)],
          rotation: Math.random() * 360,
          spin: (Math.random() - 0.5) * 14,
          life: 1,
          shape: Math.random() > 0.5 ? "rect" : "circle",
        });
      }
    });

    var start = performance.now();
    function frame(now) {
      var elapsed = now - start;
      var progress = Math.min(1, elapsed / durationMs);
      ctx.clearRect(0, 0, W, H);
      particles.forEach(function (p) {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.22;   // gravity
        p.vx *= 0.985;  // air resistance
        p.rotation += p.spin;
        p.life = 1 - progress;
        if (p.life <= 0) return;
        ctx.save();
        ctx.globalAlpha = Math.max(0, p.life);
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;
        if (p.shape === "circle") {
          ctx.beginPath();
          ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
        }
        ctx.restore();
      });
      if (progress < 1) requestAnimationFrame(frame);
      else ctx.clearRect(0, 0, W, H);
    }
    requestAnimationFrame(frame);
  }
  
  // Application Modal Controller
  function initApplicationModal() {
    var applyModalEl = document.getElementById("fjdApplyModal");
    if (!applyModalEl) return;
    
    var modalTitleJob = document.getElementById("fjdApplyModalJobTitle");
    var modalInstitution = document.getElementById("fjdApplyModalInstitution");
    var coverLetter = document.getElementById("fjdApplyCoverLetter");
    var coverLetterCount = document.getElementById("fjdApplyCoverLetterCount");
    var submitBtn = document.getElementById("fjdApplySubmitBtn");
    
    var currentJobId = null;
    var currentApplyUrl = null;
    var currentSourceBtn = null;
    
    // Character Counter
    if (coverLetter && coverLetterCount) {
      coverLetter.addEventListener("input", function() {
        coverLetterCount.textContent = this.value.length;
      });
    }
    
    // On Modal Open
    applyModalEl.addEventListener("show.bs.modal", function (event) {
      var button = event.relatedTarget;
      if (!button) return;
      
      currentSourceBtn = button;
      currentJobId = button.getAttribute("data-job-id");
      currentApplyUrl = button.getAttribute("data-apply-url");
      
      modalTitleJob.textContent = button.getAttribute("data-job-title") || "Job Title";
      modalInstitution.textContent = button.getAttribute("data-job-institution") || "Institution Name";
      
      if (coverLetter) {
        coverLetter.value = "";
        if (coverLetterCount) coverLetterCount.textContent = "0";
      }
      
      submitBtn.disabled = submitBtn.hasAttribute("data-disabled-initially");
    });
    
    // On Submit
    if (submitBtn) {
      submitBtn.addEventListener("click", function () {
        if (!currentApplyUrl) return;
        
        var dashCfg = window.FJD_DASHBOARD || {};
        var csrfToken = dashCfg.csrfToken || window.FJD_SAVED_VACANCIES?.csrfToken || "";
        
        var originalBtnText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
        submitBtn.disabled = true;
        
        var formData = new FormData();
        if (coverLetter) formData.append("cover_letter", coverLetter.value);
        
        fetch(currentApplyUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken || getCookie("csrftoken"),
            "X-Requested-With": "XMLHttpRequest"
          },
          body: formData,
          credentials: "same-origin"
        })
        .then(function(response) {
          return response.json().then(function(data) {
            if (!response.ok) {
              throw new Error(data.error || "Application submission failed.");
            }
            return data;
          });
        })
        .then(function(data) {
          notify("success", data.message || "Application submitted successfully.");
          
          var modalInstance = bootstrap.Modal.getInstance(applyModalEl);
          if (modalInstance) modalInstance.hide();
          
          if (currentSourceBtn) {
            var detailUrl = data.application_detail_url || "#";
            var newBtn = document.createElement("a");
            newBtn.href = detailUrl;
            newBtn.className = currentSourceBtn.className.replace("fjd-apply-action-btn", "");
            if (currentSourceBtn.innerHTML.includes("w-100")) newBtn.classList.add("w-100");
            newBtn.innerHTML = '<i class="bi bi-file-earmark-text me-1"></i> View Application';
            currentSourceBtn.parentNode.replaceChild(newBtn, currentSourceBtn);
          }
        })
        .catch(function(error) {
          notify("error", error.message);
        })
        .finally(function() {
          submitBtn.innerHTML = originalBtnText;
          submitBtn.disabled = false;
        });
      });
    }
  }
  
  // Initialize on load
  document.addEventListener("DOMContentLoaded", initApplicationModal);
})();
