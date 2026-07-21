(function () {
  "use strict";

  var cfg = window.JSD_INTERVIEWS || {};
  var joinWindowMs = (cfg.joinWindowMinutes || 15) * 60 * 1000;

  function getCsrfToken() {
    if (cfg.csrfToken) return cfg.csrfToken;
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

  function postAction(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      body: body,
    }).then(function (res) {
      return res.json();
    });
  }

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function formatCountdown(targetIso) {
    if (!targetIso) return "";
    var target = new Date(targetIso);
    var now = new Date();
    var diff = target.getTime() - now.getTime();
    if (diff <= 0) return "Starting now";
    var days = Math.floor(diff / 86400000);
    diff -= days * 86400000;
    var hours = Math.floor(diff / 3600000);
    diff -= hours * 3600000;
    var minutes = Math.floor(diff / 60000);
    if (days > 0) {
      return "Starts in " + days + "d " + pad(hours) + "h " + pad(minutes) + "m";
    }
    return "Starts in " + pad(hours) + "h " + pad(minutes) + "m";
  }

  function updateLiveCountdown(root) {
    var targetIso = root.getAttribute("data-countdown-target");
    if (!targetIso) return;
    var target = new Date(targetIso);
    var now = new Date();
    var diff = Math.max(0, target.getTime() - now.getTime());
    var daysEl = root.querySelector("[data-days]");
    var hoursEl = root.querySelector("[data-hours]");
    var minutesEl = root.querySelector("[data-minutes]");
    var secondsEl = root.querySelector("[data-seconds]");
    if (daysEl) {
      var days = Math.floor(diff / 86400000);
      diff -= days * 86400000;
      var hours = Math.floor(diff / 3600000);
      diff -= hours * 3600000;
      var minutes = Math.floor(diff / 60000);
      diff -= minutes * 60000;
      var seconds = Math.floor(diff / 1000);
      daysEl.textContent = pad(days);
      hoursEl.textContent = pad(hours);
      minutesEl.textContent = pad(minutes);
      secondsEl.textContent = pad(seconds);
      return;
    }
    root.textContent = formatCountdown(targetIso);
  }

  function initCountdowns() {
    document.querySelectorAll("[data-countdown-target]").forEach(function (el) {
      updateLiveCountdown(el);
    });
    window.setInterval(function () {
      document.querySelectorAll("[data-countdown-target]").forEach(function (el) {
        updateLiveCountdown(el);
      });
    }, 1000);
  }

  function initJoinButtons() {
    var detailRoot = document.getElementById("jsdInterviewDetail");
    if (!detailRoot) return;
    var scheduledAt = detailRoot.getAttribute("data-scheduled-at");
    if (!scheduledAt) return;
    var joinBtn = detailRoot.querySelector(".jsd-int-join-btn");
    if (!joinBtn) return;
    var joinUrl = joinBtn.getAttribute("data-join-url");
    function refreshJoinState() {
      var start = new Date(scheduledAt).getTime();
      var now = Date.now();
      var enabled = now >= start - joinWindowMs && now <= start + 2 * 60 * 60 * 1000;
      if (enabled) {
        joinBtn.classList.remove("is-disabled");
        joinBtn.removeAttribute("aria-disabled");
        joinBtn.removeAttribute("tabindex");
        joinBtn.setAttribute("href", joinUrl);
        joinBtn.setAttribute("target", "_blank");
        joinBtn.setAttribute("rel", "noopener");
      }
    }
    refreshJoinState();
    window.setInterval(refreshJoinState, 30000);
  }

  function initListJoinButtons() {
    document.querySelectorAll(".fjd-list-card[data-scheduled-at]").forEach(function (card) {
      var scheduledAt = card.getAttribute("data-scheduled-at");
      var joinBtn = card.querySelector(".fjd-btn--outline[disabled]");
      if (!joinBtn || !scheduledAt) return;
      function refresh() {
        var start = new Date(scheduledAt).getTime();
        var now = Date.now();
        if (now >= start - joinWindowMs && now <= start + 2 * 60 * 60 * 1000) {
          var active = card.querySelector('a.fjd-btn--primary[href]');
          if (!active) {
            var url = card.querySelector("[data-join-url]");
            if (url) {
              joinBtn.outerHTML =
                '<a href="' +
                url.getAttribute("data-join-url") +
                '" class="fjd-btn fjd-btn--primary" target="_blank" rel="noopener">Join Interview</a>';
            }
          }
        }
      }
      window.setInterval(refresh, 30000);
    });
  }

  function initDetailActions() {
    var root = document.getElementById("jsdInterviewDetail");
    if (!root) return;
    var modal = document.getElementById("jsdIntRescheduleModal");
    var reasonInput = document.getElementById("jsdIntRescheduleReason");
    var submitBtn = document.getElementById("jsdIntRescheduleSubmit");

    root.querySelectorAll("[data-int-action]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var action = btn.getAttribute("data-int-action");
        if (action === "confirm") {
          var ok = await confirmAction({
            title: "Confirm Interview Attendance",
            message: "Do you want to confirm your attendance for this interview?",
            confirmText: "Confirm Attendance",
            cancelText: "Cancel",
            variant: "info",
          });
          if (!ok) return;
          btn.disabled = true;
          postAction(root.getAttribute("data-confirm-url"), new FormData())
            .then(function (payload) {
              if (!payload.success) throw new Error(payload.error || "Unable to confirm.");
              notify("success", payload.message || "Attendance confirmed.");
              window.location.reload();
            })
            .catch(function (err) {
              notify("error", err.message);
              btn.disabled = false;
            });
        }
        if (action === "reschedule" && modal) {
          modal.hidden = false;
        }
      });
    });

    if (modal) {
      modal.querySelectorAll("[data-modal-close]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          modal.hidden = true;
        });
      });
      modal.addEventListener("click", function (event) {
        if (event.target === modal) modal.hidden = true;
      });
    }

    if (submitBtn && modal) {
      submitBtn.addEventListener("click", function () {
        submitBtn.disabled = true;
        var body = new FormData();
        body.append("reason", reasonInput ? reasonInput.value : "");
        postAction(root.getAttribute("data-reschedule-url"), body)
          .then(function (payload) {
            if (!payload.success) throw new Error(payload.error || "Unable to request reschedule.");
            notify("success", payload.message || "Reschedule request sent.");
            modal.hidden = true;
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message);
            submitBtn.disabled = false;
          });
      });
    }
  }

  function initLiveSummary() {
    var page = document.getElementById("jsdInterviewsPage");
    if (!page) return;
    var apiUrl = page.getAttribute("data-api-url") || "";
    if (!apiUrl) return;
    window.setInterval(function () {
      fetch(apiUrl, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(function (res) {
          return res.json();
        })
        .then(function (payload) {
          if (!payload.success || !payload.data) return;
          payload.data.summary.forEach(function (stat) {
            document.querySelectorAll('.fjd-tracker__item').forEach(function (el) {
              var label = el.querySelector(".fjd-tracker__label");
              if (label && label.textContent === stat.label) {
                var value = el.querySelector(".fjd-tracker__value");
                if (value) value.textContent = stat.value;
              }
            });
          });
        })
        .catch(function () {});
    }, 60000);
  }

  initCountdowns();
  initJoinButtons();
  initListJoinButtons();
  initDetailActions();
  initLiveSummary();
})();
