(function () {
  "use strict";

  var Auth = window.EduNaukriAuth;
  if (!Auth) return;

  var form = document.getElementById("forgot-panel");
  if (!form) return;

  var submitBtn = document.getElementById("submitBtn");
  var emailInput = document.getElementById("email");
  var isSubmitting = false;

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (isSubmitting) return;

    var emailError = Auth.validateEmail(emailInput ? emailInput.value : "");
    Auth.showFieldError("email", emailError);
    Auth.showFormError("");
    if (emailError) return;

    isSubmitting = true;
    Auth.setButtonLoading(submitBtn, true, "Sending Link...");

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
          Auth.showFormSuccess(result.data.message || "Check your email for reset instructions.");
          if (emailInput) emailInput.value = "";
          return;
        }
        var errors = (result.data && result.data.errors) || {};
        if (errors.email) Auth.showFieldError("email", errors.email);
        if (errors.form) Auth.showFormError(errors.form);
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
