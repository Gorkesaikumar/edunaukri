(function () {
  "use strict";

  function csrf() {
    if (window.REC_PORTAL && window.REC_PORTAL.csrfToken) return window.REC_PORTAL.csrfToken;
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function notify(type, message) {
    if (window.EduNotify && window.EduNotify.toast) {
      window.EduNotify.toast(type, message);
    }
  }

  function parseResponse(res) {
    var isJson = res.headers.get("content-type") && res.headers.get("content-type").indexOf("application/json") !== -1;
    if (!isJson) {
      if (!res.ok) throw new Error("Server error occurred. Please try again.");
      throw new Error("Unexpected response from server.");
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

  function refreshCompanyVerifyUI(company) {
    if (!company || !company.is_verified) return;

    var nameEl = document.getElementById("recCompanyNameDisplay");
    if (nameEl && company.name) nameEl.textContent = company.name;

    var industryEl = document.getElementById("recCompanyIndustryDisplay");
    if (industryEl) {
      industryEl.textContent = company.industry || "Industry not set";
    }

    var badgeHost = document.getElementById("recCompanyVerifiedBadge");
    if (badgeHost && !badgeHost.querySelector(".rcd-verified-badge")) {
      badgeHost.innerHTML =
        '<span class="rcd-verified-badge" title="Verified company">' +
        '<span class="material-symbols-outlined" aria-hidden="true">verified</span>' +
        '<span class="rcd-verified-badge__label">Verified</span></span>';
    }

    var alertHost = document.getElementById("recCompanyVerifyAlert");
    if (alertHost && !alertHost.querySelector(".rec-company-verify-banner")) {
      alertHost.innerHTML =
        '<div class="alert alert-success py-2 small d-flex align-items-center gap-2 mb-3 rec-company-verify-banner">' +
        '<span class="material-symbols-outlined" style="font-size:1.125rem" aria-hidden="true">verified</span>' +
        "Your company is verified and can publish jobs to the marketplace." +
        "</div>";
    }
  }

  function bindProfileForms() {
    var root = document.getElementById("recProfilePage");
    if (!root) return;

    if (window.location.search.indexOf("company_created=1") !== -1) {
      notify("success", "Company profile created and verified successfully.");
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, "", window.location.pathname + window.location.hash);
      }
    }

    var profileForm = document.getElementById("recProfileForm");
    if (profileForm) {
      profileForm.addEventListener("submit", function (e) {
        e.preventDefault();
        patchJson(root.getAttribute("data-api-profile"), {
          first_name: document.getElementById("recFirstName").value.trim(),
          last_name: document.getElementById("recLastName").value.trim(),
          phone: document.getElementById("recPhone").value.trim(),
          official_email: document.getElementById("recOfficialEmail").value.trim(),
          designation: document.getElementById("recDesignation").value.trim(),
          department: document.getElementById("recDepartment").value.trim(),
          company_association: document.getElementById("recAssociation").value.trim(),
        })
          .then(function (body) {
            notify("success", body.message || "Profile saved.");
          })
          .catch(function (err) {
            notify("error", err.message);
          });
      });
    }

    var companyForm = document.getElementById("recCompanyForm");
    if (companyForm) {
      companyForm.addEventListener("submit", function (e) {
        e.preventDefault();
        patchJson(root.getAttribute("data-api-company"), {
          name: document.getElementById("recCompanyName").value.trim(),
          industry: document.getElementById("recCompanyIndustry").value.trim(),
          description: document.getElementById("recCompanyDesc").value.trim(),
          website_url: document.getElementById("recCompanyWebsite").value.trim(),
          headquarters_location: document.getElementById("recCompanyHQ").value.trim(),
          city: document.getElementById("recCompanyCity").value.trim(),
          state: document.getElementById("recCompanyState").value.trim(),
          phone: document.getElementById("recCompanyPhone").value.trim(),
        })
          .then(function (body) {
            if (body.data) refreshCompanyVerifyUI(body.data);
            notify("success", body.message || "Company profile updated successfully.");
          })
          .catch(function (err) {
            notify("error", err.message);
          });
      });
    }

    var createForm = document.getElementById("recCreateCompanyForm");
    if (createForm) {
      createForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var btn = createForm.querySelector('button[type="submit"]');
        if (btn) {
            btn.disabled = true;
            btn.classList.add("is-loading");
        }
        postJson(root.getAttribute("data-api-create-company"), {
          name: document.getElementById("recNewCompanyName").value.trim(),
          industry: document.getElementById("recNewCompanyIndustry").value.trim(),
          description: document.getElementById("recNewCompanyDesc").value.trim(),
        })
          .then(function (body) {
            window.location.href = window.location.pathname + "?company_created=1";
          })
          .catch(function (err) {
            if (btn) {
                btn.disabled = false;
                btn.classList.remove("is-loading");
            }
            notify("error", err.message);
          });
      });
    }
  }

  function bindJobsPage() {
    var root = document.getElementById("recJobsPage");
    if (!root) return;

    if (window.location.search.indexOf("created=1") !== -1) {
      notify("success", "Job draft created successfully. You can publish it when ready.");
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, "", window.location.pathname + window.location.hash);
      }
    }

    var modalEl = document.getElementById("recNewJobModal");
    var openBtn = document.getElementById("recNewJobBtn");
    if (openBtn && modalEl) {
      var modal = new bootstrap.Modal(modalEl);
      openBtn.addEventListener("click", function () {
        document.getElementById("recNewJobError").hidden = true;
        modal.show();
      });
      document.getElementById("recNewJobSubmit").addEventListener("click", function () {
        var errEl = document.getElementById("recNewJobError");
        postJson(root.getAttribute("data-api-create"), {
          title: document.getElementById("recJobTitle").value.trim(),
          description: document.getElementById("recJobDesc").value.trim(),
          location: document.getElementById("recJobLocation").value.trim(),
          is_remote: document.getElementById("recJobRemote").checked,
        })
          .then(function (body) {
            modal.hide();
            notify("success", body.message || "Draft created.");
            window.location.reload();
          })
          .catch(function (err) {
            errEl.textContent = err.message;
            errEl.hidden = false;
          });
      });
    }

    document.querySelectorAll(".rec-job-publish").forEach(function (btn) {
      btn.addEventListener("click", function () {
        btn.disabled = true;
        postJson(btn.getAttribute("data-url"))
          .then(function (body) {
            notify("success", body.message || "Job published.");
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message);
            btn.disabled = false;
          });
      });
    });

    document.querySelectorAll(".rec-job-close").forEach(function (btn) {
      btn.addEventListener("click", function () {
        btn.disabled = true;
        postJson(btn.getAttribute("data-url"))
          .then(function (body) {
            notify("success", body.message || "Job closed.");
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message);
            btn.disabled = false;
          });
      });
    });
  }

  function bindCandidatesPage() {
    var root = document.getElementById("recCandidatesPage");
    if (!root) return;

    document.querySelectorAll(".rec-candidate-status").forEach(function (select) {
      select.addEventListener("change", function () {
        var status = select.value;
        if (!status) return;
        select.disabled = true;
        patchJson(select.getAttribute("data-url"), { status: status, notes: "" })
          .then(function (body) {
            notify("success", body.message || "Status updated.");
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message);
            select.disabled = false;
            select.value = "";
          });
      });
    });

    document.querySelectorAll(".rec-candidate-notes-toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var panel = btn.closest(".jsd-app-card").querySelector(".rec-candidate-notes");
        if (panel) panel.hidden = !panel.hidden;
      });
    });

    document.querySelectorAll(".rec-candidate-notes-save").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var panel = btn.closest(".rec-candidate-notes");
        var textarea = panel.querySelector(".rec-candidate-notes-input");
        btn.disabled = true;
        patchJson(textarea.getAttribute("data-url"), { recruiter_notes: textarea.value.trim() })
          .then(function (body) {
            notify("success", body.message || "Notes saved.");
          })
          .catch(function (err) {
            notify("error", err.message);
          })
          .finally(function () {
            btn.disabled = false;
          });
      });
    });
  }

  function bindNotificationsPage() {
    var root = document.getElementById("recNotificationsPage");
    if (!root) return;

    document.querySelectorAll(".rec-notification-read").forEach(function (btn) {
      btn.addEventListener("click", function () {
        btn.disabled = true;
        postJson(btn.getAttribute("data-url"))
          .then(function () {
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message);
            btn.disabled = false;
          });
      });
    });

    var markAll = document.querySelector(".rec-notifications-mark-all");
    if (markAll) {
      markAll.addEventListener("click", function () {
        markAll.disabled = true;
        postJson(markAll.getAttribute("data-url"))
          .then(function () {
            window.location.reload();
          })
          .catch(function (err) {
            notify("error", err.message);
            markAll.disabled = false;
          });
      });
    }
  }

  function bindJobCreatePage() {
    var form = document.getElementById("recJobCreateForm");
    if (!form) return;
    form.addEventListener("submit", function () {
      var btn = document.getElementById("recJobCreateSubmit");
      if (btn) {
        btn.disabled = true;
        btn.classList.add("is-loading");
      }
    });
  }

  function bindJobEditPage() {
    var form = document.getElementById("recJobEditForm");
    if (!form) return;
    form.addEventListener("submit", function () {
      var btn = document.getElementById("recJobEditSubmit");
      if (btn) {
        btn.disabled = true;
        btn.classList.add("is-loading");
      }
    });
  }

  function bindSkillTagging() {
    function setupSkillContainer(containerId, inputId, hiddenId, suggestId) {
      var container = document.getElementById(containerId);
      var input = document.getElementById(inputId);
      var hidden = document.getElementById(hiddenId);
      var suggest = document.getElementById(suggestId);
      if (!container || !input || !hidden) return;

      var debounceTimer = null;

      function updateHidden() {
        var tags = [];
        container.querySelectorAll(".badge[data-skill]").forEach(function (el) {
          var val = el.getAttribute("data-skill");
          if (val && tags.indexOf(val) === -1) tags.push(val);
        });
        hidden.value = tags.join(",");
      }

      function addSkill(skillName) {
        skillName = (skillName || "").trim();
        if (!skillName) return;
        var existing = hidden.value ? hidden.value.split(",") : [];
        if (existing.indexOf(skillName) !== -1) {
          input.value = "";
          if (suggest) suggest.classList.add("d-none");
          return;
        }
        var span = document.createElement("span");
        span.className = "badge bg-primary text-white d-inline-flex align-items-center gap-1 py-2 px-3 rounded-pill";
        if (containerId.indexOf("pref") !== -1) {
          span.className = "badge bg-soft-secondary text-dark d-inline-flex align-items-center gap-1 py-2 px-3 rounded-pill border";
        }
        span.setAttribute("data-skill", skillName);
        span.innerHTML = skillName + ' <span class="material-symbols-outlined small cursor-pointer remove-skill" style="font-size:14px;">close</span>';
        container.insertBefore(span, input);
        updateHidden();
        input.value = "";
        if (suggest) suggest.classList.add("d-none");
      }

      container.addEventListener("click", function (e) {
        if (e.target && e.target.classList.contains("remove-skill")) {
          var badge = e.target.closest(".badge");
          if (badge) {
            badge.parentNode.removeChild(badge);
            updateHidden();
          }
        } else {
          input.focus();
        }
      });

      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === ",") {
          e.preventDefault();
          var val = input.value.replace(/,/g, "").trim();
          if (val) addSkill(val);
        } else if (e.key === "Backspace" && !input.value) {
          var badges = container.querySelectorAll(".badge[data-skill]");
          if (badges.length > 0) {
            var last = badges[badges.length - 1];
            last.parentNode.removeChild(last);
            updateHidden();
          }
        }
      });

      input.addEventListener("input", function () {
        var q = input.value.trim();
        if (!suggest || !window.REC_PORTAL || !window.REC_PORTAL.skillSuggestUrl) return;
        if (q.length < 1) {
          suggest.classList.add("d-none");
          suggest.innerHTML = "";
          return;
        }
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
          fetch(window.REC_PORTAL.skillSuggestUrl + "?q=" + encodeURIComponent(q), {
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest" }
          })
            .then(function (res) { return res.json(); })
            .then(function (data) {
              if (!data.success || !data.data || !data.data.skills || data.data.skills.length === 0) {
                suggest.classList.add("d-none");
                return;
              }
              suggest.innerHTML = "";
              data.data.skills.forEach(function (sk) {
                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "list-group-item list-group-item-action py-2 px-3 small";
                btn.textContent = sk;
                btn.addEventListener("click", function () {
                  addSkill(sk);
                });
                suggest.appendChild(btn);
              });
              suggest.classList.remove("d-none");
            })
            .catch(function () {
              suggest.classList.add("d-none");
            });
        }, 200);
      });

      document.addEventListener("click", function (e) {
        if (suggest && !container.contains(e.target) && !suggest.contains(e.target)) {
          suggest.classList.add("d-none");
        }
      });
    }

    setupSkillContainer("reqSkillsContainer", "jobReqSkillsInput", "jobReqSkillsHidden", "reqSkillsSuggest");
    setupSkillContainer("prefSkillsContainer", "jobPrefSkillsInput", "jobPrefSkillsHidden", "prefSkillsSuggest");
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindProfileForms();
    bindJobsPage();
    bindJobCreatePage();
    bindJobEditPage();
    bindCandidatesPage();
    bindNotificationsPage();
    bindSkillTagging();
  });
})();
