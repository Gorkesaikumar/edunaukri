/**
 * Job Seeker Profile — structured Indian education workflow
 */
(function () {
  "use strict";

  var LEVEL_META = {
    school: {
      title: "School Education (SSC / 10th)",
      icon: "bi-book",
      short: "School (10th)",
    },
    intermediate: {
      title: "Intermediate Education (12th / Diploma)",
      icon: "bi-journal-text",
      short: "Intermediate",
    },
    degree: {
      title: "Degree / B.Tech",
      icon: "bi-mortarboard",
      short: "Degree",
    },
    post_graduation: {
      title: "Post Graduation",
      icon: "bi-award",
      short: "Post Graduation",
    },
  };

  var editingId = null;
  var helpers = null;

  function init() {
    helpers = window.JSPHelpers;
    if (!helpers) return;

    bindEducationTriggers();
    bindEducationForm();
  }

  function choices() {
    var state = helpers.getState();
    return (state && state.choices) || {};
  }

  function urls() {
    var state = helpers.getState();
    return (state && state.api_urls) || {};
  }

  function bindEducationTriggers() {
    document.querySelectorAll("[data-jsp-add-education]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openEducationModal(btn.getAttribute("data-jsp-add-education"), null);
      });
    });

    document.querySelectorAll("[data-jsp-edit-education]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-jsp-id");
        var item = helpers.findNestedItem("education", id);
        openEducationModal(item.education_level || "degree", item);
      });
    });
  }

  function bindEducationForm() {
    var form = document.getElementById("jspEducationForm");
    if (!form) return;

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (form.dataset.jspSubmitting === "1") return;

      var level = document.getElementById("jspEduLevelInput").value;
      clearFieldErrors(form);

      var errors = validateEducationForm(form, level);
      if (Object.keys(errors).length) {
        showFieldErrors(form, errors);
        helpers.showToast("Validation failed. Please check the highlighted fields.", true);
        return;
      }

      var payload = formToPayload(form, level);
      var saveBtn = document.getElementById("jspEducationSaveBtn");
      var url = editingId
        ? urls().education_detail.replace("__id__", editingId)
        : urls().education;
      var method = editingId ? "PATCH" : "POST";

      form.dataset.jspSubmitting = "1";
      helpers.setButtonLoading(saveBtn, true);

      helpers
        .api(method, url, payload)
        .then(function () {
          helpers.hideModal("jspEducationModal");
          helpers.showToast("Education saved successfully.");
          window.setTimeout(function () {
            window.location.reload();
          }, 1200);
        })
        .catch(function (err) {
          helpers.showToast(
            err && err.error ? err.error : "Unable to save education. Please try again.",
            true
          );
        })
        .finally(function () {
          helpers.setButtonLoading(saveBtn, false);
          delete form.dataset.jspSubmitting;
        });
    });

    form.addEventListener("change", function (e) {
      if (e.target && e.target.name === "score_type") {
        toggleScoreFields(form, e.target.value);
      }
    });
  }

  function openEducationModal(level, item) {
    var form = document.getElementById("jspEducationForm");
    var titleEl = document.getElementById("jspEducationModalTitle");
    var fieldsEl = document.getElementById("jspEducationFields");
    var levelInput = document.getElementById("jspEduLevelInput");
    var picker = document.getElementById("jspEduLevelPicker");

    if (!form || !fieldsEl || !levelInput) return;

    editingId = item && item.id ? item.id : null;
    level = (item && item.education_level) || level || "degree";
    levelInput.value = level;

    var meta = LEVEL_META[level] || LEVEL_META.degree;
    titleEl.textContent = (editingId ? "Edit " : "Add ") + meta.short;

    if (!editingId) {
      renderLevelPicker(picker, level);
      picker.hidden = false;
    } else if (picker) {
      picker.hidden = true;
      picker.innerHTML = "";
    }

    fieldsEl.innerHTML = buildEducationFields(level, item || {});
    bindLevelPicker(picker);
    toggleScoreFields(form, (item && item.score_type) || "percentage");
    clearFieldErrors(form);
    helpers.showModal("jspEducationModal");
  }

  function renderLevelPicker(picker, activeLevel) {
    if (!picker) return;
    var html = '<div class="jsp-edu-level-tabs" role="tablist">';
    Object.keys(LEVEL_META).forEach(function (key) {
      var meta = LEVEL_META[key];
      html +=
        '<button type="button" class="jsp-edu-level-tab' +
        (key === activeLevel ? " is-active" : "") +
        '" data-edu-level="' +
        key +
        '" role="tab">' +
        '<i class="bi ' +
        meta.icon +
        '"></i><span>' +
        escapeHtml(meta.short) +
        "</span></button>";
    });
    html += "</div>";
    picker.innerHTML = html;
  }

  function bindLevelPicker(picker) {
    if (!picker) return;
    picker.querySelectorAll("[data-edu-level]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var level = btn.getAttribute("data-edu-level");
        openEducationModal(level, null);
      });
    });
  }

  function buildEducationFields(level, item) {
    var c = choices();
    var scoreType = item.score_type || "percentage";
    var html = "";

    html += sectionHeading(LEVEL_META[level] ? LEVEL_META[level].title : "Education Details");

    if (level === "school") {
      html +=
        field("school_name", "School Name", item.school_name || item.institution, true) +
        selectField("board", "Board", item.board, c.education_board, true) +
        scoreTypeFields(scoreType, item) +
        field("passing_year", "Passing Year", item.passing_year || item.end_year, true, "number");
    } else if (level === "intermediate") {
      html +=
        field("college", "Intermediate College Name", item.college || item.institution, true) +
        field("university", "Board / University", item.university, true) +
        selectField("board", "Board (optional)", item.board, c.education_board, false) +
        selectField("stream", "Stream", item.stream, c.intermediate_stream, true) +
        scoreTypeFields(scoreType, item) +
        field("passing_year", "Passing Year", item.passing_year || item.end_year, true, "number");
    } else if (level === "degree") {
      html +=
        selectField("degree_type", "Degree Type", item.degree_type, c.degree_type, true) +
        field("college", "College Name", item.college, true) +
        field("university", "University", item.university, true) +
        field("field_of_study", "Specialization", item.field_of_study || item.specialization, false) +
        scoreTypeFields(scoreType, item) +
        '<div class="row g-3">' +
        '<div class="col-sm-6">' +
        fieldInner("start_year", "Start Year", item.start_year, true, "number") +
        "</div>" +
        '<div class="col-sm-6">' +
        fieldInner("end_year", "End Year", item.end_year, true, "number") +
        "</div></div>";
    } else if (level === "post_graduation") {
      html +=
        selectField("degree_type", "PG Degree", item.degree_type, c.pg_degree_type, true) +
        field("college_university", "College / University Name", item.institution || item.college, true) +
        field("field_of_study", "Specialization", item.field_of_study || item.specialization, false) +
        scoreTypeFields(scoreType, item) +
        '<div class="row g-3">' +
        '<div class="col-sm-6">' +
        fieldInner("start_year", "Start Year", item.start_year, true, "number") +
        "</div>" +
        '<div class="col-sm-6">' +
        fieldInner("end_year", "End Year", item.end_year, true, "number") +
        "</div></div>";
    }

    return html;
  }

  function sectionHeading(text) {
    return '<div class="jsp-edu-section-head"><h6 class="jsp-edu-section-title">' + escapeHtml(text) + "</h6></div>";
  }

  function scoreTypeFields(scoreType, item) {
    var c = choices();
    return (
      '<div class="jsp-edu-score-wrap">' +
      selectField("score_type", "Score Type", scoreType, c.education_score_type, true) +
      '<div class="jsp-edu-score-fields">' +
      '<div class="mb-3 jsp-field-wrap jsp-score-pct">' +
      fieldInner("percentage", "Percentage", item.percentage, scoreType === "percentage", "number") +
      "</div>" +
      '<div class="mb-3 jsp-field-wrap jsp-score-cgpa">' +
      fieldInner("cgpa", "CGPA", item.cgpa, scoreType === "cgpa", "number") +
      "</div></div></div>"
    );
  }

  function field(name, label, value, required, type, extraClass) {
    return (
      '<div class="mb-3 jsp-field-wrap">' +
      fieldInner(name, label, value, required, type, extraClass) +
      "</div>"
    );
  }

  function fieldInner(name, label, value, required, type, extraClass) {
    type = type || "text";
    value = value == null ? "" : value;
    extraClass = extraClass || "";
    return (
      '<label class="form-label" for="jsp_edu_' +
      name +
      '">' +
      escapeHtml(label) +
      (required ? ' <span class="text-danger">*</span>' : "") +
      '</label><input class="form-control ' +
      extraClass +
      '" id="jsp_edu_' +
      name +
      '" name="' +
      name +
      '" type="' +
      type +
      '" value="' +
      escapeAttr(String(value)) +
      '"' +
      (required ? " required" : "") +
      '><div class="invalid-feedback jsp-field-error" data-error-for="' +
      name +
      '"></div>'
    );
  }

  function selectField(name, label, value, options, required) {
    options = options || [];
    var html =
      '<div class="mb-3 jsp-field-wrap"><label class="form-label" for="jsp_edu_' +
      name +
      '">' +
      escapeHtml(label) +
      (required ? ' <span class="text-danger">*</span>' : "") +
      '</label><select class="form-select" id="jsp_edu_' +
      name +
      '" name="' +
      name +
      '"' +
      (required ? " required" : "") +
      '><option value="">Select</option>';
    options.forEach(function (opt) {
      html +=
        '<option value="' +
        escapeAttr(opt.value) +
        '"' +
        (opt.value === value ? " selected" : "") +
        ">" +
        escapeHtml(opt.label) +
        "</option>";
    });
    html +=
      '</select><div class="invalid-feedback jsp-field-error" data-error-for="' +
      name +
      '"></div></div>';
    return html;
  }

  function toggleScoreFields(form, scoreType) {
    var pctWrap = form.querySelector(".jsp-score-pct");
    var cgpaWrap = form.querySelector(".jsp-score-cgpa");
    var pct = form.querySelector('[name="percentage"]');
    var cgpa = form.querySelector('[name="cgpa"]');

    if (pctWrap) pctWrap.style.display = scoreType === "cgpa" ? "none" : "";
    if (cgpaWrap) cgpaWrap.style.display = scoreType === "percentage" ? "none" : "";
    if (pct) pct.required = scoreType === "percentage";
    if (cgpa) cgpa.required = scoreType === "cgpa";
  }

  function formToPayload(form, level) {
    var data = {};
    new FormData(form).forEach(function (value, key) {
      if (key === "csrfmiddlewaretoken") return;
      data[key] = value;
    });
    data.education_level = level;

    if (level === "post_graduation" && data.college_university) {
      data.institution = data.college_university;
    }

    if (data.score_type === "percentage") {
      delete data.cgpa;
    } else if (data.score_type === "cgpa") {
      delete data.percentage;
    }

    return data;
  }

  function validateEducationForm(form, level) {
    var errors = {};
    var currentYear = new Date().getFullYear();
    var scoreType = (form.querySelector('[name="score_type"]') || {}).value;

    function req(field, message) {
      var el = form.querySelector('[name="' + field + '"]');
      var val = el ? String(el.value || "").trim() : "";
      if (!val) errors[field] = message;
      return val;
    }

    if (level === "school") {
      req("school_name", "School name is required.");
      req("board", "Board is required.");
      req("passing_year", "Passing year is required.");
      validateYearField(form, "passing_year", errors, currentYear, true);
    } else if (level === "intermediate") {
      req("college", "College name is required.");
      req("university", "Board or university is required.");
      req("stream", "Stream is required.");
      req("passing_year", "Passing year is required.");
      validateYearField(form, "passing_year", errors, currentYear, true);
    } else if (level === "degree") {
      req("degree_type", "Degree type is required.");
      req("college", "College name is required.");
      req("university", "University is required.");
      validateYearRange(form, errors, currentYear);
    } else if (level === "post_graduation") {
      req("degree_type", "PG degree is required.");
      req("college_university", "College or university name is required.");
      validateYearRange(form, errors, currentYear);
    }

    if (scoreType === "percentage") {
      var pct = parseFloat((form.querySelector('[name="percentage"]') || {}).value);
      if (isNaN(pct)) errors.percentage = "Percentage is required.";
      else if (pct < 0 || pct > 100) errors.percentage = "Percentage must be between 0 and 100.";
    } else if (scoreType === "cgpa") {
      var cg = parseFloat((form.querySelector('[name="cgpa"]') || {}).value);
      if (isNaN(cg)) errors.cgpa = "CGPA is required.";
      else if (cg < 0 || cg > 10) errors.cgpa = "CGPA must be between 0 and 10.";
    } else {
      errors.score_type = "Select Percentage or CGPA.";
    }

    return errors;
  }

  function validateYearField(form, field, errors, currentYear, isPassing) {
    var el = form.querySelector('[name="' + field + '"]');
    var year = parseInt(el && el.value, 10);
    if (isNaN(year)) return;
    if (year < 1970 || year > currentYear) {
      errors[field] = isPassing ? "Passing year cannot be in the future." : "Enter a valid year.";
    }
  }

  function validateYearRange(form, errors, currentYear) {
    var startEl = form.querySelector('[name="start_year"]');
    var endEl = form.querySelector('[name="end_year"]');
    var start = parseInt(startEl && startEl.value, 10);
    var end = parseInt(endEl && endEl.value, 10);

    if (isNaN(start)) errors.start_year = "Start year is required.";
    if (isNaN(end)) errors.end_year = "End year is required.";
    if (!isNaN(start) && start < 1970) errors.start_year = "Enter a valid start year.";
    if (!isNaN(end) && end > currentYear + 1) errors.end_year = "End year cannot be in the future.";
    if (!isNaN(start) && !isNaN(end) && end < start) {
      errors.end_year = "End year must be greater than or equal to start year.";
    }
  }

  function showFieldErrors(form, errors) {
    Object.keys(errors).forEach(function (field) {
      var input = form.querySelector('[name="' + field + '"]');
      var errEl = form.querySelector('[data-error-for="' + field + '"]');
      if (input) input.classList.add("is-invalid");
      if (errEl) {
        errEl.textContent = errors[field];
        errEl.style.display = "block";
      }
    });
  }

  function clearFieldErrors(form) {
    form.querySelectorAll(".is-invalid").forEach(function (el) {
      el.classList.remove("is-invalid");
    });
    form.querySelectorAll(".jsp-field-error").forEach(function (el) {
      el.textContent = "";
      el.style.display = "";
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, "&quot;");
  }

  window.JSPEducation = { init: init };
})();
