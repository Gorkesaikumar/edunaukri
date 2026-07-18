(function () {

  "use strict";



  function root() {

    return document.getElementById("fjdSettingsPage");

  }



  function csrf() {

    if (window.FJD_SETTINGS && window.FJD_SETTINGS.csrfToken) return window.FJD_SETTINGS.csrfToken;

    var meta = document.querySelector('meta[name="csrf-token"]');

    if (meta) return meta.getAttribute("content") || "";

    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);

    return match ? decodeURIComponent(match[1]) : "";

  }



  function notify(type, message, options) {

    if (window.EduNotify && window.EduNotify.toast) window.EduNotify.toast(type, message, options);

  }



  function confirmAction(options) {

    if (window.EduNotify && window.EduNotify.confirm) return window.EduNotify.confirm(options);
    return Promise.resolve(false);

  }



  function apiUrl(key) {

    var el = root();

    return el ? el.getAttribute("data-api-" + key) : "";

  }



  function parseResponse(res) {

    var ct = res.headers.get("content-type") || "";

    if (ct.indexOf("application/json") === -1) {

      return Promise.reject(new Error("Unexpected server response."));

    }

    return res.json().then(function (body) {

      if (!res.ok || !body.success) throw new Error(body.error || body.message || "Request failed.");

      return body;

    });

  }



  function patchJson(url, payload) {

    return fetch(url, {

      method: "PATCH",

      credentials: "same-origin",

      headers: {

        "Content-Type": "application/json",

        "X-CSRFToken": csrf(),

        "X-Requested-With": "XMLHttpRequest",

      },

      body: JSON.stringify(payload),

    }).then(parseResponse);

  }



  function postJson(url, payload) {

    return fetch(url, {

      method: "POST",

      credentials: "same-origin",

      headers: {

        "Content-Type": "application/json",

        "X-CSRFToken": csrf(),

        "X-Requested-With": "XMLHttpRequest",

      },

      body: JSON.stringify(payload || {}),

    }).then(parseResponse);

  }



  function getJson(url) {

    return fetch(url, {

      method: "GET",

      credentials: "same-origin",

      headers: { "X-Requested-With": "XMLHttpRequest" },

    }).then(parseResponse);

  }



  function deleteReq(url) {

    return fetch(url, {

      method: "DELETE",

      credentials: "same-origin",

      headers: {

        "X-CSRFToken": csrf(),

        "X-Requested-With": "XMLHttpRequest",

      },

    }).then(parseResponse);

  }



  function sessionItems(data) {

    if (!data) return [];

    if (Array.isArray(data)) return data;

    if (data.items) return data.items;

    return [];

  }



  function renderSessions(sessions) {

    var list = document.getElementById("fjdSetSessionsList");

    if (!list) return;

    if (!sessions || !sessions.length) {

      list.innerHTML = '<p class="text-muted mb-0">No active sessions recorded yet.</p>';

      return;

    }

    list.innerHTML = sessions

      .map(function (s) {

        var revokeBtn = s.is_current

          ? ""

          : '<button type="button" class="fjd-btn fjd-btn--danger-outline btn-sm fjd-set-revoke-session" data-session-id="' +

            s.id +

            '">Sign Out</button>';

        return (

          '<article class="fjd-set-session' +

          (s.is_current ? " is-current" : "") +

          '"><div><strong>' +

          (s.device_label || "Unknown device") +

          "</strong>" +

          (s.is_current ? '<span class="fjd-set-badge fjd-set-badge--ok">Current session</span>' : "") +

          '<p class="mb-0 text-muted small">' +

          (s.browser || "") +

          " · " +

          (s.os_name || "") +

          " · " +

          (s.ip_address || "") +

          '</p><p class="mb-0 text-muted small">Logged in ' +

          (s.login_label || "") +

          " · Last active " +

          (s.last_active_label || "") +

          "</p></div>" +

          revokeBtn +

          "</article>"

        );

      })

      .join("");

    bindSessionRevokeButtons();

  }



  function renderAudit(events) {

    var list = document.getElementById("fjdSetActivityList");

    if (!list) return;

    if (!events || !events.length) {

      list.innerHTML = '<p class="text-muted mb-0">No security activity recorded yet.</p>';

      return;

    }

    list.innerHTML = events

      .map(function (e) {

        return (

          '<article class="fjd-set-audit__item"><div><strong>' +

          (e.title || "") +

          "</strong>" +

          (e.description ? '<p class="mb-0 text-muted small">' + e.description + "</p>" : "") +

          '<p class="mb-0 text-muted small">' +

          (e.occurred_label || "") +

          (e.ip_address ? " · " + e.ip_address : "") +

          "</p></div></article>"

        );

      })

      .join("");

  }



  function bindPasswordToggles() {

    document.querySelectorAll(".fjd-set-pass-toggle").forEach(function (btn) {

      btn.addEventListener("click", function () {

        var input = document.getElementById(btn.getAttribute("data-target"));

        if (!input) return;

        var isPass = input.type === "password";

        input.type = isPass ? "text" : "password";

        btn.innerHTML = isPass ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';

      });

    });

  }



  function bindPasswordStrength() {

    var input = document.getElementById("fjdSetNewPass");

    var bar = document.getElementById("fjdSetStrengthBar");

    var label = document.getElementById("fjdSetStrengthLabel");

    if (!input || !bar) return;

    input.addEventListener("input", function () {

      var val = input.value || "";

      var score = 0;

      if (val.length >= 8) score++;

      if (/[A-Z]/.test(val)) score++;

      if (/[a-z]/.test(val)) score++;

      if (/\d/.test(val)) score++;

      if (/[^A-Za-z0-9]/.test(val)) score++;

      var pct = Math.min(100, score * 20);

      bar.style.width = pct + "%";

      bar.style.background = pct >= 80 ? "#15803d" : pct >= 40 ? "#ca8a04" : "#dc2626";

      if (label) {

        label.textContent =

          pct >= 80 ? "Strong password" : pct >= 40 ? "Moderate password" : val ? "Weak password" : "Password strength";

      }

    });

  }



  function bindRealtimeToggle(input, saveFn, options) {

    options = options || {};

    var row = input.closest(".fjd-set-toggle");

    if (!row) return;

    var busy = false;



    input.addEventListener("change", function () {

      if (busy) return;

      var key = input.getAttribute("data-notify-key") || input.getAttribute("data-privacy-key");

      if (!key) return;

      busy = true;

      input.disabled = true;

      row.classList.remove("is-saved", "is-error");

      row.classList.add("is-saving");



      saveFn(key, input.checked)

        .then(function (body) {

          row.classList.remove("is-saving");

          row.classList.add("is-saved");

          if (options.showSuccessToast !== false && body && body.message) {

            notify("success", body.message, { dedupeKey: "pref-" + key });

          }

          window.setTimeout(function () {

            row.classList.remove("is-saved");

          }, 1200);

        })

        .catch(function (err) {

          row.classList.remove("is-saving");

          row.classList.add("is-error");

          input.checked = !input.checked;

          notify("error", err.message || "Could not save preference.");

          window.setTimeout(function () {

            row.classList.remove("is-error");

          }, 2000);

        })

        .finally(function () {

          busy = false;

          input.disabled = false;

        });

    });

  }



  function bindToggles() {

    document.querySelectorAll("[data-notify-key]").forEach(function (el) {

      bindRealtimeToggle(

        el,

        function (key, enabled) {

          var payload = {};

          payload[key] = enabled;

          return patchJson(apiUrl("notifications"), payload);

        },

        { showSuccessToast: false }

      );

    });



    var vis = document.getElementById("fjdSetVisibility");

    if (vis) {

      vis.setAttribute("data-prev-value", vis.value);

      vis.addEventListener("change", function () {

        var prev = vis.getAttribute("data-prev-value") || vis.value;

        vis.disabled = true;

        vis.classList.add("is-saving");

        patchJson(apiUrl("privacy"), { profile_visibility: vis.value })

          .then(function (body) {

            notify("success", (body && body.message) || "Profile visibility updated.", {

              dedupeKey: "privacy-visibility",

            });

            vis.setAttribute("data-prev-value", vis.value);

          })

          .catch(function (err) {

            vis.value = prev;

            notify("error", err.message || "Could not update profile visibility.");

          })

          .finally(function () {

            vis.disabled = false;

            vis.classList.remove("is-saving");

          });

      });

    }



    document.querySelectorAll("[data-privacy-key]").forEach(function (el) {

      bindRealtimeToggle(el, function (key, enabled) {

        var payload = {};

        payload[key] = enabled;

        return patchJson(apiUrl("privacy"), payload);

      });

    });

  }



  function bindSessionRevokeButtons() {

    document.querySelectorAll(".fjd-set-revoke-session").forEach(function (btn) {

      if (btn.dataset.bound) return;

      btn.dataset.bound = "1";

      btn.addEventListener("click", function () {

        var id = btn.getAttribute("data-session-id");

        confirmAction({

          title: "Sign Out Session",

          message: "Sign out of this device? You will need to sign in again on that device.",

          confirmText: "Sign Out",

          variant: "warning",

        }).then(function (ok) {

          if (!ok) return;

          deleteReq(apiUrl("sessions").replace(/\/$/, "") + "/" + id + "/")

            .then(function (body) {

              notify("success", body.message || "Session signed out.");

              window.location.reload();

            })

            .catch(function (err) {

              notify("error", err.message);

            });

        });

      });

    });

  }



  function bindSessions() {

    var revokeBtn = document.getElementById("fjdSetRevokeOthers");

    if (revokeBtn) {

      revokeBtn.addEventListener("click", function () {

        confirmAction({

          title: "Sign out other devices",

          message: "This will sign you out on all other browsers and devices.",

          confirmText: "Sign Out Others",

          variant: "warning",

        }).then(function (ok) {

          if (!ok) return;

          postJson(apiUrl("revoke-others"), {})

            .then(function (body) {

              notify("success", body.message || "Other sessions signed out.");

              window.location.reload();

            })

            .catch(function (err) {

              notify("error", err.message || "Could not revoke sessions.");

            });

        });

      });

    }

    bindSessionRevokeButtons();

  }



  function bindDeleteAccount() {

    var modalEl = document.getElementById("fjdSetDeleteModal");

    var openBtn = document.getElementById("fjdSetDeleteOpen");

    var confirmBtn = document.getElementById("fjdSetDeleteConfirm");

    if (!modalEl || !openBtn || !confirmBtn || typeof bootstrap === "undefined") return;

    var modal = new bootstrap.Modal(modalEl);

    openBtn.addEventListener("click", function () {

      document.getElementById("fjdSetDeletePass").value = "";

      document.getElementById("fjdSetDeleteError").hidden = true;

      modal.show();

    });

    confirmBtn.addEventListener("click", function () {

      var errEl = document.getElementById("fjdSetDeleteError");

      postJson(apiUrl("delete"), { password: document.getElementById("fjdSetDeletePass").value })

        .then(function (body) {

          modal.hide();

          notify("success", body.message);

          window.location.href =

            body.redirect_url || (window.FJD_SETTINGS && window.FJD_SETTINGS.loginUrl) || "/faculty/login/professor/";

        })

        .catch(function (err) {

          errEl.textContent = err.message;

          errEl.hidden = false;

        });

    });

  }



  document.addEventListener("DOMContentLoaded", function () {

    if (!root()) return;



    document.querySelectorAll(".fjd-set-nav__link").forEach(function (link) {

      link.addEventListener("click", function () {

        document.querySelectorAll(".fjd-set-nav__link").forEach(function (l) {

          l.classList.remove("is-active");

        });

        link.classList.add("is-active");

      });

    });



    bindPasswordToggles();

    bindPasswordStrength();

    bindToggles();

    bindSessions();

    bindDeleteAccount();



    var accountForm = document.getElementById("fjdSetAccountForm");

    if (accountForm) {

      accountForm.addEventListener("submit", function (e) {

        e.preventDefault();

        patchJson(apiUrl("account"), {

          first_name: document.getElementById("fjdSetFirstName").value.trim(),

          last_name: document.getElementById("fjdSetLastName").value.trim(),

          phone: document.getElementById("fjdSetPhone").value.trim(),

        })

          .then(function (res) {

            var data = res.data || {};

            var full = document.getElementById("fjdSetFullName");

            var phone = document.getElementById("fjdSetPhoneDisplay");

            if (full) full.textContent = data.full_name || full.textContent;

            if (phone) phone.textContent = data.phone || "—";

            notify("success", res.message || "Account updated.");

          })

          .catch(function (err) {

            notify("error", err.message || "Could not update account.");

          });

      });

    }



    var passwordForm = document.getElementById("fjdSetPasswordForm");

    if (passwordForm) {

      passwordForm.addEventListener("submit", function (e) {

        e.preventDefault();

        var errEl = document.getElementById("fjdSetPasswordError");

        if (errEl) errEl.hidden = true;

        postJson(apiUrl("password"), {

          current_password: document.getElementById("fjdSetCurrentPass").value,

          new_password: document.getElementById("fjdSetNewPass").value,

          confirm_password: document.getElementById("fjdSetConfirmPass").value,

        })

          .then(function (res) {

            passwordForm.reset();

            var bar = document.getElementById("fjdSetStrengthBar");

            if (bar) bar.style.width = "0";

            if (res.data && res.data.password_changed_label) {

              var changedEl = document.querySelector("[data-password-changed-label]");

              if (changedEl) changedEl.textContent = res.data.password_changed_label;

            }

            notify("success", res.message || "Password updated.");

          })

          .catch(function (err) {

            if (errEl) {

              errEl.textContent = err.message || "Could not update password.";

              errEl.hidden = false;

            } else {

              notify("error", err.message || "Could not update password.");

            }

          });

      });

    }



    var refreshBtn = document.getElementById("fjdSetRefreshActivity");

    if (refreshBtn) {

      refreshBtn.addEventListener("click", function () {

        refreshBtn.disabled = true;

        getJson(apiUrl("audit"))

          .then(function (res) {

            renderAudit(sessionItems(res.data));

            notify("success", "Activity refreshed.");

          })

          .catch(function (err) {

            notify("error", err.message || "Could not refresh activity.");

          })

          .finally(function () {

            refreshBtn.disabled = false;

          });

      });

    }

    document.querySelectorAll(".fjd-set-disconnect").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var provider = btn.getAttribute("data-provider");
        var label = provider === "google" ? "Google" : "LinkedIn";
        confirmAction({
          title: "Disconnect " + label,
          message: "You will no longer be able to sign in with " + label + " until you connect again.",
          confirmText: "Disconnect",
          cancelText: "Cancel",
          variant: "warning",
          icon: "bi-link-45deg",
        }).then(function (ok) {
          if (!ok) return;
          var base = apiUrl("connected").replace(/\/$/, "");
          deleteReq(base + "/" + provider + "/")
            .then(function (body) {
              notify("success", body.message || label + " disconnected.");
              window.location.reload();
            })
            .catch(function (err) {
              notify("error", err.message);
            });
        });
      });
    });

  });

})();


