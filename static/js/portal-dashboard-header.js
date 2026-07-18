/**
 * Shared portal dashboard header interactions (IT Job Seeker reference).
 */
(function () {
  "use strict";

  function openMobileSearch() {
    var panel = document.getElementById("jsdMobileSearch");
    var toggle = document.getElementById("jsdMobileSearchToggle");
    if (!panel) return;
    panel.hidden = false;
    if (toggle) toggle.setAttribute("aria-expanded", "true");
    var input = panel.querySelector(".jsd-header__search-input");
    if (input) {
      window.setTimeout(function () {
        input.focus();
      }, 50);
    }
  }

  function closeMobileSearch() {
    var panel = document.getElementById("jsdMobileSearch");
    var toggle = document.getElementById("jsdMobileSearchToggle");
    if (!panel || panel.hidden) return;
    panel.hidden = true;
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      toggle.focus();
    }
  }

  function initSearchShortcut() {
    window.addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        var desktop = document.getElementById("jsdSearchInput");
        if (desktop && window.matchMedia("(min-width: 992px)").matches) {
          desktop.focus();
          return;
        }
        openMobileSearch();
      }
      if (e.key === "Escape") {
        closeMobileSearch();
      }
    });
  }

  function initMobileSearch() {
    var toggle = document.getElementById("jsdMobileSearchToggle");
    var panel = document.getElementById("jsdMobileSearch");
    var closeBtn = document.getElementById("jsdMobileSearchClose");
    if (!toggle || !panel) return;

    toggle.addEventListener("click", function () {
      if (panel.hidden) {
        openMobileSearch();
      } else {
        closeMobileSearch();
      }
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", closeMobileSearch);
    }
  }

  function initNotificationForms() {
    document.querySelectorAll(".jsd-notif-mark-form").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (!window.fetch) return;
        e.preventDefault();
        var fd = new FormData(form);
        fetch(form.action, {
          method: "POST",
          body: fd,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        }).then(function (res) {
          if (res.ok) {
            var btn = form.querySelector(".jsd-notif-item");
            if (btn) btn.classList.remove("jsd-notif-item--unread");
          }
        });
      });
    });
  }

  function initProfileDropdownChevron() {
    var profileBtn = document.getElementById("jsdProfileDropdown");
    if (!profileBtn) return;
    profileBtn.addEventListener("hidden.bs.dropdown", function () {
      profileBtn.classList.remove("show");
    });
    profileBtn.addEventListener("shown.bs.dropdown", function () {
      profileBtn.classList.add("show");
    });
  }

    window.initPortalDashboardHeader = function () {
    initSearchShortcut();
    initMobileSearch();
    initNotificationForms();
    initProfileDropdownChevron();
    initRealTimeNotifications();
  };

  function initRealTimeNotifications() {
    // Only connect if the user is authenticated and we're on a dashboard
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = wsScheme + "://" + window.location.host + "/ws/notifications/";
    let socket = new WebSocket(wsUrl);

    socket.onmessage = function (e) {
      const data = JSON.parse(e.data);
      if (data.event === "application.status_changed") {
        // Increment tracker badge
        const trackerBadges = document.querySelectorAll("[data-tracker-count]");
        trackerBadges.forEach(badge => {
          badge.textContent = data.unread_count;
          badge.classList.remove("d-none");
        });

        // Show a simple toast if toastContainer exists, otherwise alert or log
        showToastNotification("Application Update", data.body);

        // If on the tracker page, trigger an event for dynamic DOM update
        const evt = new CustomEvent("TrackerStatusUpdated", { detail: data });
        document.dispatchEvent(evt);
      } else if (data.event === "application.selected_popup") {
        showSelectionToastNotification(data.title, data.body, data.application_id, data.message_url, data.application_url);
      }
    };

    socket.onclose = function (e) {
      console.log("Notification socket closed unexpectedly");
      // Optional: implement reconnect logic
    };
  }

  function showToastNotification(title, message) {
    const toastContainer = document.querySelector(".toast-container") || createToastContainer();
    const toastHtml = `
      <div class="toast align-items-center text-white bg-primary border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
        <div class="d-flex">
          <div class="toast-body">
            <strong>${title}</strong><br>
            ${message}
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>
    `;
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastEl = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
  }

  function showSelectionToastNotification(title, message, appId, messageUrl, applicationUrl) {
    const toastContainer = document.querySelector(".toast-container") || createToastContainer();
    const msgUrl = messageUrl || "#";
    const appUrl = applicationUrl || "#";
    const toastHtml = `
      <div class="toast align-items-center text-white border-0 mb-3" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="15000" style="background: linear-gradient(135deg, #4F46E5, #7C3AED); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2); border-radius: 12px; width: 350px;">
        <div class="toast-body p-4">
          <div class="d-flex justify-content-between align-items-start mb-3">
            <div class="d-flex align-items-center gap-2">
              <i class="bi bi-stars fs-4" style="color: #FBBF24;"></i>
              <strong class="fs-5" style="line-height: 1.2;">${title}</strong>
            </div>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close" style="opacity: 0.8;"></button>
          </div>
          <p class="mb-4" style="font-size: 0.95rem; opacity: 0.95;">${message}</p>
          <div class="d-flex gap-2">
            <a href="${msgUrl}" class="btn btn-sm btn-light fw-medium px-3 rounded-pill text-primary" style="background-color: white;">View Message</a>
            <a href="${appUrl}" class="btn btn-sm btn-outline-light fw-medium px-3 rounded-pill">View Application</a>
          </div>
        </div>
      </div>
    `;
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastEl = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
  }

  function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1080';
    document.body.appendChild(container);
    return container;
  }
})();
