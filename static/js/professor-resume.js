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

  function cfg() {
    return window.JSD_RESUME || {};
  }

  function getCsrfToken() {
    if (cfg().csrfToken) return cfg().csrfToken;
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function notify(type, message) {
    if (window.EduNotify && typeof window.EduNotify.toast === "function") {
      window.EduNotify.toast(type, message);
    }
  }

  function confirmAction(options) {
    if (!window.EduNotify || typeof window.EduNotify.confirm !== "function") {
      return Promise.resolve(false);
    }
    return window.EduNotify.confirm(options);
  }

  function root() {
    return document.getElementById("jsdResumePage");
  }

  function urls() {
    var el = root();
    return {
      upload: el ? el.getAttribute("data-upload-url") : "",
      delete: el ? el.getAttribute("data-delete-url") : "",
      autofill: el ? el.getAttribute("data-autofill-url") : "",
      portal: el ? el.getAttribute("data-portal-api-url") : "",
    };
  }

  function validateResumeFile(file) {
    var ext = file.name.indexOf(".") >= 0 ? file.name.split(".").pop().toLowerCase() : "";
    if (!ALLOWED_EXT[ext]) return "Only PDF and DOCX resume files are allowed.";
    if (file.size > MAX_BYTES) return "Resume size cannot exceed 5 MB.";
    if (file.size <= 0) return "The selected file is empty.";
    var mime = (file.type || "").toLowerCase();
    if (mime && !ALLOWED_MIME[mime]) return "Invalid resume file type. Upload a PDF or DOCX file.";
    return "";
  }

  function showError(message) {
    var el = document.getElementById("jsdResumeError");
    if (!el) return;
    el.textContent = message;
    el.hidden = !message;
  }

  function showSelected(name) {
    var el = document.getElementById("jsdResumeSelected");
    if (!el) return;
    el.textContent = name ? "Selected: " + name : "";
    el.hidden = !name;
  }

  function setProgress(pct, visible) {
    var wrap = document.getElementById("jsdResumeProgress");
    var bar = document.getElementById("jsdResumeProgressBar");
    var text = document.getElementById("jsdResumeProgressText");
    if (!wrap || !bar) return;
    wrap.hidden = !visible;
    bar.style.width = Math.min(100, Math.max(0, pct)) + "%";
    if (text) text.textContent = visible ? (pct >= 100 ? "Processing…" : "Uploading… " + pct + "%") : "";
  }

  function uploadResume(file) {
    var url = urls().upload;
    if (!url) return;
    uploading = true;
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
      setProgress(Math.round((e.loaded / e.total) * 100), true);
    });
    xhr.addEventListener("load", function () {
      uploading = false;
      setProgress(100, false);
      var payload;
      try {
        payload = JSON.parse(xhr.responseText || "{}");
      } catch (err) {
        showError("Unable to upload your resume. Please try again.");
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300 && payload.success) {
        notify("success", "Resume uploaded successfully.");
        window.setTimeout(function () {
          window.location.reload();
        }, 900);
        return;
      }
      showError((payload && payload.error) || "Unable to upload your resume. Please try again.");
    });
    xhr.addEventListener("error", function () {
      uploading = false;
      setProgress(0, false);
      showError("Network error. Please check your connection and try again.");
    });
    xhr.send(fd);
  }

  function deleteResume() {
    var url = urls().delete;
    if (!url) return;
    fetch(url, {
      method: "DELETE",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (payload) {
        if (!payload.success) throw new Error(payload.error || "Unable to delete resume.");
        notify("success", "Resume removed successfully.");
        window.setTimeout(function () {
          window.location.reload();
        }, 700);
      })
      .catch(function (err) {
        notify("error", err.message);
      });
  }

  function handleFile(file) {
    showError("");
    var validation = validateResumeFile(file);
    if (validation) {
      showError(validation);
      return;
    }
    showSelected(file.name);
    uploadResume(file);
  }

  function initScoreRing() {
    document.querySelectorAll(".jsd-res-score-ring").forEach(function (el) {
      var score = parseInt(el.getAttribute("data-score") || "0", 10);
      el.style.setProperty("--score", String(Math.min(100, Math.max(0, score))));
    });
  }

  function initUpload() {
    var input = document.getElementById("jsdResumeInput");
    var uploadBtn = document.getElementById("jsdResumeUploadBtn");
    var replaceBtn = document.getElementById("jsdResumeReplaceBtn");
    var deleteBtn = document.getElementById("jsdResumeDeleteBtn");
    var dropzone = document.getElementById("jsdResumeDropzone");

    function openPicker() {
      if (uploading || !input) return;
      showError("");
      input.click();
    }

    if (uploadBtn) uploadBtn.addEventListener("click", openPicker);
    if (replaceBtn) replaceBtn.addEventListener("click", openPicker);

    if (input) {
      input.addEventListener("change", function () {
        var file = input.files && input.files[0];
        input.value = "";
        if (file) handleFile(file);
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", async function () {
        if (uploading) return;
        var ask = await confirmAction({
          title: "Delete Resume",
          message: "Remove your resume? This action cannot be undone.",
          confirmText: "Delete Resume",
          cancelText: "Cancel",
          variant: "danger",
        });
        if (!ask) return;
        deleteResume();
      });
    }

    if (dropzone) {
      dropzone.addEventListener("click", function (e) {
        if (e.target.closest("button")) return;
        openPicker();
      });
      dropzone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropzone.classList.add("is-dragover");
      });
      dropzone.addEventListener("dragleave", function () {
        dropzone.classList.remove("is-dragover");
      });
      dropzone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropzone.classList.remove("is-dragover");
        var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
        if (file) handleFile(file);
      });
    }
  }

  function initAutofill() {
    var btn = document.getElementById("jsdResumeAutofillBtn");
    if (!btn) return;
    btn.addEventListener("click", async function () {
      var ok = await confirmAction({
        title: "Apply Parsed Resume Data",
        message: "Apply parsed resume data to your profile?",
        confirmText: "Apply Data",
        cancelText: "Cancel",
        variant: "info",
      });
      if (!ok) return;
      btn.disabled = true;
      var body = new FormData();
      fetch(urls().autofill, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: body,
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (payload) {
          if (!payload.success) throw new Error(payload.error || "Unable to apply resume data.");
          notify("success", payload.message || "Profile updated from resume.");
          window.setTimeout(function () {
            window.location.reload();
          }, 800);
        })
        .catch(function (err) {
          notify("error", err.message);
          btn.disabled = false;
        });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initScoreRing();
    initUpload();
    initAutofill();
  });
})();
