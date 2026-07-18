(function () {
  "use strict";

  var Auth = window.EduNaukriAuth;
  if (!Auth) return;

  var form = document.getElementById("reset-panel");
  if (!form) return;

  var submitBtn = document.getElementById("submitBtn");
  var passwordInput = document.getElementById("password");
  var confirmInput = document.getElementById("confirm_password");
  var strengthFill = document.getElementById("passwordStrengthFill");
  var strengthReqs = document.getElementById("passwordRequirements");
  var isSubmitting = false;

  function validateForm() {
    var valid = true;
    var passwordError = Auth.validatePasswordStrength(passwordInput ? passwordInput.value : "");
    var confirmError = Auth.validateConfirmPassword(
      passwordInput ? passwordInput.value : "",
      confirmInput ? confirmInput.value : ""
    );
    Auth.showFieldError("password", passwordError);
    Auth.showFieldError("confirm_password", confirmError);
    Auth.showFormError("");
    if (passwordError || confirmError) valid = false;
    return valid;
  }

  if (passwordInput) {
    passwordInput.addEventListener("input", function () {
      Auth.updatePasswordStrengthUI(passwordInput.value, strengthFill, strengthReqs);
      Auth.showFieldError("password", "");
    });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (isSubmitting || !validateForm()) return;

    isSubmitting = true;
    Auth.setButtonLoading(submitBtn, true, "Updating...");

    fetch(window.location.pathname + window.location.search, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": Auth.getCsrfToken(),
      },
      body: new FormData(form),
      credentials: "same-origin",
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.data && result.data.success) {
          Auth.showFormSuccess(result.data.message || "Password updated.");
          if (result.data.redirect_url) {
            window.setTimeout(function () {
              window.location.replace(result.data.redirect_url);
            }, 900);
          }
          return;
        }
        var errors = (result.data && result.data.errors) || {};
        Object.keys(errors).forEach(function (key) {
          if (key === "form") Auth.showFormError(errors[key]);
          else Auth.showFieldError(key, errors[key]);
        });
      })
      .catch(function () {
        Auth.showFormError("Network error. Please try again.");
      })
      .finally(function () {
        isSubmitting = false;
        Auth.setButtonLoading(submitBtn, false);
      });
  });
})();
