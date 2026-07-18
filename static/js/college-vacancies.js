(function () {
  "use strict";

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

  function confirmConfig(action, message) {
    var map = {
      delete: { title: "Delete Vacancy", confirmText: "Delete", variant: "danger" },
      close: { title: "Close Vacancy", confirmText: "Close Vacancy", variant: "warning" },
      archive: { title: "Archive Vacancy", confirmText: "Archive", variant: "warning" },
      pause: { title: "Pause Vacancy", confirmText: "Pause", variant: "warning" },
      reopen: { title: "Reopen Vacancy", confirmText: "Reopen", variant: "info" },
      publish: { title: "Publish Vacancy", confirmText: "Publish Vacancy", variant: "info" },
    };
    var cfg = map[action] || { title: "Confirm Action", confirmText: "Confirm", variant: "info" };
    cfg.message = message;
    cfg.cancelText = "Cancel";
    return cfg;
  }

  function postAction(url, token) {
    return fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    }).then(function (res) {
      return res.json().then(function (payload) {
        if (!res.ok || !payload.success) {
          throw new Error(payload.error || "Request failed.");
        }
        return payload;
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var page = document.getElementById("icdVacanciesPage");
    if (!page) return;
    var token = csrfToken(page);

    page.querySelectorAll("[data-vacancy-action]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var action = btn.getAttribute("data-vacancy-action");
        var url = btn.getAttribute("data-url");
        if (!url) return;
        var confirmMsg = {
          delete: "Delete this vacancy?",
          close: "Close this vacancy?",
          archive: "Archive this vacancy?",
          pause: "Pause this vacancy?",
          reopen: "Reopen this vacancy for applications?",
          publish: "Publish this vacancy now?",
        }[action];
        if (confirmMsg) {
          var ok = await confirmAction(confirmConfig(action, confirmMsg));
          if (!ok) return;
        }

        btn.disabled = true;
        postAction(url, token)
          .then(function (payload) {
            notify("success", payload.message || "Updated.");
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message);
            btn.disabled = false;
          });
      });
    });
  });
})();
