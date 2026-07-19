/**

 * EduNaukri Auth — shared utilities for login and signup pages.

 */

window.EduNaukriAuth = window.EduNaukriAuth || {};



(function (Auth) {

  "use strict";



  Auth.getCsrfToken = function () {

    var input = document.querySelector("[name=csrfmiddlewaretoken]");

    return input ? input.value : "";

  };



  Auth.setButtonLoading = function (button, isLoading, loadingText) {

    if (!button) return;

    var label = button.querySelector(".ed-auth-btn__label");

    var spinner = button.querySelector(".ed-auth-btn__spinner");



    if (isLoading) {

      if (label && !button.hasAttribute("data-original-html")) {

        button.setAttribute("data-original-html", label.innerHTML);

      }

      if (label && loadingText) {

        label.innerHTML = loadingText;

      }

    } else {

      if (label && button.hasAttribute("data-original-html")) {

        label.innerHTML = button.getAttribute("data-original-html");

      }

    }



    button.disabled = isLoading;

    button.classList.toggle("is-loading", isLoading);

    if (spinner) spinner.classList.toggle("d-none", !isLoading);

  };



  Auth.validateEmail = function (value) {

    var email = (value || "").trim();

    if (!email) return "Email address is required.";

    var pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!pattern.test(email)) return "Enter a valid email address.";

    return "";

  };



  Auth.validatePassword = function (value) {

    if (!value) return "Password is required.";

    return "";

  };



  Auth.validateMobile = function (value) {

    var digits = (value || "").replace(/\D/g, "");

    if (!digits) return "Mobile number is required.";

    if (digits.length < 10 || digits.length > 15) return "Enter a valid mobile number.";

    return "";

  };



  Auth.validateRequired = function (value, label) {

    if (!(value || "").trim()) return (label || "This field") + " is required.";

    return "";

  };



  Auth.validateConfirmPassword = function (password, confirm) {

    if (!confirm) return "Please confirm your password.";

    if (password !== confirm) return "Passwords do not match.";

    return "";

  };



  Auth.getPasswordStrength = function (password) {

    var value = password || "";

    var checks = {

      length: value.length >= 8,

      upper: /[A-Z]/.test(value),

      lower: /[a-z]/.test(value),

      number: /[0-9]/.test(value),

      special: /[^A-Za-z0-9]/.test(value),

    };

    var score = Object.keys(checks).filter(function (key) {

      return checks[key];

    }).length;

    return { checks: checks, score: score, isStrong: score === 5 };

  };



  Auth.validatePasswordStrength = function (value) {
    if (!value) return "Password is required.";
    var result = Auth.getPasswordStrength(value);
    if (result.checks.length && result.isStrong) return "";
    if (!result.checks.length) {
      return "Password must be at least 8 characters.";
    }
    return "Password must include uppercase, lowercase, a number, and a special character.";
  };



  Auth.updatePasswordStrengthUI = function (password, fillEl, reqsEl) {

    var result = Auth.getPasswordStrength(password);

    if (fillEl) {

      var width = (result.score / 5) * 100;

      fillEl.style.width = width + "%";

      fillEl.classList.remove(

        "ed-auth-strength__fill--weak",

        "ed-auth-strength__fill--fair",

        "ed-auth-strength__fill--good",

        "ed-auth-strength__fill--strong"

      );

      if (result.score <= 2) fillEl.classList.add("ed-auth-strength__fill--weak");

      else if (result.score === 3) fillEl.classList.add("ed-auth-strength__fill--fair");

      else if (result.score === 4) fillEl.classList.add("ed-auth-strength__fill--good");

      else fillEl.classList.add("ed-auth-strength__fill--strong");

    }

    if (reqsEl) {

      reqsEl.querySelectorAll("[data-req]").forEach(function (item) {

        var key = item.getAttribute("data-req");

        item.classList.toggle("is-met", Boolean(result.checks[key]));

      });

    }

    return result;

  };



  Auth.showFieldError = function (fieldId, message) {

    var input = document.getElementById(fieldId);

    var error = document.getElementById(fieldId + "Error");

    if (input) {

      input.classList.toggle("is-invalid", Boolean(message));

      input.setAttribute("aria-invalid", message ? "true" : "false");

    }

    if (error) {

      error.textContent = message || "";

      error.classList.toggle("is-visible", Boolean(message));

    }

  };



  Auth.showFormError = function (message) {

    var el = document.getElementById("formError");

    var success = document.getElementById("formSuccess");

    if (success) {

      success.textContent = "";

      success.classList.add("d-none");

    }

    if (!el) return;

    if (message) {

      el.textContent = message;

      el.classList.remove("d-none");

    } else {

      el.textContent = "";

      el.classList.add("d-none");

    }

  };



  Auth.showFormSuccess = function (message) {

    var el = document.getElementById("formSuccess");

    var error = document.getElementById("formError");

    if (error) {

      error.textContent = "";

      error.classList.add("d-none");

    }

    if (!el) return;

    if (message) {

      el.textContent = message;

      el.classList.remove("d-none");

    } else {

      el.textContent = "";

      el.classList.add("d-none");

    }

  };



  Auth.clearValidation = function () {

    Auth.showFieldError("email", "");

    Auth.showFieldError("password", "");

    Auth.showFormError("");

  };



  Auth.initPasswordToggles = function () {

    document.querySelectorAll("[data-auth-toggle-password]").forEach(function (toggle) {

      var targetId = toggle.getAttribute("data-target") || "password";

      var passwordInput = document.getElementById(targetId);

      if (!passwordInput) return;



      toggle.addEventListener("click", function () {

        var icon = toggle.querySelector("i");

        var isHidden = passwordInput.type === "password";

        passwordInput.type = isHidden ? "text" : "password";

        toggle.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");

        if (icon) {

          icon.classList.toggle("bi-eye", !isHidden);

          icon.classList.toggle("bi-eye-slash", isHidden);

        }

      });

    });

  };



  Auth.initPasswordToggle = function () {

    Auth.initPasswordToggles();

  };



  // -------------------------------------------------------------------
  // Cross-domain OAuth linked modal
  // -------------------------------------------------------------------

  Auth.showOAuthLinkedModal = function (data) {
    var modal = document.getElementById("oauthLinkedModal");
    if (!modal) return;

    var nameEl = document.getElementById("oauthLinkedAccountName");
    if (nameEl) nameEl.textContent = data.accountName || "";

    modal.classList.remove("d-none");
    document.body.style.overflow = "hidden";
  };

  Auth.closeOAuthLinkedModal = function () {
    var modal = document.getElementById("oauthLinkedModal");
    if (!modal) return;
    modal.classList.add("d-none");
    document.body.style.overflow = "";
  };

  Auth.handleOAuthLinkedParams = function () {
    var params = new URLSearchParams(window.location.search);
    var linkedAccount = params.get("oauth_linked_account");

    if (linkedAccount) {
      // Clean the URL immediately to prevent re-triggering on navigation
      if (window.history && window.history.replaceState) {
        params.delete("oauth_linked_account");
        var clean = window.location.pathname + (params.toString() ? "?" + params.toString() : "");
        window.history.replaceState({}, "", clean);
      }

      Auth.showOAuthLinkedModal({
        accountName: decodeURIComponent(linkedAccount.replace(/\+/g, " ")),
      });

      return true;
    }

    return false;
  };

  // -------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------

  document.addEventListener("DOMContentLoaded", function () {
    Auth.initPasswordToggles();

    // Close modal on overlay click
    var modal = document.getElementById("oauthLinkedModal");
    if (modal) {
      modal.addEventListener("click", function (event) {
        if (event.target === modal) {
          Auth.closeOAuthLinkedModal();
        }
      });

      var closeBtn = document.getElementById("oauthLinkedModalClose");
      var cancelBtn = document.getElementById("oauthLinkedCancelBtn");
      var anotherBtn = document.getElementById("oauthLinkedAnotherBtn");

      if (closeBtn) closeBtn.addEventListener("click", Auth.closeOAuthLinkedModal);
      if (cancelBtn) cancelBtn.addEventListener("click", Auth.closeOAuthLinkedModal);
      if (anotherBtn) {
        anotherBtn.addEventListener("click", function () {
          Auth.closeOAuthLinkedModal();
          // Refresh the page to clear any OAuth state
          window.location.href = window.location.pathname;
        });
      }

      // Close on Escape key
      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.classList.contains("d-none")) {
          Auth.closeOAuthLinkedModal();
        }
      });
    }

    // Check for structured OAuth linked params on page load
    Auth.handleOAuthLinkedParams();
  });

})(window.EduNaukriAuth);

