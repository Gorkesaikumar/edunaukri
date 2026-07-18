(function () {
  "use strict";

  var SPECIAL = /[!@#$%^&*(),.?":{}|<>\[\]\\/_+=\-~`';]/;

  function root() {
    return document.getElementById("jsdSettingsPage");
  }

  function csrf() {
    if (window.JSD_SETTINGS && window.JSD_SETTINGS.csrfToken) {
      return window.JSD_SETTINGS.csrfToken;
    }
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute("content")) {
      return meta.getAttribute("content");
    }
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function notify(type, message) {
    if (window.EduNotify && typeof window.EduNotify.toast === "function") {
      window.EduNotify.toast(type, message);
      return;
    }
  }

  function confirmAction(options) {
    if (window.EduNotify && typeof window.EduNotify.confirm === "function") {
      return window.EduNotify.confirm(options);
    }
    return Promise.resolve(false);
  }

  function apiUrl(key) {
    var el = root();
    return el ? el.getAttribute("data-api-" + key) : "";
  }

  function parseResponse(res) {
    var contentType = res.headers.get("content-type") || "";
    if (contentType.indexOf("application/json") === -1) {
      if (res.status === 403 || res.status === 401) {
        return Promise.reject(new Error("Your session expired. Please sign in again."));
      }
      return Promise.reject(new Error("Unexpected server response. Please try again."));
    }
    return res.json().then(function (body) {
      if (!res.ok || !body.success) {
        throw new Error(body.error || body.message || "Request failed.");
      }
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

  function deleteReq(url) {
    return fetch(url, {
      method: "DELETE",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
    }).then(parseResponse);
  }

  function getJson(url) {
    return fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    }).then(parseResponse);
  }

  function setButtonLoading(button, loading) {
    if (!button) return;
    var label = button.querySelector(".jsd-set-btn__label");
    var spinner = button.querySelector(".jsd-set-btn__spinner");
    button.disabled = loading;
    button.classList.toggle("is-loading", loading);
    if (label) label.classList.toggle("invisible", loading);
    if (spinner) spinner.classList.toggle("d-none", !loading);
  }

  function showFieldError(inputId, message) {
    var input = document.getElementById(inputId);
    var error = document.getElementById(inputId + "Error");
    if (input) input.classList.toggle("is-invalid", Boolean(message));
    if (error) {
      error.textContent = message || "";
      error.hidden = !message;
    }
  }

  function showFormError(elId, message) {
    var el = document.getElementById(elId);
    if (!el) return;
    if (message) {
      el.textContent = message;
      el.hidden = false;
    } else {
      el.textContent = "";
      el.hidden = true;
    }
  }

  function clearPasswordErrors() {
    showFormError("jsdSetPasswordError", "");
    showFieldError("jsdSetCurrentPass", "");
    showFieldError("jsdSetNewPass", "");
    showFieldError("jsdSetConfirmPass", "");
  }

  function passwordRulesMet(value) {
    return {
      length: value.length >= 8,
      upper: /[A-Z]/.test(value),
      lower: /[a-z]/.test(value),
      digit: /\d/.test(value),
      special: SPECIAL.test(value),
    };
  }

  function validatePasswordForm(current, newPass, confirm) {
    clearPasswordErrors();
    var errors = [];

    if (!current) {
      showFieldError("jsdSetCurrentPass", "Current password is required.");
      errors.push("current");
    }
    if (!newPass) {
      showFieldError("jsdSetNewPass", "New password is required.");
      errors.push("new");
    }
    if (!confirm) {
      showFieldError("jsdSetConfirmPass", "Please confirm your new password.");
      errors.push("confirm");
    }
    if (newPass && current && newPass === current) {
      showFieldError("jsdSetNewPass", "New password must be different from your current password.");
      errors.push("new");
    }
    if (newPass) {
      var rules = passwordRulesMet(newPass);
      if (!rules.length || !rules.upper || !rules.lower || !rules.digit || !rules.special) {
        showFieldError("jsdSetNewPass", "Password must meet all strength requirements below.");
        errors.push("new");
      }
    }
    if (newPass && confirm && newPass !== confirm) {
      showFieldError("jsdSetConfirmPass", "Passwords do not match.");
      errors.push("confirm");
    }
    return errors.length === 0;
  }

  function resetPasswordStrengthUI() {
    var bar = document.getElementById("jsdSetStrengthBar");
    var label = document.getElementById("jsdSetStrengthLabel");
    var rules = document.getElementById("jsdSetPassRules");
    if (bar) bar.style.width = "0";
    if (label) label.textContent = "Password strength";
    if (rules) {
      rules.querySelectorAll("li").forEach(function (item) {
        item.classList.remove("is-valid");
      });
    }
  }
  function bindPasswordToggles() {
    document.querySelectorAll(".jsd-set-pass-toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var input = document.getElementById(btn.getAttribute("data-target"));
        if (!input) return;
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        btn.querySelector("i").className = show ? "bi bi-eye-slash" : "bi bi-eye";
      });
    });
  }

  function scorePassword(value) {
    var score = 0;
    if (value.length >= 8) score += 20;
    if (value.length >= 12) score += 10;
    if (/[A-Z]/.test(value)) score += 15;
    if (/[a-z]/.test(value)) score += 15;
    if (/\d/.test(value)) score += 20;
    if (SPECIAL.test(value)) score += 20;
    return Math.min(100, score);
  }

  function bindPasswordStrength() {
    var input = document.getElementById("jsdSetNewPass");
    var bar = document.getElementById("jsdSetStrengthBar");
    var label = document.getElementById("jsdSetStrengthLabel");
    var rules = document.getElementById("jsdSetPassRules");
    if (!input || !bar) return;

    input.addEventListener("input", function () {
      var v = input.value || "";
      var score = scorePassword(v);
      bar.style.width = score + "%";
      if (score < 40) {
        bar.style.background = "#dc2626";
        label.textContent = "Weak password";
      } else if (score < 70) {
        bar.style.background = "#f59e0b";
        label.textContent = "Fair password";
      } else if (score < 90) {
        bar.style.background = "#6366f1";
        label.textContent = "Good password";
      } else {
        bar.style.background = "#059669";
        label.textContent = "Strong password";
      }
      if (rules) {
        rules.querySelector('[data-rule="length"]').classList.toggle("is-valid", v.length >= 8);
        rules.querySelector('[data-rule="upper"]').classList.toggle("is-valid", /[A-Z]/.test(v));
        rules.querySelector('[data-rule="lower"]').classList.toggle("is-valid", /[a-z]/.test(v));
        rules.querySelector('[data-rule="digit"]').classList.toggle("is-valid", /\d/.test(v));
        rules.querySelector('[data-rule="special"]').classList.toggle("is-valid", SPECIAL.test(v));
      }
    });
  }

  function bindAccountForm() {
    var form = document.getElementById("jsdSetAccountForm");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var payload = {
        first_name: document.getElementById("jsdSetFirstName").value.trim(),
        last_name: document.getElementById("jsdSetLastName").value.trim(),
        phone: document.getElementById("jsdSetPhone").value.trim(),
      };
      var officialEmail = document.getElementById("jsdSetOfficialEmail");
      var designation = document.getElementById("jsdSetDesignation");
      if (officialEmail) payload.official_email = officialEmail.value.trim();
      if (designation) payload.designation = designation.value.trim();
      patchJson(apiUrl("account"), payload)
        .then(function (body) {
          notify("success", body.message || "Account updated.");
        })
        .catch(function (err) {
          notify("error", err.message);
        });
    });
  }

  function bindPasswordForm() {
    var form = document.getElementById("jsdSetPasswordForm");
    var submitBtn = document.getElementById("jsdSetPasswordBtn");
    if (!form) return;

    ["jsdSetCurrentPass", "jsdSetNewPass", "jsdSetConfirmPass"].forEach(function (id) {
      var input = document.getElementById(id);
      if (!input) return;
      input.addEventListener("input", function () {
        showFieldError(id, "");
        showFormError("jsdSetPasswordError", "");
      });
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var current = document.getElementById("jsdSetCurrentPass").value;
      var newPass = document.getElementById("jsdSetNewPass").value;
      var confirm = document.getElementById("jsdSetConfirmPass").value;
      var url = apiUrl("password");

      if (!url) {
        notify("error", "Password service is unavailable. Please refresh the page.");
        return;
      }
      if (!validatePasswordForm(current, newPass, confirm)) {
        return;
      }

      setButtonLoading(submitBtn, true);
      postJson(url, {
        current_password: current,
        new_password: newPass,
        confirm_password: confirm,
      })
        .then(function (body) {
          notify("success", body.message || "Password updated successfully.");
          form.reset();
          resetPasswordStrengthUI();
          if (body.data && body.data.password_changed_label) {
            var changedEl = document.querySelector("[data-password-changed-label]");
            if (changedEl) changedEl.textContent = body.data.password_changed_label;
          }
        })
        .catch(function (err) {
          var msg = err.message || "Could not update password.";
          if (msg.indexOf("Current password") >= 0) {
            showFieldError("jsdSetCurrentPass", msg);
          } else if (msg.indexOf("confirm") >= 0 || msg.indexOf("match") >= 0) {
            showFieldError("jsdSetConfirmPass", msg);
          } else if (msg.indexOf("Password") >= 0) {
            showFieldError("jsdSetNewPass", msg);
          } else {
            showFormError("jsdSetPasswordError", msg);
          }
          notify("error", msg);
        })
        .finally(function () {
          setButtonLoading(submitBtn, false);
        });
    });
  }

  function saveNotificationField(key, enabled) {
    var payload = {};
    payload[key] = enabled;
    return patchJson(apiUrl("notifications"), payload);
  }

  function savePrivacyField(key, enabled) {
    var payload = {};
    payload[key] = enabled;
    return patchJson(apiUrl("privacy"), payload);
  }

  function savePrivacyVisibility(value) {
    return patchJson(apiUrl("privacy"), { profile_visibility: value });
  }

  function bindRealtimeToggle(input, saveFn, options) {
    options = options || {};
    var row = input.closest(".jsd-set-toggle");
    if (!row) return;
    var busy = false;

    function persist() {
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
            notify("success", body.message, { dedupeKey: "privacy-" + key });
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
    }

    input.addEventListener("change", persist);
  }

  function bindToggles() {
    document.querySelectorAll("[data-notify-key]").forEach(function (el) {
      bindRealtimeToggle(el, function (key, enabled) {
        return saveNotificationField(key, enabled);
      }, { showSuccessToast: false });
    });

    var vis = document.getElementById("jsdSetVisibility");
    if (vis) {
      vis.setAttribute("data-prev-value", vis.value);
      vis.addEventListener("change", function () {
        var prev = vis.getAttribute("data-prev-value") || vis.value;
        vis.disabled = true;
        vis.classList.add("is-saving");
        savePrivacyVisibility(vis.value)
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
        return savePrivacyField(key, enabled);
      });
    });
  }

  function bindOAuthQueryParams() {
    var params = new URLSearchParams(window.location.search);
    var success = params.get("oauth_success");
    var error = params.get("oauth_error");
    if (success) {
      notify("success", success);
      params.delete("oauth_success");
      var clean = window.location.pathname + (params.toString() ? "?" + params.toString() : "") + window.location.hash;
      window.history.replaceState({}, "", clean);
    } else if (error) {
      notify("error", error);
      params.delete("oauth_error");
      var cleanErr = window.location.pathname + (params.toString() ? "?" + params.toString() : "") + window.location.hash;
      window.history.replaceState({}, "", cleanErr);
    }
  }

  function bindConnected() {
    document.querySelectorAll(".jsd-set-disconnect").forEach(function (btn) {
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
  }

  function renderActivityItems(items) {
    var list = document.getElementById("jsdSetActivityList");
    if (!list) return;
    list.innerHTML = "";
    if (!items || !items.length) {
      list.innerHTML = '<p class="text-muted mb-0">No security activity recorded yet.</p>';
      return;
    }
    items.forEach(function (event) {
      var article = document.createElement("article");
      article.className = "jsd-set-audit__item";
      article.setAttribute("data-event-type", event.event_type || "");
      var ip = event.ip_address ? " · " + event.ip_address : "";
      var desc = event.description
        ? '<p class="mb-0 text-muted small">' + event.description + "</p>"
        : "";
      article.innerHTML =
        "<div><strong>" +
        (event.title || "Security event") +
        "</strong>" +
        desc +
        '<p class="mb-0 text-muted small">' +
        (event.occurred_label || "") +
        ip +
        "</p></div>";
      list.appendChild(article);
    });
  }

  function bindSecurityActivity() {
    var refreshBtn = document.getElementById("jsdSetRefreshActivity");
    if (!refreshBtn) return;
    refreshBtn.addEventListener("click", function () {
      refreshBtn.disabled = true;
      getJson(apiUrl("audit"))
        .then(function (body) {
          var items = (body.data && body.data.items) || [];
          renderActivityItems(items);
          notify("success", "Security activity updated.");
        })
        .catch(function (err) {
          notify("error", err.message || "Could not refresh activity.");
        })
        .finally(function () {
          refreshBtn.disabled = false;
        });
    });
  }

  function bindSessions() {
    var revokeOthers = document.getElementById("jsdSetRevokeOthers");
    if (revokeOthers) {
      revokeOthers.addEventListener("click", function () {
        confirmAction({
          title: "Sign Out Other Devices",
          message: "This will end all active sessions except your current device. Continue?",
          confirmText: "Sign Out Others",
          cancelText: "Cancel",
          variant: "warning",
          icon: "bi-laptop",
        }).then(function (ok) {
          if (!ok) return;
          postJson(apiUrl("revoke-others"))
            .then(function (body) {
              notify("success", body.message || "Other devices signed out.");
              window.location.reload();
            })
            .catch(function (err) {
              notify("error", err.message);
            });
        });
      });
    }
    document.querySelectorAll(".jsd-set-revoke-session").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-session-id");
        confirmAction({
          title: "Sign Out Session",
          message: "Sign out of this device? You will need to sign in again on that device.",
          confirmText: "Sign Out",
          cancelText: "Cancel",
          variant: "warning",
          icon: "bi-box-arrow-right",
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

  function bindDeleteAccount() {
    var modalEl = document.getElementById("jsdSetDeleteModal");
    if (!modalEl) return;
    var modal = new bootstrap.Modal(modalEl);
    document.getElementById("jsdSetDeleteOpen").addEventListener("click", function () {
      document.getElementById("jsdSetDeletePass").value = "";
      document.getElementById("jsdSetDeleteError").hidden = true;
      modal.show();
    });
    document.getElementById("jsdSetDeleteConfirm").addEventListener("click", function () {
      var errEl = document.getElementById("jsdSetDeleteError");
      postJson(apiUrl("delete"), { password: document.getElementById("jsdSetDeletePass").value })
        .then(function (body) {
          modal.hide();
          notify("success", body.message);
          window.location.href = body.redirect_url || (window.JSD_SETTINGS && window.JSD_SETTINGS.loginUrl) || "/it/login/job-seeker/";
        })
        .catch(function (err) {
          errEl.textContent = err.message;
          errEl.hidden = false;
        });
    });
  }

  function bindNav() {
    document.querySelectorAll(".jsd-set-nav__link").forEach(function (link) {
      link.addEventListener("click", function () {
        document.querySelectorAll(".jsd-set-nav__link").forEach(function (l) {
          l.classList.remove("is-active");
        });
        link.classList.add("is-active");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!root()) return;
    bindPasswordToggles();
    bindPasswordStrength();
    bindAccountForm();
    bindPasswordForm();
    bindToggles();
    bindOAuthQueryParams();
    bindConnected();
    bindSessions();
    bindSecurityActivity();
    bindDeleteAccount();
    bindNav();
  });
})();
