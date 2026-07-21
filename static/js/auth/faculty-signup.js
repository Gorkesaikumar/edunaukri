/**
 * EduNaukri Auth — Faculty domain signup (Faculty Job Seeker / Institution).
 */
(function () {
  "use strict";

  var Auth = window.EduNaukriAuth;
  if (!Auth) return;

  var form = document.getElementById("signup-panel");
  if (!form) return;

  var roleInput = document.getElementById("authRoleInput");
  var registerBtn = document.getElementById("registerBtn");
  var passwordInput = document.getElementById("password");
  var confirmInput = document.getElementById("confirm_password");
  var emailInput = document.getElementById("email");
  var institutionEmailInput = document.getElementById("institution_email");
  var loginLink = document.getElementById("signupLoginLink");
  var segmented = document.querySelector(".ed-auth-segmented");
  var strengthFill = document.getElementById("passwordStrengthFill");
  var strengthReqs = document.getElementById("passwordRequirements");

  var endpoints = {
    seeker: form.getAttribute("data-signup-seeker") || "",
    institution: form.getAttribute("data-signup-institution") || "",
  };
  var pageUrls = {
    seeker: form.getAttribute("data-page-seeker") || "",
    institution: form.getAttribute("data-page-institution") || "",
  };
  var loginUrls = {
    seeker: form.getAttribute("data-login-seeker") || "",
    institution: form.getAttribute("data-login-institution") || "",
  };
  var checkEmailUrl = form.getAttribute("data-check-email") || "";
  var oauthGoogle = form.getAttribute("data-oauth-google") || "";
  var oauthLinkedin = form.getAttribute("data-oauth-linkedin") || "";

  var googleBtn = document.getElementById("googleBtn");
  var linkedinBtn = document.getElementById("linkedinBtn");

  var selectedRole = roleInput ? roleInput.value || "seeker" : "seeker";
  var isSubmitting = false;
  var emailCheckTimer = null;

  function field(id) {
    var el = document.getElementById(id);
    return el ? el.value : "";
  }

  function activeEmailInput() {
    return selectedRole === "institution" ? institutionEmailInput : emailInput;
  }

  function signupEndpoint() {
    return selectedRole === "institution" ? endpoints.institution : endpoints.seeker;
  }

  function setRole(role, options) {
    options = options || {};
    selectedRole = role === "institution" ? "institution" : "seeker";
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
      loginLink.href = selectedRole === "institution" ? loginUrls.institution : loginUrls.seeker;
    }

    if (!options.skipClear) {
      Auth.showFormError("");
      Auth.showFormSuccess("");
    }

    if (options.updateUrl) {
      var target = selectedRole === "institution" ? pageUrls.institution : pageUrls.seeker;
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

  function validateInstitutionForm() {
    var valid = true;
    var checks = [
      ["institution_name", Auth.validateRequired(field("institution_name"), "Institution name")],
      ["rep_name", Auth.validateRequired(field("rep_name"), "Representative name")],
      ["institution_email", Auth.validateEmail(field("institution_email"))],
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
    return selectedRole === "institution" ? validateInstitutionForm() : validateSeekerForm();
  }

  function applyServerErrors(errors) {
    Object.keys(errors || {}).forEach(function (key) {
      if (key === "email" && selectedRole === "institution") {
        Auth.showFieldError("institution_email", errors[key]);
        return;
      }
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
    if (selectedRole === "institution") {
      var instEmail = field("institution_email");
      if (instEmail) {
        body.set("email", instEmail);
      }
      body.delete("institution_email");
    } else {
      body.delete("institution_email");
    }

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

  function setLoginPending(active) {
    if (window.EduNaukriAuthSession && window.EduNaukriAuthSession.setLoginInProgress) {
      window.EduNaukriAuthSession.setLoginInProgress(active);
    }
  }

  function oauthRoleParam() {
    return selectedRole === "seeker" ? "professor" : selectedRole;
  }

  function startOAuth(provider) {
    if (isSubmitting) return;
    var button = provider === "linkedin" ? linkedinBtn : googleBtn;
    isSubmitting = true;
    setLoginPending(true);
    Auth.setButtonLoading(button, true, "Connecting...");
    Auth.showFormError("");

    if (provider === "google") {
      // Faculty domain: "seeker" → professor domain, "institution" → college domain
      var facultyDomain = selectedRole === "institution" ? "college" : "professor";
      var facultyRole = selectedRole === "institution" ? "institution" : "seeker";

      // API-based flow: POST to backend with domain+role, get authorize_url, redirect
      fetch("/api/social-auth/google/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": Auth.getCsrfToken(),
        },
        body: JSON.stringify({
          domain: facultyDomain,
          role: facultyRole,
          login_url: window.location.pathname,
        }),
        credentials: "same-origin",
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (result) {
          console.log("Faculty Google OAuth Response:", result);

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
          setLoginPending(false);
          Auth.setButtonLoading(button, false);
        })
      .catch(function () {
        Auth.showFormError("Network error. Please check your connection and try again.");
        isSubmitting = false;
        setLoginPending(false);
        Auth.setButtonLoading(button, false);
      });
  } else {
    // LinkedIn: keep redirect-based flow for now
    var baseUrl = oauthLinkedin;
    if (!baseUrl) {
      isSubmitting = false;
      setLoginPending(false);
      Auth.setButtonLoading(button, false);
      return;
    }
    var url =
      baseUrl +
      (baseUrl.indexOf("?") >= 0 ? "&" : "?") +
      "role=" +
      encodeURIComponent(oauthRoleParam());
    window.location.href = url;
  }
}

  function checkEmailAvailability() {
  if (!checkEmailUrl) return;
  var input = activeEmailInput();
  if (!input) return;
  var email = input.value.trim();
  if (!email || Auth.validateEmail(email)) return;

  fetch(
    checkEmailUrl +
    "?email=" +
    encodeURIComponent(email) +
    "&role=" +
    encodeURIComponent(selectedRole),
    {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    }
  )
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      if (!data.available) {
        var fieldId = selectedRole === "institution" ? "institution_email" : "email";
        Auth.showFieldError(fieldId, data.message || "An account with this email already exists.");
      }
    })
    .catch(function () { });
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

[emailInput, institutionEmailInput].forEach(function (input) {
  if (!input) return;
  input.addEventListener("input", function () {
    Auth.showFieldError(input.id, "");
    Auth.showFormError("");
  });
  input.addEventListener("blur", function () {
    window.clearTimeout(emailCheckTimer);
    emailCheckTimer = window.setTimeout(checkEmailAvailability, 250);
  });
});

form.querySelectorAll(".ed-auth-input").forEach(function (input) {
  if (
    input.id === "password" ||
    input.id === "confirm_password" ||
    input.id === "email" ||
    input.id === "institution_email"
  ) {
    return;
  }
  input.addEventListener("input", function () {
    Auth.showFieldError(input.id, "");
    Auth.showFormError("");
  });
});

if (googleBtn) {
  googleBtn.addEventListener("click", function () {
    startOAuth("google");
  });
}
if (linkedinBtn) {
  linkedinBtn.addEventListener("click", function () {
    startOAuth("linkedin");
  });
}

var params = new URLSearchParams(window.location.search);
var oauthError = params.get("oauth_error");
if (oauthError) {
  Auth.showFormError(decodeURIComponent(oauthError.replace(/\+/g, " ")));
  if (window.history && window.history.replaceState) {
    params.delete("oauth_error");
    var clean = window.location.pathname + (params.toString() ? "?" + params.toString() : "");
    window.history.replaceState({}, "", clean);
  }
}

window.addEventListener("popstate", function () {
  var path = window.location.pathname;
  setRole(path.indexOf("/institution") !== -1 ? "institution" : "seeker", { skipClear: true });
});

initRoleSwitcher();
}) ();
