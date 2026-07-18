(function () {
  "use strict";

  var pollMs = 60000;
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Removed renderPipelines to prevent JS from overriding Django template HTML

  function renderProfileAnalytics(analytics) {
    if (!analytics) return;
    document.querySelectorAll("[data-analytics-key]").forEach(function (el) {
      var key = el.getAttribute("data-analytics-key");
      if (!key || analytics[key] == null) return;
      var value = analytics[key];
      if (key === "recruiter_interest") value = value + "/100";
      if (key === "response_rate" || key === "profile_completion" || key === "skills_match_percentage" || key === "visibility_change") {
        value = (key === "visibility_change" && Number(value) > 0 ? "+" : "") + value + "%";
      }
      el.textContent = value;
    });
  }

  function refresh() {
    var root = document.getElementById("jsdTrackerPage");
    if (!root) return;
    var url = root.getAttribute("data-api-url");
    if (!url) return;

    var params = new URLSearchParams(window.location.search);
    params.set("live", "1");

    fetch(url + "?" + params.toString(), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success || !payload.data) return;
        var data = payload.data;
        var updated = document.getElementById("jsdTrackerUpdated");
        if (updated && data.updated_at) {
          updated.textContent = "Updated " + data.updated_at;
        }
        if (data.summary) {
          data.summary.forEach(function (card) {
            var el = document.querySelector('[data-tracker-stat="' + card.key + '"] .jsd-tracker-stat__value');
            if (el) el.textContent = card.value;
          });
        }
        if (data.profile_analytics) {
          renderProfileAnalytics(data.profile_analytics);
        }
        // Removed renderPipelines to prevent JS from overriding Django template HTML
      })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.getElementById("jsdTrackerPage")) {
      window.setInterval(refresh, pollMs);
    }
  });

  // Handle real-time WebSocket updates without full page reload
  document.addEventListener("TrackerStatusUpdated", function (e) {
    console.log("Real-time tracker update received:", e.detail);
    
    // Clear sidebar badges
    document.querySelectorAll("[data-tracker-count]").forEach(badge => {
      badge.textContent = "0";
      badge.classList.add("d-none");
      badge.style.animation = "none";
    });

    // Mark as read immediately on the backend
    var csrfToken = (window.JSD_TRACKER && window.JSD_TRACKER.csrfToken) || (window.FJD_TRACKER && window.FJD_TRACKER.csrfToken) || "";
    if (csrfToken) {
      fetch("/api/v1/notifications/tracker/mark-read/", {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken
        }
      });
    }

    // Refresh the DOM partially by fetching the current page URL and extracting the updated sections
    var root = document.getElementById("jsdTrackerPage");
    if (!root) return;
    
    fetch(window.location.href, {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
    .then(res => res.text())
    .then(html => {
      var parser = new DOMParser();
      var doc = parser.parseFromString(html, "text/html");
      
      // Update pipelines
      var newPipelines = doc.getElementById("jsdTrackerPipelines");
      var oldPipelines = document.getElementById("jsdTrackerPipelines");
      if (newPipelines && oldPipelines) {
        oldPipelines.innerHTML = newPipelines.innerHTML;
      }
      
      // Update activity feed
      var newFeed = doc.getElementById("jsdTrackerFeed");
      var oldFeed = document.getElementById("jsdTrackerFeed");
      if (newFeed && oldFeed) {
        oldFeed.innerHTML = newFeed.innerHTML;
      }
      
      // We could update more sections if needed
    })
    .catch(err => console.error("Error updating tracker DOM", err));
  });

})();
