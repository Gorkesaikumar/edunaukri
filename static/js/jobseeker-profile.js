/**

 * Job Seeker Profile page — section editing via JSON API

 */

(function () {

  "use strict";



  var state = window.JSP_PROFILE || {};

  var urls = state.api_urls || {};



  document.addEventListener("DOMContentLoaded", function () {

    bindSectionButtons();

    bindNestedButtons();

    bindFileInputs();

    bindModalForms();

    if (window.JSPEducation && window.JSPEducation.init) {
      window.JSPEducation.init();
    }

  });



  function bindSectionButtons() {

    document.querySelectorAll("[data-jsp-edit]").forEach(function (btn) {

      btn.addEventListener("click", function () {

        openSectionModal(btn.getAttribute("data-jsp-edit"));

      });

    });

  }



  function bindNestedButtons() {

    document.querySelectorAll("[data-jsp-add]").forEach(function (btn) {

      btn.addEventListener("click", function () {

        var type = btn.getAttribute("data-jsp-add");

        if (type === "education") return;

        openNestedModal(type, null);

      });

    });

    document.querySelectorAll("[data-jsp-edit-item]").forEach(function (btn) {

      btn.addEventListener("click", function () {

        var type = btn.getAttribute("data-jsp-type");

        if (type === "education") return;

        var id = btn.getAttribute("data-jsp-id");

        openNestedModal(type, findNestedItem(type, id));

      });

    });

    document.querySelectorAll("[data-jsp-delete-item]").forEach(function (btn) {

      btn.addEventListener("click", function () {

        var type = btn.getAttribute("data-jsp-type");

        var id = btn.getAttribute("data-jsp-id");

        var copy = {
          experience: {
            title: "Delete Experience",
            message: "Remove this work experience from your profile? This action cannot be undone.",
          },
          education: {
            title: "Delete Education",
            message: "Remove this education entry from your profile? This action cannot be undone.",
          },
          project: {
            title: "Delete Project",
            message: "Remove this project from your profile? This action cannot be undone.",
          },
          certification: {
            title: "Delete Certification",
            message: "Remove this certification from your profile? This action cannot be undone.",
          },
        };

        var cfg = copy[type] || {
          title: "Delete Entry",
          message: "Delete this entry? This action cannot be undone.",
        };

        (window.EduNotify ? window.EduNotify.confirm({
          title: cfg.title,
          message: cfg.message,
          confirmText: "Delete",
          cancelText: "Cancel",
          variant: "danger",
          icon: "bi-trash3-fill",
        }) : Promise.resolve(false)).then(function (ok) {

          if (!ok) return;

          deleteNested(type, id);

        });

      });

    });

  }



  function bindFileInputs() {

    var photoInput = document.getElementById("jspPhotoInput");

    if (photoInput) {

      photoInput.addEventListener("change", function () {

        if (photoInput.files[0]) uploadFile(urls.photo_upload, photoInput.files[0], "photo");

      });

    }

    var deletePhoto = document.getElementById("jspDeletePhoto");

    if (deletePhoto) {

      deletePhoto.addEventListener("click", function () {

        api("DELETE", urls.photo_upload).then(handleProfileResponse).catch(function () {});

      });

    }

  }



  function bindModalForms() {

    var sectionForm = document.getElementById("jspSectionForm");

    if (sectionForm) {

      sectionForm.addEventListener("submit", function (e) {

        e.preventDefault();

        var section = sectionForm.getAttribute("data-section");

        var payload = formToObject(sectionForm);

        var saveBtn = sectionForm.querySelector('[type="submit"]');



        if (section === "skills") {

          payload.skills = (payload.skills || "")

            .split(",")

            .map(function (s) {

              return s.trim();

            })

            .filter(Boolean);

        }

        if (section === "career") {

          payload.preferred_roles = (payload.preferred_roles || "")

            .split(",")

            .map(function (s) {

              return s.trim();

            })

            .filter(Boolean);

        }



        var url = urls.section.replace("__section__", section);

        if (sectionForm.dataset.jspSubmitting === "1") return;
        sectionForm.dataset.jspSubmitting = "1";
        setButtonLoading(saveBtn, true);

        api("PATCH", url, payload)

          .then(function (res) {

            hideModal("jspSectionModal");

            handleProfileResponse(res, { section: section });

          })

          .catch(function (err) {

            showToast(err && err.error ? err.error : "Unable to save your profile. Please try again.", true);

          })

          .finally(function () {

            setButtonLoading(saveBtn, false);
            delete sectionForm.dataset.jspSubmitting;

          });

      });

    }



    var nestedForm = document.getElementById("jspNestedForm");

    if (nestedForm) {

      nestedForm.addEventListener("submit", function (e) {

        e.preventDefault();

        var type = nestedForm.getAttribute("data-type");

        var id = nestedForm.getAttribute("data-id");

        var payload = formToObject(nestedForm);

        var saveBtn = nestedForm.querySelector('[type="submit"]');



        payload.is_current = payload.is_current === "on" || payload.is_current === true;

        if (payload.technologies) {

          payload.technologies = String(payload.technologies)

            .split(",")

            .map(function (t) {

              return t.trim();

            })

            .filter(Boolean);

        }



        var url;

        var method = id ? "PATCH" : "POST";

        if (type === "experience") {

          url = id ? urls.experience_detail.replace("__id__", id) : urls.experiences;

        } else if (type === "education") {

          url = id ? urls.education_detail.replace("__id__", id) : urls.education;

        } else if (type === "project") {

          url = id ? urls.project_detail.replace("__id__", id) : urls.projects;

        } else if (type === "certification") {

          url = id ? urls.certification_detail.replace("__id__", id) : urls.certifications;

        }



        setButtonLoading(saveBtn, true);

        api(method, url, payload)

          .then(function () {

            hideModal("jspNestedModal");

            showToast("Profile updated successfully.");

            window.setTimeout(function () {

              window.location.reload();

            }, 1200);

          })

          .catch(function (err) {

            showToast(err && err.error ? err.error : "Unable to save your profile. Please try again.", true);

          })

          .finally(function () {

            setButtonLoading(saveBtn, false);

          });

      });

    }

  }



  function openSectionModal(section) {

    var form = document.getElementById("jspSectionForm");

    var title = document.getElementById("jspSectionModalTitle");

    var fields = document.getElementById("jspSectionFields");

    if (!form || !fields) return;



    form.setAttribute("data-section", section);

    fields.innerHTML = buildSectionFields(section);

    title.textContent = sectionTitle(section);

    showModal("jspSectionModal");

  }



  function openNestedModal(type, item) {

    var form = document.getElementById("jspNestedForm");

    var title = document.getElementById("jspNestedModalTitle");

    var fields = document.getElementById("jspNestedFields");

    if (!form || !fields) return;



    form.setAttribute("data-type", type);

    form.setAttribute("data-id", item && item.id ? item.id : "");

    fields.innerHTML = buildNestedFields(type, item || {});

    title.textContent = (item && item.id ? "Edit " : "Add ") + nestedLabel(type);

    if (type === "experience") {

      syncExperienceEndDateState();

    }

    showModal("jspNestedModal");

  }



  function syncExperienceEndDateState() {

    var isCurrent = document.getElementById("jsp_is_current");

    var endDate = document.getElementById("jsp_end_date");

    if (!isCurrent || !endDate) return;



    function apply() {

      if (isCurrent.checked) {

        endDate.value = "";

        endDate.disabled = true;

      } else {

        endDate.disabled = false;

      }

    }



    if (isCurrent._jspEndDateHandler) {

      isCurrent.removeEventListener("change", isCurrent._jspEndDateHandler);

    }

    isCurrent._jspEndDateHandler = apply;

    isCurrent.addEventListener("change", apply);

    apply();

  }



  function buildSectionFields(section) {

    var p = state;

    var choices = state.choices || {};

    if (section === "header") {

      return (

        field("first_name", "First Name", p.first_name) +

        field("last_name", "Last Name", p.last_name) +

        field("headline", "Professional Headline", p.headline) +

        field("current_company", "Current Company", p.current_company) +

        field("current_location", "Current Location", p.current_location) +

        field("experience_years", "Years of Experience", p.experience_years, "number")

      );

    }

    if (section === "basic") {

      return (

        field("first_name", "First Name", p.first_name) +

        field("last_name", "Last Name", p.last_name) +

        field("phone", "Mobile Number", p.phone) +

        selectField("gender", "Gender", p.gender, choices.gender) +

        field("date_of_birth", "Date of Birth", p.date_of_birth, "date") +

        field("city", "City", p.city) +

        field("state", "State", p.state) +

        field("country", "Country", p.country || "India")

      );

    }

    if (section === "summary") {

      return textarea("summary", "Professional Summary", p.summary, 8);

    }

    if (section === "skills") {

      var skills = (p.skills || []).join(", ");

      return field("skills", "Skills (comma separated)", skills);

    }

    if (section === "career") {

      return (

        field("preferred_roles", "Preferred Roles (comma separated)", (p.preferred_roles || []).join(", ")) +

        field("preferred_location", "Preferred Location", p.preferred_location) +

        field("expected_salary", "Expected Salary (LPA per annum)", p.expected_salary_lpa, "number") +

        '<div class="mb-3"><p class="form-text text-muted mb-0">Enter in Lakhs per annum (e.g. 12 for ₹12L PA).</p></div>' +

        selectField("employment_type_preference", "Employment Type", p.employment_type_preference, choices.employment_type_preference) +

        selectField("work_mode_preference", "Work Mode", p.work_mode_preference, choices.work_mode_preference) +

        field("notice_period_days", "Notice Period (days)", p.notice_period_days, "number")

      );

    }

    if (section === "social") {

      return (

        field("linkedin_url", "LinkedIn URL", p.linkedin_url) +

        field("github_url", "GitHub URL", p.github_url) +

        field("portfolio_url", "Portfolio URL", p.portfolio_url) +

        field("personal_website", "Personal Website", p.personal_website)

      );

    }

    return "";

  }



  function buildNestedFields(type, item) {

    if (type === "experience") {

      return (

        field("company_name", "Company", item.company_name) +

        field("title", "Designation", item.title) +

        selectField("employment_type", "Employment Type", item.employment_type, (state.choices || {}).employment_type) +

        field("location", "Location", item.location) +

        field("start_date", "Start Date", item.start_date, "date") +

        checkbox("is_current", "Currently working here", item.is_current) +

        field("end_date", "End Date", item.is_current ? "" : item.end_date, "date") +

        textarea("description", "Description", item.description, 4)

      );

    }

    if (type === "education") {

      return (

        field("degree", "Degree", item.degree) +

        field("university", "University", item.university || item.institution) +

        field("college", "College", item.college) +

        field("field_of_study", "Specialization", item.field_of_study) +

        field("percentage", "Percentage", item.percentage, "number") +

        field("cgpa", "CGPA", item.cgpa, "number") +

        field("start_year", "Start Year", item.start_year, "number") +

        field("end_year", "End Year", item.end_year, "number")

      );

    }

    if (type === "project") {

      return (

        field("title", "Project Title", item.title) +

        textarea("description", "Description", item.description, 3) +

        field("technologies", "Technologies (comma separated)", (item.technologies || []).join(", ")) +

        field("project_url", "Project URL", item.project_url) +

        field("github_url", "GitHub URL", item.github_url)

      );

    }

    if (type === "certification") {

      return (

        field("name", "Certification Name", item.name) +

        field("issuing_organization", "Organization", item.issuing_organization) +

        field("issue_date", "Issue Date", item.issue_date, "date") +

        field("credential_id", "Credential ID", item.credential_id) +

        field("credential_url", "Credential URL", item.credential_url)

      );

    }

    return "";

  }



  function field(name, label, value, type) {

    type = type || "text";

    value = value == null ? "" : value;

    return (

      '<div class="mb-3"><label class="form-label" for="jsp_' +

      name +

      '">' +

      label +

      '</label><input class="form-control" id="jsp_' +

      name +

      '" name="' +

      name +

      '" type="' +

      type +

      '" value="' +

      escapeAttr(String(value)) +

      '"></div>'

    );

  }



  function textarea(name, label, value, rows) {

    value = value == null ? "" : value;

    return (

      '<div class="mb-3"><label class="form-label" for="jsp_' +

      name +

      '">' +

      label +

      '</label><textarea class="form-control" id="jsp_' +

      name +

      '" name="' +

      name +

      '" rows="' +

      (rows || 4) +

      '">' +

      escapeHtml(String(value)) +

      "</textarea></div>"

    );

  }



  function selectField(name, label, value, options) {

    options = options || [];

    var html =

      '<div class="mb-3"><label class="form-label" for="jsp_' +

      name +

      '">' +

      label +

      '</label><select class="form-select" id="jsp_' +

      name +

      '" name="' +

      name +

      '"><option value="">—</option>';

    options.forEach(function (opt) {

      var selected = opt.value === value ? " selected" : "";

      html += '<option value="' + escapeAttr(opt.value) + '"' + selected + ">" + escapeHtml(opt.label) + "</option>";

    });

    html += "</select></div>";

    return html;

  }



  function checkbox(name, label, checked) {

    return (

      '<div class="form-check mb-3"><input class="form-check-input" type="checkbox" id="jsp_' +

      name +

      '" name="' +

      name +

      '"' +

      (checked ? " checked" : "") +

      '><label class="form-check-label" for="jsp_' +

      name +

      '">' +

      label +

      "</label></div>"

    );

  }



  function formToObject(form) {

    var data = {};

    new FormData(form).forEach(function (value, key) {

      if (key === "csrfmiddlewaretoken") return;

      data[key] = value;

    });

    return data;

  }



  function uploadFile(url, file, fieldName) {

    var fd = new FormData();

    fd.append("file", file);

    fd.append(fieldName, file);

    return fetch(url, {

      method: "POST",

      body: fd,

      headers: { "X-CSRFToken": getCsrfToken(), "X-Requested-With": "XMLHttpRequest" },

      credentials: "same-origin",

    })

      .then(parseResponse)

      .then(handleProfileResponse)

      .catch(function (err) {

        showToast(err && err.error ? err.error : "Upload failed. Please try again.", true);

      });

  }



  function deleteNested(type, id) {

    var url;

    if (type === "experience") url = urls.experience_detail.replace("__id__", id);

    else if (type === "education") url = urls.education_detail.replace("__id__", id);

    else if (type === "project") url = urls.project_detail.replace("__id__", id);

    else if (type === "certification") url = urls.certification_detail.replace("__id__", id);

    api("DELETE", url)

      .then(function () {

        showToast("Entry removed successfully.");

        window.setTimeout(function () {

          window.location.reload();

        }, 800);

      })

      .catch(function (err) {

        showToast(err && err.error ? err.error : "Unable to delete entry.", true);

      });

  }



  function api(method, url, body) {

    var opts = {

      method: method,

      headers: {

        "X-CSRFToken": getCsrfToken(),

        "X-Requested-With": "XMLHttpRequest",

      },

      credentials: "same-origin",

    };

    if (body && method !== "GET" && method !== "DELETE") {

      opts.headers["Content-Type"] = "application/json";

      opts.body = JSON.stringify(body);

    }

    return fetch(url, opts).then(parseResponse);

  }



  function parseResponse(res) {

    var contentType = res.headers.get("content-type") || "";

    if (contentType.indexOf("application/json") === -1) {

      if (res.status === 403) {

        return Promise.reject({ error: "Session expired or invalid security token. Please refresh the page." });

      }

      return Promise.reject({ error: "Unable to save your profile. Please try again." });

    }

    return res.json().then(function (data) {

      if (!res.ok || !data.success) {

        return Promise.reject({ error: data.error || "Request failed." });

      }

      return data;

    });

  }



  function handleProfileResponse(res, options) {

    if (!res || !res.data) return;

    window.JSP_PROFILE = res.data;

    state = res.data;

    applyProfileToPage(res.data);

    options = options || {};

    var rec = res.data.recommendations;

    if (options.section === "career" && rec) {

      applyCareerToPage(res.data);

      var message = rec.total_matches > 0

        ? "Career preferences saved. " + rec.total_matches + " jobs match your profile"

          + (rec.new_matches_count > 0 ? " (" + rec.new_matches_count + " new)." : ".")

        : "Career preferences saved. We'll notify you when matching jobs are posted.";

      if (window.EduNotify) {

        window.EduNotify.success(message, { duration: 4800 });

      } else {

        showToast(message);

      }

      if (rec.unread_notification_count != null) {

        updateNotificationBadge(rec.unread_notification_count);

      }

      document.dispatchEvent(new CustomEvent("edu:recommendations-updated", { detail: rec }));

      return;

    }

    showToast("Profile updated successfully.");

    window.setTimeout(function () {

      window.location.reload();

    }, 1500);

  }



  function applyCareerToPage(data) {

    var careerSection = null;

    document.querySelectorAll(".jsp-section").forEach(function (section) {

      var title = section.querySelector(".jsp-section__title");

      if (title && title.textContent.indexOf("Career Preferences") !== -1) {

        careerSection = section;

      }

    });

    if (!careerSection) return;

    var fields = careerSection.querySelectorAll(".jsp-field p");

    if (fields.length >= 6) {

      var roles = (data.preferred_roles || []).join(", ") || "—";

      fields[0].textContent = roles;

      fields[1].textContent = data.preferred_location || "—";

      fields[2].textContent = data.expected_salary_display || (data.expected_salary_lpa ? formatSalaryLpa(data.expected_salary_lpa) : "—");

      fields[3].textContent = employmentLabel(data.employment_type_preference);

      fields[4].textContent = workModeLabel(data.work_mode_preference);

      fields[5].textContent = data.notice_period_days != null ? data.notice_period_days + " days" : "—";

    }

  }



  function formatSalaryLpa(value) {

    var num = parseFloat(value);

    if (isNaN(num)) return value;

    var label = num >= 1 ? num.toFixed(0) : num.toFixed(1);

    label = label.replace(/\.0$/, "");

    return "₹" + label + "L PA";

  }



  function employmentLabel(value) {

    var choices = (state.choices || {}).employment_type_preference || [];

    for (var i = 0; i < choices.length; i++) {

      if (choices[i].value === value) return choices[i].label;

    }

    return value || "—";

  }



  function workModeLabel(value) {

    var choices = (state.choices || {}).work_mode_preference || [];

    for (var i = 0; i < choices.length; i++) {

      if (choices[i].value === value) return choices[i].label;

    }

    return value || "—";

  }



  function updateNotificationBadge(count) {

    var badge = document.querySelector(".jsd-icon-btn--notif .jsd-icon-btn__badge");

    var btn = document.querySelector(".jsd-icon-btn--notif");

    if (!btn) return;

    if (count > 0) {

      if (!badge) {

        badge = document.createElement("span");

        badge.className = "jsd-icon-btn__badge";

        badge.setAttribute("aria-hidden", "true");

        btn.appendChild(badge);

      }

      badge.textContent = count > 9 ? "9+" : String(count);

      badge.hidden = false;

    } else if (badge) {

      badge.hidden = true;

    }

  }



  function isProfileVerified(data, pct) {

    if (pct == null) {

      pct = data.completion && data.completion.percentage != null

        ? data.completion.percentage

        : data.completion_percentage;

    }

    pct = parseInt(pct, 10) || 0;

    if (pct < 100) return false;

    if (data.completion && data.completion.profile_completed === false) return false;

    return pct >= 100;

  }



  function updateCompletionVerifiedLabel(pct, data) {

    var mini = document.getElementById("jspCompletionMini");

    if (!mini) return;

    var verified = document.getElementById("jspCompletionVerified");

    var show = isProfileVerified(data || state || {}, pct);

    if (show) {

      if (!verified) {

        verified = document.createElement("p");

        verified.className = "jsp-completion-mini__verified";

        verified.id = "jspCompletionVerified";

        verified.innerHTML = '<i class="bi bi-patch-check-fill" aria-hidden="true"></i> Verified Profile';

        var btn = mini.querySelector("[data-jsp-edit]");

        if (btn) mini.insertBefore(verified, btn);

        else mini.appendChild(verified);

      }

    } else if (verified) {

      verified.remove();

    }

  }



  function updateVerifiedBadge(pct, data) {

    var nameEl = document.getElementById("jspFullName");

    if (!nameEl) return;

    var nameWrap = nameEl.parentElement;

    if (!nameWrap || !nameWrap.classList.contains("jsp-name")) return;

    var badge = document.getElementById("jspVerifiedBadge");

    var show = isProfileVerified(data || state || {}, pct);

    if (show) {

      if (!badge) {

        badge = document.createElement("span");

        badge.className = "jsp-verified-badge";

        badge.id = "jspVerifiedBadge";

        badge.title = "Verified profile — 100% complete";

        badge.innerHTML = '<i class="bi bi-patch-check-fill" aria-hidden="true"></i><span class="visually-hidden">Verified profile</span>';

        nameWrap.appendChild(badge);

      }

    } else if (badge) {

      badge.remove();

    }

  }



  function applyProfileToPage(data) {
    var nameEl = document.getElementById("jspFullName");
    var headlineEl = document.getElementById("jspHeadline");

    if (nameEl) nameEl.textContent = data.full_name || "";
    if (headlineEl) {
      if (data.headline && data.headline.trim()) {
        headlineEl.textContent = data.headline;
        headlineEl.hidden = false;
      } else {
        headlineEl.textContent = "";
        headlineEl.hidden = true;
      }
    }

    var metaEl = document.getElementById("jspMeta");
    if (metaEl) {
      var companySpan = document.getElementById("jspMetaCompany");
      if (data.current_company && data.current_company.trim()) {
        if (!companySpan) {
          companySpan = document.createElement("span");
          companySpan.id = "jspMetaCompany";
          metaEl.prepend(companySpan);
        }
        companySpan.innerHTML = '<i class="bi bi-building"></i> ' + escapeHtml(data.current_company);
        companySpan.hidden = false;
      } else if (companySpan) {
        companySpan.remove();
      }

      var locSpan = document.getElementById("jspMetaLocation");
      var locDisplay = data.city || data.state || data.country || data.current_location
        ? [data.city, data.state, data.country].filter(Boolean).join(", ") || data.current_location
        : "";
      if (locDisplay) {
        if (!locSpan) {
          locSpan = document.createElement("span");
          locSpan.id = "jspMetaLocation";
          metaEl.appendChild(locSpan);
        }
        locSpan.innerHTML = '<i class="bi bi-geo-alt"></i> ' + escapeHtml(locDisplay);
        locSpan.hidden = false;
      } else if (locSpan) {
        locSpan.remove();
      }

      var expSpan = document.getElementById("jspMetaExperience");
      if (data.experience_years != null) {
        var expText = data.experience_years === 0 ? "Fresher" : data.experience_years + " yr" + (data.experience_years !== 1 ? "s" : "");
        if (!expSpan) {
          expSpan = document.createElement("span");
          expSpan.id = "jspMetaExperience";
          metaEl.appendChild(expSpan);
        }
        expSpan.innerHTML = '<i class="bi bi-briefcase"></i> ' + escapeHtml(expText);
        expSpan.hidden = false;
      } else if (expSpan) {
        expSpan.remove();
      }
    }

    var pct = data.completion && data.completion.percentage != null
      ? data.completion.percentage
      : data.completion_percentage;

    if (pct != null) {
      var pctLabel = document.getElementById("jspCompletionPctLabel");
      var bar = document.getElementById("jspCompletionBar");
      var mini = document.getElementById("jspCompletionMini");

      if (pctLabel) pctLabel.textContent = pct + "%";
      if (bar) bar.style.width = pct + "%";
      if (bar && bar.parentElement) {
        bar.parentElement.setAttribute("aria-valuenow", String(pct));
      }

      updateVerifiedBadge(pct, data);
      updateCompletionVerifiedLabel(pct, data);

      if (mini) {
        mini.classList.toggle("jsp-completion-mini--complete", isProfileVerified(data, pct));
      }
    }

    var headerName = document.querySelector(".jsd-header__profile-name");
    if (headerName && data.full_name) headerName.textContent = data.full_name;
  }



  function setButtonLoading(btn, loading) {

    if (!btn) return;

    if (loading) {

      btn.disabled = true;

      btn.dataset.jspOriginalText = btn.innerHTML;

      btn.innerHTML = '<span class="jsp-btn-spinner" aria-hidden="true"></span> Saving…';

    } else {

      btn.disabled = false;

      if (btn.dataset.jspOriginalText) {

        btn.innerHTML = btn.dataset.jspOriginalText;

        delete btn.dataset.jspOriginalText;

      }

    }

  }



  function showModal(id) {

    var el = document.getElementById(id);

    if (window.bootstrap && el) {

      window.bootstrap.Modal.getOrCreateInstance(el).show();

    }

  }



  function hideModal(id) {

    var el = document.getElementById(id);

    if (window.bootstrap && el) {

      var inst = window.bootstrap.Modal.getInstance(el);

      if (inst) inst.hide();

    }

  }



  function showToast(msg, isError) {

    if (!window.EduNotify) return;

    if (isError) window.EduNotify.error(msg);

    else window.EduNotify.success(msg);

  }



  function getCsrfToken() {

    var meta = document.querySelector('meta[name="csrf-token"]');

    if (meta && meta.getAttribute("content")) {

      return meta.getAttribute("content");

    }

    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');

    if (input && input.value) {

      return input.value;

    }

    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);

    return match ? decodeURIComponent(match[1]) : "";

  }



  function sectionTitle(section) {

    var map = {

      header: "Edit Profile Header",

      basic: "Edit Basic Information",

      summary: "Edit Professional Summary",

      skills: "Edit Skills",

      career: "Edit Career Preferences",

      social: "Edit Social Links",

    };

    return map[section] || "Edit Section";

  }



  function nestedLabel(type) {

    return { experience: "Experience", education: "Education", project: "Project", certification: "Certification" }[

      type

    ];

  }



  function findNestedItem(type, id) {

    var keyMap = {

      experience: "experiences",

      education: "education",

      project: "projects",

      certification: "certifications",

    };

    var list = state[keyMap[type]] || [];

    for (var i = 0; i < list.length; i++) {

      if (String(list[i].id) === String(id)) {

        return list[i];

      }

    }

    return { id: id };

  }



  function escapeHtml(s) {

    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  }



  function escapeAttr(s) {

    return escapeHtml(s).replace(/"/g, "&quot;");

  }

  window.JSPHelpers = {
    api: api,
    showToast: showToast,
    notify: window.EduNotify,
    confirm: function (options) {
      return window.EduNotify ? window.EduNotify.confirm(options) : Promise.resolve(false);
    },
    showModal: showModal,
    hideModal: hideModal,
    setButtonLoading: setButtonLoading,
    getState: function () {
      return state;
    },
    setState: function (data) {
      state = data;
      window.JSP_PROFILE = data;
    },
    findNestedItem: findNestedItem,
  };

})();


