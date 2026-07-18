(function () {
  "use strict";

  var pending = {};

  function config() {
    return window.JSD_SAVED_JOBS || window.JM_CONFIG || {};
  }

  function getCsrfToken() {
    var cfg = config();
    if (cfg.csrfToken) return cfg.csrfToken;
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute("content");
    var input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function toggleUrl() {
    var cfg = config();
    return cfg.toggleUrl || cfg.savedJobToggleUrl || "";
  }

  function notify(type, message) {
    if (window.EduNotify && typeof window.EduNotify.toast === "function") {
      window.EduNotify.toast(type, message);
      return;
    }
    if (type === "error") {
      console.error(message);
    }
  }

  function updateCountBadge(count) {
    document.querySelectorAll("[data-saved-jobs-count]").forEach(function (el) {
      el.textContent = count;
      el.classList.toggle("d-none", !count);
    });
    var badge = document.getElementById("jsdSavedCountBadge");
    if (badge) {
      badge.textContent = count + " saved";
    }
  }

  function updateButton(btn, isSaved) {
    if (!btn) return;
    btn.classList.toggle("is-saved", isSaved);
    btn.classList.remove("is-saving");
    btn.disabled = false;
    btn.setAttribute("aria-pressed", isSaved ? "true" : "false");
    var icon = btn.querySelector("i");
    if (icon) {
      icon.className = isSaved ? "bi bi-bookmark-fill" : "bi bi-bookmark";
    }
    var label = btn.querySelector("span");
    if (label) {
      label.textContent = isSaved ? "Saved" : "Save";
    }
    btn.classList.add("jsd-save-btn--pulse");
    window.setTimeout(function () {
      btn.classList.remove("jsd-save-btn--pulse");
    }, 420);
  }

  function syncButtons(jobId, isSaved) {
    document.querySelectorAll('[data-save-job-toggle][data-job-id="' + jobId + '"]').forEach(function (btn) {
      updateButton(btn, isSaved);
    });
  }

  function dispatchChange(detail) {
    document.dispatchEvent(new CustomEvent("edu:saved-jobs-changed", { detail: detail }));
  }

  function removeSavedCard(jobId) {
    var card = document.querySelector('[data-saved-job-card][data-job-id="' + jobId + '"]');
    if (!card) return;
    card.classList.add("is-removing");
    window.setTimeout(function () {
      card.remove();
      var grid = document.getElementById("jsdSavedJobsGrid");
      if (grid && !grid.querySelector("[data-saved-job-card]")) {
        window.location.reload();
      }
    }, 280);
  }

  function toggle(jobId, button) {
    if (!jobId || pending[jobId]) return Promise.resolve(null);
    var url = toggleUrl();
    if (!url) return Promise.resolve(null);

    pending[jobId] = true;
    if (button) {
      button.classList.add("is-saving");
      button.disabled = true;
    }

    var body = new FormData();
    body.append("job_id", jobId);

    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      body: body,
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success) {
          throw new Error(payload.error || "Unable to update saved job.");
        }
        var data = payload.data;
        syncButtons(data.job_id, data.is_saved);
        updateCountBadge(data.saved_count);
        notify("success", data.message);
        if (!data.is_saved) {
          removeSavedCard(data.job_id);
        }
        dispatchChange(data);
        return data;
      })
      .catch(function (err) {
        notify("error", err.message || "Unable to update saved job.");
        if (button) {
          button.classList.remove("is-saving");
          button.disabled = false;
        }
        return null;
      })
      .finally(function () {
        delete pending[jobId];
      });
  }

  function initToggleButtons() {
    document.addEventListener("click", function (event) {
      var btn = event.target.closest("[data-save-job-toggle]");
      if (!btn) return;
      event.preventDefault();
      event.stopPropagation();
      var jobId = btn.getAttribute("data-job-id");
      toggle(jobId, btn);
    });
  }

  function initForms() {
    document.querySelectorAll("[data-save-job-form]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        var btn = form.querySelector("[data-save-job-toggle], button");
        var jobId = (btn && btn.getAttribute("data-job-id")) || form.getAttribute("data-job-id");
        if (!jobId) {
          var action = form.getAttribute("action") || "";
          var parts = action.split("/");
          jobId = parts[parts.length - 2];
        }
        toggle(jobId, btn);
      });
    });
  }

  function initAutoSaveFromQuery() {
    var params = new URLSearchParams(window.location.search);
    var jobId = params.get("save_job");
    if (!jobId || !toggleUrl()) return;
    toggle(jobId).then(function (data) {
      if (!data) return;
      params.delete("save_job");
      var next = window.location.pathname + (params.toString() ? "?" + params.toString() : "");
      window.history.replaceState({}, "", next);
    });
  }

  function initStatusSync() {
    var cfg = config();
    if (!cfg.statusUrl) return;
    var buttons = document.querySelectorAll("[data-save-job-toggle][data-job-id]");
    if (!buttons.length) return;
    var ids = [];
    buttons.forEach(function (btn) {
      var id = btn.getAttribute("data-job-id");
      if (id && ids.indexOf(id) === -1) ids.push(id);
    });
    if (!ids.length) return;

    fetch(cfg.statusUrl + "?ids=" + encodeURIComponent(ids.join(",")), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success || !payload.data) return;
        var status = payload.data.status || {};
        Object.keys(status).forEach(function (jobId) {
          syncButtons(jobId, status[jobId]);
        });
        if (typeof payload.data.saved_count === "number") {
          updateCountBadge(payload.data.saved_count);
        }
      })
      .catch(function () {});
  }

  window.EduSavedJobs = {
    toggle: toggle,
    syncButtons: syncButtons,
    updateCountBadge: updateCountBadge,
  };

  document.addEventListener("DOMContentLoaded", function () {
    initToggleButtons();
    initForms();
    initAutoSaveFromQuery();
    initStatusSync();
  });
})();
