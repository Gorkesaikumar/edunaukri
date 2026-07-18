/** Professor profile page — section editing via JSON API */

(function () {
  "use strict";

  var SECTION_FIELDS = {
    basic: [
      { name: "first_name", label: "First Name", type: "text", required: true },
      { name: "last_name", label: "Last Name", type: "text", required: true },
      { name: "phone", label: "Phone", type: "tel" },
    ],
    professional: [
      { name: "current_designation", label: "Current Designation", type: "text" },
      { name: "current_institution", label: "Current Institution", type: "text" },
      { name: "highest_qualification", label: "Highest Qualification", type: "text" },
      { name: "specialization", label: "Specialization", type: "text" },
      { name: "teaching_experience_years", label: "Teaching Experience (years)", type: "number", min: 0 },
      { name: "industry_experience_years", label: "Industry Experience (years)", type: "number", min: 0 },
      { name: "expected_salary_lpa", label: "Expected Salary (LPA)", type: "number", step: "0.1", min: 0 },
    ],
    research: [
      { name: "specialization", label: "Specialization", type: "text" },
      { name: "research_interests", label: "Research Interests", type: "textarea" },
      { name: "publications_count", label: "Publications Count", type: "number", min: 0 },
    ],
    locations: [
      { name: "preferred_locations", label: "Preferred Locations (comma-separated)", type: "text" },
    ],
  };

  var SECTION_TITLES = {
    basic: "Basic Information",
    professional: "Professional Details",
    research: "Research",
    locations: "Preferred Locations",
  };

  function root() {
    return document.getElementById("fjpProfileRoot");
  }

  function csrf() {
    if (window.FJP_PROFILE && window.FJP_PROFILE.csrfToken) return window.FJP_PROFILE.csrfToken;
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute("content") || "";
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function notify(type, message) {
    if (window.EduNotify && window.EduNotify.toast) window.EduNotify.toast(type, message);
  }

  function apiUrl(key) {
    var el = root();
    return el ? el.getAttribute("data-api-" + key) : "";
  }

  function sectionUrl(section) {
    var template = apiUrl("section");
    return template ? template.replace("{section}", section) : "";
  }

  function parseResponse(res) {
    var ct = res.headers.get("content-type") || "";
    if (ct.indexOf("application/json") === -1) {
      return Promise.reject(new Error("Unexpected server response."));
    }
    return res.json().then(function (body) {
      if (!res.ok || !body.success) throw new Error(body.error || "Request failed.");
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

  function uploadFile(url, file, fieldName) {
    var fd = new FormData();
    fd.append(fieldName, file);
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
      body: fd,
    }).then(parseResponse);
  }

  function text(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value || "—";
  }

  function applyProfile(data) {
    if (!data) return;
    text("fjpFullName", data.full_name);
    text("fjpFirstName", data.first_name);
    text("fjpLastName", data.last_name);
    text("fjpPhone", data.phone);
    text("fjpPhoneDisplay", data.phone || "Add phone number");
    text("fjpSpecDisplay", data.specialization || "Add specialization");
    text("fjpDesignation", data.current_designation);
    text("fjpInstitution", data.current_institution);
    text("fjpQualification", data.highest_qualification);
    text("fjpExperience", data.experience_display);
    text("fjpSalary", data.expected_salary_display);
    text("fjpSpecialization", data.specialization);
    text("fjpResearch", data.research_interests);
    text("fjpPublications", String(data.publications_count || 0));
    text("fjpLocations", data.preferred_locations_display);
    text("fjpCvName", data.cv_filename || "No CV uploaded yet.");

    var pct = document.getElementById("fjpCompletionPct");
    var bar = document.getElementById("fjpCompletionBar");
    var strengthEl = document.getElementById("fjpCompletionStrength");
    var strengthText = document.getElementById("fjpCompletionStrengthText");
    var descEl = document.getElementById("fjpCompletionDesc");
    var val = data.completion_percentage || 0;
    
    // Check if we just hit 100% and need to celebrate
    var justCompleted = (val === 100 && pct && pct.textContent.indexOf("100%") === -1);
    
    if (pct) pct.textContent = val + "% Complete";
    if (bar) bar.style.width = val + "%";
    if (strengthEl && strengthText) {
      var sClass = "is-beginner", sLabel = "Beginner";
      if (val === 100) { sClass = "is-complete"; sLabel = "Complete"; }
      else if (val >= 75) { sClass = "is-strong"; sLabel = "Strong"; }
      else if (val >= 40) { sClass = "is-intermediate"; sLabel = "Intermediate"; }
      strengthEl.className = "fjd-profile-card__strength " + sClass;
      strengthText.textContent = sLabel;
    }
    
    if (val === 100 && descEl) {
      descEl.classList.add("d-none");
    } else if (descEl) {
      descEl.classList.remove("d-none");
    }
    
    if (justCompleted) {
      var canvas = document.getElementById("jsdHeroConfetti");
      if (canvas) startConfetti(canvas, 3000);
    }
    if (data.completion && data.completion.checklist && document.getElementById("fjpCompletionList")) {
      var listEl = document.getElementById("fjpCompletionList");
      listEl.innerHTML = data.completion.checklist.map(function (item) {
        var isDone = item.completed;
        var chipClass = isDone ? "fjd-status-chip--done" : "fjd-status-chip--pending";
        var chipText = isDone ? "Completed" : "Incomplete";
        var iconClass = isDone ? "bi-check-circle-fill" : "bi-circle";
        var iconTint = isDone ? "icon--done" : "icon--pending";
        var itemClass = isDone ? "fjd-profile-card__item is-completed" : "fjd-profile-card__item";
        return '<li class="' + itemClass + '">' +
          '<a href="' + item.url + '" class="fjd-profile-card__row" title="' + (isDone ? 'Completed: ' : 'Complete ') + item.label + '">' +
            '<div class="fjd-profile-card__row-left">' +
              '<span class="fjd-profile-card__icon ' + iconTint + '"><i class="bi ' + iconClass + '" aria-hidden="true"></i></span>' +
              '<span class="fjd-profile-card__label">' + item.label + '</span>' +
            '</div>' +
            '<div class="fjd-profile-card__row-right">' +
              '<span class="fjd-status-chip ' + chipClass + '">' + chipText + '</span>' +
              '<i class="bi bi-chevron-right fjd-profile-card__chevron" aria-hidden="true"></i>' +
            '</div>' +
          '</a></li>';
      }).join("");
    }

    var avatar = document.getElementById("fjpAvatar");
    if (avatar && data.avatar_url) {
      avatar.innerHTML = '<img src="' + data.avatar_url + '" alt="">';
    }

    notify("success", "Profile updated.");
  }

  function openSectionModal(section) {
    var fields = SECTION_FIELDS[section];
    if (!fields) return;
    var container = document.getElementById("fjpSectionFields");
    var form = document.getElementById("fjpSectionForm");
    var title = document.getElementById("fjpSectionModalTitle");
    if (!container || !form) return;

    title.textContent = "Edit " + (SECTION_TITLES[section] || section);
    container.innerHTML = fields
      .map(function (f) {
        if (f.type === "textarea") {
          return (
            '<div class="mb-3"><label class="form-label" for="fjp_' +
            f.name +
            '">' +
            f.label +
            '</label><textarea class="form-control" id="fjp_' +
            f.name +
            '" name="' +
            f.name +
            '" rows="4"></textarea></div>'
          );
        }
        var attrs = 'class="form-control" id="fjp_' + f.name + '" name="' + f.name + '"';
        if (f.type) attrs += ' type="' + f.type + '"';
        if (f.required) attrs += " required";
        if (f.min !== undefined) attrs += ' min="' + f.min + '"';
        if (f.step) attrs += ' step="' + f.step + '"';
        return '<div class="mb-3"><label class="form-label" for="fjp_' + f.name + '">' + f.label + "</label><input " + attrs + "></div>";
      })
      .join("");

    form.setAttribute("data-section", section);
    fields.forEach(function (f) {
      var input = document.getElementById("fjp_" + f.name);
      if (!input) return;
      if (section === "locations" && f.name === "preferred_locations") {
        var locEl = document.getElementById("fjpLocations");
        input.value = locEl && locEl.textContent !== "—" ? locEl.textContent : "";
        return;
      }
      var src = document.getElementById(
        f.name === "first_name"
          ? "fjpFirstName"
          : f.name === "last_name"
            ? "fjpLastName"
            : f.name === "phone"
              ? "fjpPhone"
              : f.name === "current_designation"
                ? "fjpDesignation"
                : f.name === "current_institution"
                  ? "fjpInstitution"
                  : f.name === "highest_qualification"
                    ? "fjpQualification"
                    : f.name === "specialization"
                      ? "fjpSpecialization"
                      : f.name === "research_interests"
                        ? "fjpResearch"
                        : f.name === "publications_count"
                          ? "fjpPublications"
                          : null
      );
      if (src) input.value = src.textContent === "—" ? "" : src.textContent.trim();
    });

    var modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("fjpSectionModal"));
    modal.show();
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
      body: JSON.stringify(payload),
    }).then(parseResponse);
  }

  function deleteJson(url) {
    return fetch(url, {
      method: "DELETE",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
    }).then(parseResponse);
  }

  function renderQualifications(items) {
    var list = document.getElementById("fjpQualList");
    if (!list) return;
    list.innerHTML = "";
    (items || []).forEach(function (q) {
      var li = document.createElement("li");
      li.className = "fjp-qual-item";
      li.setAttribute("data-qual-id", q.id);
      var label = q.name;
      if (q.institution_name) label += " · " + q.institution_name;
      if (q.year_obtained) label += " · " + q.year_obtained;
      li.innerHTML =
        "<span>" +
        label +
        '</span><span class="fjp-qual-actions">' +
        '<button type="button" class="fjp-btn-text" data-fjp-edit-qual data-id="' +
        q.id +
        '" data-name="' +
        (q.name || "").replace(/"/g, "&quot;") +
        '" data-institution="' +
        (q.institution_name || "").replace(/"/g, "&quot;") +
        '" data-year="' +
        (q.year_obtained || "") +
        '">Edit</button>' +
        '<button type="button" class="fjp-btn-text text-danger" data-fjp-delete-qual data-id="' +
        q.id +
        '">Delete</button></span>';
      list.appendChild(li);
    });
    bindQualificationActions();
  }

  function bindQualificationActions() {
    document.querySelectorAll("[data-fjp-edit-qual]").forEach(function (btn) {
      btn.onclick = function () {
        openQualModal({
          id: btn.getAttribute("data-id"),
          name: btn.getAttribute("data-name") || "",
          institution_name: btn.getAttribute("data-institution") || "",
          year_obtained: btn.getAttribute("data-year") || "",
        });
      };
    });
    document.querySelectorAll("[data-fjp-delete-qual]").forEach(function (btn) {
      btn.onclick = function () {
        var id = btn.getAttribute("data-id");
        var base = apiUrl("qualifications").replace(/\/$/, "");
        deleteJson(base + "/" + id + "/")
          .then(function () {
            btn.closest(".fjp-qual-item").remove();
            notify("success", "Qualification removed.");
          })
          .catch(function (err) {
            notify("error", err.message || "Could not delete qualification.");
          });
      };
    });
  }

  function openQualModal(data) {
    var modalEl = document.getElementById("fjpQualModal");
    if (!modalEl) return;
    document.getElementById("fjpQualModalTitle").textContent = data.id ? "Edit Qualification" : "Add Qualification";
    document.getElementById("fjpQualId").value = data.id || "";
    document.getElementById("fjpQualName").value = data.name || "";
    document.getElementById("fjpQualInstitution").value = data.institution_name || "";
    document.getElementById("fjpQualYear").value = data.year_obtained || "";
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-fjp-edit]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openSectionModal(btn.getAttribute("data-fjp-edit"));
      });
    });

    var form = document.getElementById("fjpSectionForm");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var section = form.getAttribute("data-section");
        var payload = {};
        (SECTION_FIELDS[section] || []).forEach(function (f) {
          var input = document.getElementById("fjp_" + f.name);
          if (input) payload[f.name] = input.value;
        });
        patchJson(sectionUrl(section), payload)
          .then(function (res) {
            applyProfile(res.data);
            bootstrap.Modal.getInstance(document.getElementById("fjpSectionModal")).hide();
          })
          .catch(function (err) {
            notify("error", err.message || "Could not save.");
          });
      });
    }

    var photoInput = document.getElementById("fjpPhotoInput");
    if (photoInput) {
      photoInput.addEventListener("change", function () {
        if (!photoInput.files[0]) return;
        uploadFile(apiUrl("photo"), photoInput.files[0], "photo")
          .then(function (res) {
            applyProfile(res.data);
          })
          .catch(function (err) {
            notify("error", err.message || "Photo upload failed.");
          });
      });
    }

    var cvInput = document.getElementById("fjpCvInput");
    if (cvInput) {
      cvInput.addEventListener("change", function () {
        if (!cvInput.files[0]) return;
        uploadFile(apiUrl("cv"), cvInput.files[0], "cv")
          .then(function (res) {
            applyProfile(res.data);
          })
          .catch(function (err) {
            notify("error", err.message || "CV upload failed.");
          });
      });
    }

    if (window.location.hash === "#research") {
      var research = document.getElementById("research");
      if (research) research.scrollIntoView({ behavior: "smooth" });
    }

    var addQualBtn = document.getElementById("fjpAddQualBtn");
    if (addQualBtn) {
      addQualBtn.addEventListener("click", function () {
        openQualModal({});
      });
    }

    var qualForm = document.getElementById("fjpQualForm");
    if (qualForm) {
      qualForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var id = document.getElementById("fjpQualId").value;
        var payload = {
          name: document.getElementById("fjpQualName").value.trim(),
          institution_name: document.getElementById("fjpQualInstitution").value.trim(),
          year_obtained: document.getElementById("fjpQualYear").value.trim(),
        };
        var base = apiUrl("qualifications").replace(/\/$/, "");
        var req = id
          ? patchJson(base + "/" + id + "/", payload)
          : postJson(base + "/", payload);
        req
          .then(function (res) {
            bootstrap.Modal.getInstance(document.getElementById("fjpQualModal")).hide();
            return fetch(apiUrl("profile"), {
              credentials: "same-origin",
              headers: { "X-Requested-With": "XMLHttpRequest" },
            })
              .then(parseResponse)
              .then(function (body) {
                renderQualifications(body.data.qualifications);
                notify("success", "Qualification saved.");
              });
          })
          .catch(function (err) {
            notify("error", err.message || "Could not save qualification.");
          });
      });
    }

    bindQualificationActions();
  });
  function startConfetti(canvas, durationMs) {
    if (!canvas || !canvas.getContext) return null;
    var ctx = canvas.getContext("2d");
    var rect = canvas.parentElement ? canvas.parentElement.getBoundingClientRect() : canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    var colors = ["#6366f1", "#8b5cf6", "#22c55e", "#f59e0b", "#ec4899", "#0ea5e9"];
    var particles = [];
    var count = Math.min(120, Math.floor((canvas.width * canvas.height) / 4500));
    for (var i = 0; i < count; i++) {
      particles.push({
        x: canvas.width * 0.5 + (Math.random() - 0.5) * canvas.width * 0.35,
        y: canvas.height * 0.35,
        vx: (Math.random() - 0.5) * 8,
        vy: Math.random() * -8 - 3,
        size: Math.random() * 6 + 3,
        color: colors[Math.floor(Math.random() * colors.length)],
        rotation: Math.random() * 360,
        spin: (Math.random() - 0.5) * 12,
        life: 1,
      });
    }
    var start = performance.now();
    var rafId = 0;
    function frame(now) {
      var elapsed = now - start;
      var progress = Math.min(1, elapsed / durationMs);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(function (p) {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.18;
        p.vx *= 0.99;
        p.rotation += p.spin;
        p.life = 1 - progress;
        if (p.life <= 0) return;
        ctx.save();
        ctx.globalAlpha = Math.max(0, p.life);
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.65);
        ctx.restore();
      });
      if (progress < 1) {
        rafId = requestAnimationFrame(frame);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
    rafId = requestAnimationFrame(frame);
    return rafId;
  }

})();
