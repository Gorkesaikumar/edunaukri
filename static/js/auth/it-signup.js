/**
 * EduNaukri Auth — IT domain signup (streamlined Job Seeker / Recruiter).
 * Role panels switch instantly; profile details are completed in the dashboard.
 */
(function () {
  "use strict";

  var Auth = window.EduNaukriAuth;
  if (!Auth) return;

  var form = document.getElementById("signup-panel");
  if (!form) return;

  var wrap = document.querySelector(".ed-auth-wrap--signup");

  var roleInput = document.getElementById("authRoleInput");
  var registerBtn = document.getElementById("registerBtn");
  var googleBtn = document.getElementById("googleBtn");
  var linkedinBtn = document.getElementById("linkedinBtn");
  var passwordInput = document.getElementById("password");
  var confirmInput = document.getElementById("confirm_password");
  var emailInput = document.getElementById("email");
  var loginLink = document.getElementById("signupLoginLink");
  var segmented = document.querySelector(".ed-auth-segmented");
  var strengthFill = document.getElementById("passwordStrengthFill");
  var strengthReqs = document.getElementById("passwordRequirements");

  var endpoints = {
    seeker: form.getAttribute("data-signup-seeker") || "",
    recruiter: form.getAttribute("data-signup-recruiter") || "",
  };
  var pageUrls = {
    seeker: form.getAttribute("data-page-seeker") || "",
    recruiter: form.getAttribute("data-page-recruiter") || "",
  };
  var loginUrls = {
    seeker: form.getAttribute("data-login-seeker") || "",
    recruiter: form.getAttribute("data-login-recruiter") || "",
  };
  var checkEmailUrl = form.getAttribute("data-check-email") || "";
  var oauthGoogle = wrap ? wrap.getAttribute("data-oauth-google") || "" : "";
  var oauthLinkedin = wrap ? wrap.getAttribute("data-oauth-linkedin") || "" : "";

  var selectedRole = roleInput ? roleInput.value || "seeker" : "seeker";
  var isSubmitting = false;
  var emailCheckTimer = null;

  function field(id) {
    var el = document.getElementById(id);
    return el ? el.value : "";
  }

  function signupEndpoint() {
    return selectedRole === "recruiter" ? endpoints.recruiter : endpoints.seeker;
  }

  function setRole(role, options) {
    options = options || {};
    selectedRole = role === "recruiter" ? "recruiter" : "seeker";
    if (roleInput) roleInput.value = selectedRole;

    if (segmented) {
      segmented.querySelectorAll("[data-auth-role]").forEach(function (btn) {
        var isActive = btn.getAttribute("data-auth-role") === selectedRole;
        btn.classList.toggle("is-active", isActive);
        btn.setAttribute("aria-selected", isActive ? "true" : "false");
      });
    }

    form.querySelectorAll("[data-role-panel]").forEach(function (panel) {
      var show = panel.getAttribute("data-role-panel") === selectedRole;
      panel.classList.toggle("d-none", !show);
    });

    if (loginLink) {
      loginLink.href = selectedRole === "recruiter" ? loginUrls.recruiter : loginUrls.seeker;
    }

    if (!options.skipClear) {
      Auth.showFormError("");
      Auth.showFormSuccess("");
    }

    if (options.updateUrl) {
      var target = selectedRole === "recruiter" ? pageUrls.recruiter : pageUrls.seeker;
      if (target && window.location.pathname !== target) {
        history.replaceState({ role: selectedRole }, "", target);
      }
    }
  }

  function initRoleSwitcher() {
    if (!segmented) return;
    segmented.querySelectorAll("[data-auth-role]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var role = btn.getAttribute("data-auth-role");
        if (role === selectedRole) return;
        setRole(role, { updateUrl: true });
      });
    });
    setRole(selectedRole, { skipClear: true });
  }

  function validateSeekerForm() {
    var valid = true;
    var checks = [
      ["full_name", Auth.validateRequired(field("full_name"), "Full name")],
      ["email", Auth.validateEmail(field("email"))],
      ["mobile", Auth.validateMobile(field("mobile"))],
      ["password", Auth.validatePasswordStrength(field("password"))],
      ["confirm_password", Auth.validateConfirmPassword(field("password"), field("confirm_password"))],
    ];
    checks.forEach(function (item) {
      Auth.showFieldError(item[0], item[1]);
      if (item[1]) valid = false;
    });
    Auth.showFormError("");
    return valid;
  }

  function validateRecruiterForm() {
    var valid = true;
    var checks = [
      ["recruiter_name", Auth.validateRequired(field("recruiter_name"), "Recruiter name")],
      ["company_name", Auth.validateRequired(field("company_name"), "Company name")],
      ["email", Auth.validateEmail(field("email"))],
      ["mobile", Auth.validateMobile(field("mobile"))],
      ["password", Auth.validatePasswordStrength(field("password"))],
      ["confirm_password", Auth.validateConfirmPassword(field("password"), field("confirm_password"))],
    ];
    checks.forEach(function (item) {
      Auth.showFieldError(item[0], item[1]);
      if (item[1]) valid = false;
    });
    Auth.showFormError("");
    return valid;
  }

  function validateForm() {
    return selectedRole === "recruiter" ? validateRecruiterForm() : validateSeekerForm();
  }

  function applyServerErrors(errors) {
    Object.keys(errors || {}).forEach(function (key) {
      if (key === "form") Auth.showFormError(errors[key]);
      else Auth.showFieldError(key, errors[key]);
    });
  }

  function submitRegistration() {
    if (isSubmitting) return;
    if (!validateForm()) return;

    var endpoint = signupEndpoint();
    if (!endpoint) return;

    isSubmitting = true;
    Auth.setButtonLoading(registerBtn, true, "Creating Account...");
    Auth.showFormError("");
    Auth.showFormSuccess("");

    var body = new FormData(form);
    body.set("role", selectedRole);

    fetch(endpoint, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": Auth.getCsrfToken(),
      },
      body: body,
      credentials: "same-origin",
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.data && result.data.success) {
          Auth.showFormSuccess(result.data.message || "Registration successful.");
          if (result.data.redirect_url) {
            window.setTimeout(function () {
              window.location.replace(result.data.redirect_url);
            }, 400);
          }
          return;
        }
        applyServerErrors((result.data && result.data.errors) || {});
      })
      .catch(function () {
        Auth.showFormError("Network error. Please check your connection and try again.");
      })
      .finally(function () {
        isSubmitting = false;
        Auth.setButtonLoading(registerBtn, false);
      });
  }

  function checkEmailAvailability() {
    if (!checkEmailUrl || !emailInput) return;
    var email = emailInput.value.trim();
    if (!email || Auth.validateEmail(email)) return;

    fetch(checkEmailUrl + "?email=" + encodeURIComponent(email), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (!data.available) {
          Auth.showFieldError("email", data.message || "An account with this email already exists.");
        }
      })
      .catch(function () { });
  }

  function startOAuth(provider) {
    if (isSubmitting) return;
    var button = provider === "linkedin" ? linkedinBtn : googleBtn;
    isSubmitting = true;
    Auth.setButtonLoading(button, true, "Connecting...");
    Auth.showFormError("");

    if (provider === "google") {
      // API-based flow: POST to backend with domain+role, get authorize_url, redirect
      fetch("/api/social-auth/google/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": Auth.getCsrfToken(),
        },
        body: JSON.stringify({
          domain: "it",
          role: selectedRole,
          login_url: window.location.pathname,
        }),
        credentials: "same-origin",
      })
        .then(async function (res) {
          var data = await res.json();

          console.log("Backend Response:", data);

          return {
            ok: res.ok,
            data: data
          };
        })
        .then(function (result) {

          console.log("Google OAuth Response:", result);

          if (
            result.ok &&
            result.data &&
            result.data.success &&
            result.data.data &&
            result.data.data.authorize_url
          ) {
            window.location.href = result.data.data.authorize_url;
            return;
          }

          var errMsg =
            (result.data &&
              (
                result.data.error ||
                result.data.detail ||
                (result.data.data && result.data.data.error)
              )) ||
            "Failed to initiate Google sign-in.";

          Auth.showFormError(errMsg);

          isSubmitting = false;
          Auth.setButtonLoading(button, false);
        })
        .catch(function () {
          Auth.showFormError("Network error. Please check your connection and try again.");
          isSubmitting = false;
          Auth.setButtonLoading(button, false);
        });
    } else {
      // LinkedIn: keep redirect-based flow for now
      var baseUrl = oauthLinkedin;
      if (!baseUrl) {
        isSubmitting = false;
        Auth.setButtonLoading(button, false);
        return;
      }
      var url =
        baseUrl +
        (baseUrl.indexOf("?") >= 0 ? "&" : "?") +
        "role=" +
        encodeURIComponent(selectedRole);
      window.location.href = url;
    }
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    submitRegistration();
  });

  if (passwordInput) {
    passwordInput.addEventListener("input", function () {
      Auth.updatePasswordStrengthUI(passwordInput.value, strengthFill, strengthReqs);
      Auth.showFieldError("password", "");
      Auth.showFormError("");
    });
  }

  if (confirmInput) {
    confirmInput.addEventListener("input", function () {
      Auth.showFieldError("confirm_password", "");
    });
  }

  if (emailInput) {
    emailInput.addEventListener("input", function () {
      Auth.showFieldError("email", "");
      Auth.showFormError("");
    });
    emailInput.addEventListener("blur", function () {
      window.clearTimeout(emailCheckTimer);
      emailCheckTimer = window.setTimeout(checkEmailAvailability, 250);
    });
  }

  form.querySelectorAll(".ed-auth-input").forEach(function (input) {
    if (input.id === "password" || input.id === "confirm_password" || input.id === "email") return;
    input.addEventListener("input", function () {
      Auth.showFieldError(input.id, "");
      Auth.showFormError("");
    });
  });

  if (googleBtn) googleBtn.addEventListener("click", function () { startOAuth("google"); });
  if (linkedinBtn) linkedinBtn.addEventListener("click", function () { startOAuth("linkedin"); });

  window.addEventListener("popstate", function () {
    var path = window.location.pathname;
    setRole(path.indexOf("/recruiter") !== -1 ? "recruiter" : "seeker", { skipClear: true });
  });

  initRoleSwitcher();
})();
