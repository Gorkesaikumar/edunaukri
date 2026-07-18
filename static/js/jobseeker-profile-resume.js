/**
 * Job Seeker Profile — resume upload (PDF/DOCX, max 5 MB)
 */
(function () {
  "use strict";

  var MAX_BYTES = 5 * 1024 * 1024;
  var ALLOWED_EXT = { pdf: true, docx: true };
  var ALLOWED_MIME = {
    "application/pdf": true,
    "application/x-pdf": true,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": true,
  };

  var uploading = false;
  var helpers = null;

  function init() {
    helpers = window.JSPHelpers;
    if (!helpers) return;

    var uploadBtn = document.getElementById("jspResumeUploadBtn");
    var fileInput = document.getElementById("jspResumeInput");
    var deleteBtn = document.getElementById("jspDeleteResume");

    if (uploadBtn && fileInput) {
      uploadBtn.addEventListener("click", function () {
        if (uploading) return;
        clearResumeError();
        fileInput.click();
      });

      fileInput.addEventListener("change", function () {
        var file = fileInput.files && fileInput.files[0];
        fileInput.value = "";
        if (!file) return;
        handleFileSelected(file);
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", function () {
        if (uploading) return;
        var ask = window.EduNotify
          ? window.EduNotify.confirm({
              title: "Delete Resume",
              message: "Remove your resume from your profile? The file will be permanently deleted.",
              confirmText: "Delete Resume",
              cancelText: "Cancel",
              variant: "danger",
              icon: "bi-trash3-fill",
            })
          : Promise.resolve(false);
        ask.then(function (ok) {
          if (!ok) return;
          deleteResume(deleteBtn);
        });
      });
    }
  }

  function urls() {
    var state = helpers.getState();
    return (state && state.api_urls) || {};
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute("content")) return meta.getAttribute("content");
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) return input.value;
    return "";
  }

  function handleFileSelected(file) {
    clearResumeError();
    var validation = validateResumeFile(file);
    if (validation) {
      showResumeError(validation);
      return;
    }

    showSelectedFile(file.name);
    uploadResume(file);
  }

  function validateResumeFile(file) {
    var name = file.name || "";
    var ext = name.indexOf(".") >= 0 ? name.split(".").pop().toLowerCase() : "";
    if (!ALLOWED_EXT[ext]) {
      return "Only PDF and DOCX resume files are allowed.";
    }
    if (file.size > MAX_BYTES) {
      return "Resume size cannot exceed 5 MB.";
    }
    if (file.size <= 0) {
      return "The selected file is empty.";
    }
    var mime = (file.type || "").toLowerCase();
    if (mime && !ALLOWED_MIME[mime]) {
      return "Invalid resume file type. Upload a PDF or DOCX file.";
    }
    return "";
  }

  function uploadResume(file) {
    var uploadBtn = document.getElementById("jspResumeUploadBtn");
    var url = urls().resume_upload;
    if (!url) return;

    uploading = true;
    if (uploadBtn) uploadBtn.disabled = true;
    setProgress(0, true);

    var fd = new FormData();
    fd.append("file", file);
    fd.append("resume", file);

    var xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);
    xhr.setRequestHeader("X-CSRFToken", getCsrfToken());
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

    xhr.upload.addEventListener("progress", function (e) {
      if (!e.lengthComputable) return;
      var pct = Math.round((e.loaded / e.total) * 100);
      setProgress(pct, true);
    });

    xhr.addEventListener("load", function () {
      uploading = false;
      if (uploadBtn) uploadBtn.disabled = false;
      setProgress(100, false);

      var payload;
      try {
        payload = JSON.parse(xhr.responseText || "{}");
      } catch (err) {
        showResumeError("Unable to upload your resume. Please try again.");
        return;
      }

      if (xhr.status >= 200 && xhr.status < 300 && payload.success) {
        helpers.showToast("Resume uploaded successfully.");
        window.setTimeout(function () {
          window.location.reload();
        }, 1200);
        return;
      }

      showResumeError(
        (payload && payload.error) || "Unable to upload your resume. Please try again."
      );
    });

    xhr.addEventListener("error", function () {
      uploading = false;
      if (uploadBtn) uploadBtn.disabled = false;
      setProgress(0, false);
      showResumeError("Network error. Please check your connection and try again.");
    });

    xhr.addEventListener("abort", function () {
      uploading = false;
      if (uploadBtn) uploadBtn.disabled = false;
      setProgress(0, false);
      showResumeError("Upload was cancelled.");
    });

    xhr.send(fd);
  }

  function deleteResume(btn) {
    helpers.setButtonLoading(btn, true);
    helpers
      .api("DELETE", urls().resume_upload)
      .then(function () {
        helpers.showToast("Resume removed successfully.");
        window.setTimeout(function () {
          window.location.reload();
        }, 900);
      })
      .catch(function (err) {
        helpers.showToast(
          (err && err.error) || "Unable to delete your resume. Please try again.",
          true
        );
      })
      .finally(function () {
        helpers.setButtonLoading(btn, false);
      });
  }

  function showSelectedFile(name) {
    var el = document.getElementById("jspResumeSelected");
    if (!el) return;
    el.textContent = "Selected: " + name;
    el.hidden = false;
  }

  function showResumeError(message) {
    var el = document.getElementById("jspResumeError");
    if (!el) return;
    el.textContent = message;
    el.hidden = false;
  }

  function clearResumeError() {
    var err = document.getElementById("jspResumeError");
    var sel = document.getElementById("jspResumeSelected");
    if (err) {
      err.textContent = "";
      err.hidden = true;
    }
    if (sel) {
      sel.textContent = "";
      sel.hidden = true;
    }
  }

  function setProgress(pct, visible) {
    var wrap = document.getElementById("jspResumeProgress");
    var bar = document.getElementById("jspResumeProgressBar");
    var text = document.getElementById("jspResumeProgressText");
    if (!wrap || !bar) return;
    wrap.hidden = !visible;
    bar.style.width = Math.min(100, Math.max(0, pct)) + "%";
    if (text) {
      text.textContent = visible ? (pct >= 100 ? "Processing…" : "Uploading… " + pct + "%") : "";
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
