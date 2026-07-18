/**
 * EduNaukri Auth — Faculty domain login (Faculty Job Seeker / Institution).
 */
(function () {
  "use strict";

  var Auth = window.EduNaukriAuth;
  if (!Auth) return;

  var AuthSession = window.EduNaukriAuthSession;

  var form = document.getElementById("login-panel");
  if (!form) return;

  var roleInput = document.getElementById("authRoleInput");
  var signInBtn = document.getElementById("signInBtn");
  var emailInput = document.getElementById("email");
  var passwordInput = document.getElementById("password");

  var loginEndpoint = form.getAttribute("data-login-action") || "";
  var oauthGoogle = form.getAttribute("data-oauth-google") || "";
  var oauthLinkedin = form.getAttribute("data-oauth-linkedin") || "";
  var googleBtn = document.getElementById("googleBtn");
  var linkedinBtn = document.getElementById("linkedinBtn");
  var selectedRole = roleInput ? roleInput.value || "seeker" : "seeker";
  var isSubmitting = false;

  function setLoginPending(active) {
    if (AuthSession && AuthSession.setLoginInProgress) {
      AuthSession.setLoginInProgress(active);
    }
  }

  function validateForm() {
    var emailError = Auth.validateEmail(emailInput ? emailInput.value : "");
    var passwordError = Auth.validatePassword(passwordInput ? passwordInput.value : "");
    Auth.showFieldError("email", emailError);
    Auth.showFieldError("password", passwordError);
    Auth.showFormError("");
    return !emailError && !passwordError;
  }

  function parseLoginResponse(res) {
    var contentType = res.headers.get("content-type") || "";
    if (contentType.indexOf("application/json") === -1) {
      return Promise.reject(new Error("invalid_response"));
    }
    return res.json().then(function (data) {
      return { ok: res.ok, status: res.status, data: data };
    });
  }

  function submitCredentialsLogin() {
    if (isSubmitting) return;
    if (!validateForm()) return;
    if (!loginEndpoint) return;

    isSubmitting = true;
    setLoginPending(true);
    Auth.setButtonLoading(signInBtn, true, "Logging In...");
    Auth.showFormError("");

    var body = new FormData(form);
    body.set("role", selectedRole);

    var fetchOptions = {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": Auth.getCsrfToken(),
      },
      body: body,
      credentials: "same-origin",
    };
    if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
      fetchOptions.signal = AbortSignal.timeout(30000);
    }

    fetch(loginEndpoint, fetchOptions)
      .then(parseLoginResponse)
      .then(function (result) {
        if (result.data && result.data.success && result.data.redirect_url) {
          if (AuthSession && AuthSession.clearRedirectLoopState) {
            AuthSession.clearRedirectLoopState();
          }
          if (AuthSession && AuthSession.setLoginInProgress) {
            AuthSession.setLoginInProgress(true);
          }
          window.location.href = result.data.redirect_url;
          return;
        }

        var errors = (result.data && result.data.errors) || {};
        if (errors.email) Auth.showFieldError("email", errors.email);
        if (errors.password) Auth.showFieldError("password", errors.password);
        if (errors.form) Auth.showFormError(errors.form);
        if (!errors.email && !errors.password && !errors.form) {
          Auth.showFormError("Unable to sign in. Please check your credentials.");
        }
      })
      .catch(function (err) {
        if (err && err.name === "TimeoutError") {
          Auth.showFormError("Sign in timed out. Please try again.");
          return;
        }
        Auth.showFormError("Network error. Please check your connection and try again.");
      })
      .finally(function () {
        if (window.location.pathname.indexOf("/faculty/login") !== -1) {
          isSubmitting = false;
          setLoginPending(false);
          Auth.setButtonLoading(signInBtn, false);
        }
      });
  }

  function oauthRoleParam() {
    return selectedRole === "seeker" ? "professor" : selectedRole;
  }

  function startOAuth(provider) {
    if (isSubmitting) return;
    var baseUrl = provider === "linkedin" ? oauthLinkedin : oauthGoogle;
    var button = provider === "linkedin" ? linkedinBtn : googleBtn;
    if (!baseUrl) return;

    isSubmitting = true;
    setLoginPending(true);
    Auth.setButtonLoading(button, true, "Connecting...");

    var url =
      baseUrl +
      (baseUrl.indexOf("?") >= 0 ? "&" : "?") +
      "role=" +
      encodeURIComponent(oauthRoleParam());
    window.location.href = url;
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    submitCredentialsLogin();
  });

  if (emailInput) {
    emailInput.addEventListener("input", function () {
      Auth.showFieldError("email", "");
      Auth.showFormError("");
    });
  }
  if (passwordInput) {
    passwordInput.addEventListener("input", function () {
      Auth.showFieldError("password", "");
      Auth.showFormError("");
    });
  }

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
})();
