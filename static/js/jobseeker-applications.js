(function () {
  "use strict";

  function getCsrfToken() {
    var cfg = window.JSD_APPLICATIONS || {};
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

  function initWithdraw() {
    var btn = document.querySelector("[data-withdraw-application]");
    var root = document.getElementById("jsdApplicationDetail");
    if (!btn || !root) return;
    btn.addEventListener("click", async function () {
      var ok = await confirmAction({
        title: "Withdraw Application",
        message: "Are you sure you want to withdraw this application? This action cannot be undone.",
        confirmText: "Withdraw",
        cancelText: "Keep Application",
        variant: "danger",
      });
      if (!ok) {
        return;
      }
      btn.disabled = true;
      var body = new FormData();
      postAction(root.getAttribute("data-withdraw-url"), body)
        .then(function (payload) {
          if (!payload.success) throw new Error(payload.error || "Unable to withdraw.");
          notify("success", payload.message || "Application withdrawn.");
          window.setTimeout(function () {
            window.location.href = document.querySelector(".jsd-app-breadcrumb a")?.href || window.location.pathname.replace(/\/[^/]+\/?$/, "/");
          }, 700);
        })
        .catch(function (err) {
          notify("error", err.message);
          btn.disabled = false;
        });
    });
  }

  function initOfferActions() {
    var root = document.getElementById("jsdApplicationDetail");
    if (!root) return;
    root.querySelectorAll("[data-offer-action]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var action = btn.getAttribute("data-offer-action");
        var confirmMsg =
          action === "accept"
            ? "Accept this offer?"
            : "Decline this offer? This cannot be undone.";
        var ok = await confirmAction({
          title: action === "accept" ? "Accept Offer" : "Decline Offer",
          message: confirmMsg,
          confirmText: action === "accept" ? "Accept Offer" : "Decline Offer",
          cancelText: "Cancel",
          variant: action === "accept" ? "info" : "danger",
        });
        if (!ok) return;
        btn.disabled = true;
        var body = new FormData();
        body.append("action", action);
        postAction(root.getAttribute("data-offer-url"), body)
          .then(function (payload) {
            if (!payload.success) throw new Error(payload.error || "Unable to update offer.");
            notify("success", payload.message);
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message);
            btn.disabled = false;
          });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initWithdraw();
    initOfferActions();
  });
})();
