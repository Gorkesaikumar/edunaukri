(function () {
  "use strict";

  var config = window.JM_CONFIG || {};
  var debounceTimer;

  function notify(type, message) {
    if (window.EduNotify && typeof window.EduNotify.toast === "function") {
      window.EduNotify.toast(type, message);
    }
  }

  function showResumeRequiredModal() {
    var modal = document.getElementById("jmResumeRequiredModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "jmResumeRequiredModal";
      modal.className = "jm-apply-modal";
      modal.innerHTML = `
        <div class="jm-apply-modal__dialog" role="dialog" aria-labelledby="jmResumeModalTitle">
            <div class="jm-apply-modal__icon" style="background: #fef3c7; color: #d97706; border-color: #fde68a;">
                <i class="bi bi-file-earmark-text"></i>
            </div>
            <h3 id="jmResumeModalTitle" style="margin-top: 16px;">Upload Resume Required</h3>
            <p style="margin-top: 8px;">Before applying for this job, you need to upload your latest resume. Once your resume is uploaded successfully, you can continue with your application.</p>
            <div class="d-flex gap-2 justify-content-center mt-4 w-100">
                <button type="button" class="ed-btn ed-btn--outline" onclick="document.getElementById('jmResumeRequiredModal').hidden = true;">Cancel</button>
                <a href="${config.resumeUrl}?next=${encodeURIComponent(window.location.href)}" class="ed-btn ed-btn--gradient">Upload Resume</a>
            </div>
        </div>
      `;
      document.body.appendChild(modal);
    }
    modal.hidden = false;
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute("content");
    var input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : config.csrfToken || "";
  }

  function initFilterToggle() {
    var toggle = document.getElementById("jmFilterToggle");
    var sidebar = document.getElementById("jmFiltersSidebar");
    if (!toggle || !sidebar) return;
    toggle.addEventListener("click", function () {
      var open = sidebar.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function initSuggest() {
    var input = document.getElementById("jmSearchInput");
    var list = document.getElementById("jmSuggestList");
    if (!input || !list || !config.suggestApiUrl) return;

    input.addEventListener("input", function () {
      clearTimeout(debounceTimer);
      var q = input.value.trim();
      if (q.length < 2) {
        list.innerHTML = "";
        return;
      }
      debounceTimer = setTimeout(function () {
        fetch(config.suggestApiUrl + "?q=" + encodeURIComponent(q), {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        })
          .then(function (res) {
            return res.json();
          })
          .then(function (payload) {
            if (!payload.success || !payload.data) return;
            list.innerHTML = payload.data
              .map(function (item) {
                return '<option value="' + escapeAttr(item.label) + '"></option>';
              })
              .join("");
          })
          .catch(function () {});
      }, 250);
    });
  }

  function initSaveForms() {
    /* Handled globally by saved-jobs.js via data-save-job-toggle / data-save-job-form */
  }

  function initApplyForms() {
    document.querySelectorAll("[data-apply-job-form], #jmDetailApplyForm").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!config.isJobSeeker) return;
        event.preventDefault();
        fetch(form.action, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCsrfToken(),
          },
          body: new FormData(form),
        })
          .then(function (res) {
            return res.json();
          })
          .then(function (payload) {
            if (payload.success) {
              var modal = document.getElementById("jmApplyModal");
              if (modal) {
                modal.hidden = false;
              } else if (payload.redirect_url) {
                window.location.href = payload.redirect_url;
              }
              form.querySelector("button")?.setAttribute("disabled", "disabled");
            } else if (payload.code === "RESUME_REQUIRED") {
              showResumeRequiredModal();
            } else if (payload.message || payload.error) {
              notify("error", payload.message || payload.error);
            }
          })
          .catch(function () {
            form.submit();
          });
      });
    });
  }

  function initShareButtons() {
    var modal = document.getElementById("jmShareModal");
    if (!modal) return;

    var logoImg = document.getElementById("jmShareLogoImg");
    var logoInitial = document.getElementById("jmShareLogoInitial");
    var titleEl = document.getElementById("jmShareJobTitle");
    var companyEl = document.getElementById("jmShareCompany");
    var locationEl = document.getElementById("jmShareLocation");
    var typeEl = document.getElementById("jmShareType");

    var btnWhatsApp = document.getElementById("jmShareWhatsApp");
    var btnCopy = document.getElementById("jmShareCopy");
    var btnLinkedIn = document.getElementById("jmShareLinkedIn");
    var btnTwitter = document.getElementById("jmShareTwitter");
    var btnFacebook = document.getElementById("jmShareFacebook");
    var btnTelegram = document.getElementById("jmShareTelegram");

    document.querySelectorAll(".jm-share-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var urlPath = btn.getAttribute("data-share-url") || window.location.pathname;
        var fullUrl = window.location.origin + urlPath;
        var title = btn.getAttribute("data-share-title") || document.title;
        var company = btn.getAttribute("data-share-company") || "";
        var domain = btn.getAttribute("data-share-domain") || "";
        var location = btn.getAttribute("data-share-location") || "";
        var type = btn.getAttribute("data-share-type") || "";
        var logoUrl = btn.getAttribute("data-share-logo");
        var initial = btn.getAttribute("data-share-initial");

        // Populate Modal Info
        titleEl.textContent = title;
        companyEl.textContent = company;
        locationEl.innerHTML = '<i class="bi bi-geo-alt"></i> ' + location;
        typeEl.textContent = type;

        if (logoUrl) {
          logoImg.src = logoUrl;
          logoImg.style.display = "block";
          logoInitial.style.display = "none";
        } else {
          logoImg.style.display = "none";
          logoInitial.textContent = initial || company.charAt(0);
          logoInitial.style.display = "grid";
        }

        // Generate WhatsApp Message
        var waMsg = "";
        if (domain.toLowerCase().includes("faculty")) {
          waMsg = "📚 Faculty Opportunity!\n🏫 Institution: " + company + "\n👨‍🏫 Position: " + title + "\n📍 Location: " + location + "\n\nApply here:\n" + fullUrl + "\n\nShared via EduNaukri";
        } else {
          waMsg = "🚀 New Job Opportunity!\n📌 Position: " + title + "\n🏢 Company: " + company + "\n📍 Location: " + location + "\n💼 Employment Type: " + type + "\n\nApply here:\n" + fullUrl + "\n\nShared via EduNaukri";
        }

        // Attach Event Listeners (using cloneNode to remove previous listeners if necessary, but assigning onclick is easier)
        btnWhatsApp.onclick = function() {
          window.open("https://api.whatsapp.com/send?text=" + encodeURIComponent(waMsg), "_blank");
        };
        btnCopy.onclick = function() {
          if (navigator.clipboard) {
            navigator.clipboard.writeText(fullUrl).then(function() {
              notify("success", "Job link copied successfully.");
            });
          }
        };
        btnLinkedIn.href = "https://www.linkedin.com/sharing/share-offsite/?url=" + encodeURIComponent(fullUrl);
        btnTwitter.href = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(title) + "&url=" + encodeURIComponent(fullUrl);
        btnFacebook.href = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(fullUrl);
        btnTelegram.href = "https://t.me/share/url?url=" + encodeURIComponent(fullUrl) + "&text=" + encodeURIComponent(title);

        // Show Modal
        modal.hidden = false;
      });
    });
  }

  function initRecentSearches() {
    var form = document.getElementById("jmSearchForm");
    var input = document.getElementById("jmSearchInput");
    if (!form || !input || !window.localStorage) return;
    var key = "edunaukri_recent_job_searches";
    form.addEventListener("submit", function () {
      var q = input.value.trim();
      if (!q) return;
      try {
        var items = JSON.parse(localStorage.getItem(key) || "[]");
        items = [q].concat(items.filter(function (item) {
          return item !== q;
        })).slice(0, 5);
        localStorage.setItem(key, JSON.stringify(items));
      } catch (e) {}
    });
  }

  function escapeAttr(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFilterToggle();
    initSuggest();
    initSaveForms();
    initApplyForms();
    initShareButtons();
    initRecentSearches();
  });
})();
