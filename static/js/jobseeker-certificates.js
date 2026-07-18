(function () {
  "use strict";

  var MAX_BYTES = 5 * 1024 * 1024;
  var ALLOWED_EXT = { pdf: true, jpg: true, jpeg: true, png: true };
  var ALLOWED_MIME = {
    "application/pdf": true,
    "application/x-pdf": true,
    "image/jpeg": true,
    "image/png": true,
  };

  var uploading = false;
  var pendingDeleteUrl = "";
  var uploadModal;
  var editModal;
  var previewModal;
  var deleteModal;

  function cfg() {
    return window.JSD_CERTIFICATES || {};
  }

  function pageRoot() {
    return document.getElementById("jsdCertPage");
  }

  function uploadUrl() {
    var root = pageRoot();
    return root ? root.getAttribute("data-upload-url") : "";
  }

  function getCsrfToken() {
    if (cfg().csrfToken) return cfg().csrfToken;
    var root = pageRoot();
    if (root && root.getAttribute("data-csrf")) return root.getAttribute("data-csrf");
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function notify(type, message) {
    if (window.EduNotify && typeof window.EduNotify.toast === "function") {
      window.EduNotify.toast(type, message);
    }
  }

  function validateFile(file) {
    if (!file) return "Please select a certificate file.";
    var ext = file.name.indexOf(".") >= 0 ? file.name.split(".").pop().toLowerCase() : "";
    if (!ALLOWED_EXT[ext]) return "Only PDF, JPG, JPEG, and PNG certificate files are allowed.";
    if (file.size > MAX_BYTES) return "Certificate size cannot exceed 5 MB.";
    if (file.size <= 0) return "The selected file is empty.";
    var mime = (file.type || "").toLowerCase();
    if (mime && !ALLOWED_MIME[mime]) return "Invalid certificate file type.";
    return "";
  }

  function showUploadError(message) {
    var el = document.getElementById("jsdCertUploadError");
    if (!el) return;
    el.textContent = message || "";
    el.hidden = !message;
  }

  function showEditError(message) {
    var el = document.getElementById("jsdCertEditError");
    if (!el) return;
    el.textContent = message || "";
    el.hidden = !message;
  }

  function setProgress(visible, pct) {
    var wrap = document.getElementById("jsdCertProgress");
    var bar = document.getElementById("jsdCertProgressBar");
    if (!wrap || !bar) return;
    wrap.hidden = !visible;
    bar.style.width = (pct || 0) + "%";
  }

  function xhrUpload(url, formData, onProgress) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", url, true);
      xhr.setRequestHeader("X-CSRFToken", getCsrfToken());
      xhr.upload.onprogress = function (ev) {
        if (ev.lengthComputable && onProgress) onProgress(Math.round((ev.loaded / ev.total) * 100));
      };
      xhr.onload = function () {
        var body = {};
        try {
          body = JSON.parse(xhr.responseText || "{}");
        } catch (e) {
          body = {};
        }
        if (xhr.status >= 200 && xhr.status < 300 && body.success) resolve(body);
        else reject(new Error(body.error || "Upload failed. Please try again."));
      };
      xhr.onerror = function () {
        reject(new Error("Network error. Please try again."));
      };
      xhr.send(formData);
    });
  }

  function xhrPatch(url, formData) {
    return fetch(url, {
      method: "PATCH",
      headers: { "X-CSRFToken": getCsrfToken() },
      body: formData,
    }).then(function (res) {
      return res.json().then(function (body) {
        if (!res.ok || !body.success) throw new Error(body.error || "Update failed.");
        return body;
      });
    });
  }

  function xhrDelete(url) {
    return fetch(url, {
      method: "DELETE",
      headers: { "X-CSRFToken": getCsrfToken() },
    }).then(function (res) {
      return res.json().then(function (body) {
        if (!res.ok || !body.success) throw new Error(body.error || "Delete failed.");
        return body;
      });
    });
  }

  function openUploadModal() {
    if (!uploadModal) uploadModal = new bootstrap.Modal(document.getElementById("jsdCertUploadModal"));
    document.getElementById("jsdCertUploadForm").reset();
    document.getElementById("jsdCertSelected").hidden = true;
    showUploadError("");
    setProgress(false, 0);
    uploadModal.show();
  }

  function handleSelectedFile(file) {
    var err = validateFile(file);
    if (err) {
      showUploadError(err);
      return;
    }
    showUploadError("");
    var sel = document.getElementById("jsdCertSelected");
    sel.textContent = file.name + " (" + (file.size / 1024 / 1024).toFixed(2) + " MB)";
    sel.hidden = false;
    document.getElementById("jsdCertFileInput")._selectedFile = file;
  }

  function bindDropzone() {
    var dropzone = document.getElementById("jsdCertDropzone");
    var input = document.getElementById("jsdCertFileInput");
    var choose = document.getElementById("jsdCertChooseBtn");
    if (!dropzone || !input) return;

    choose.addEventListener("click", function () {
      input.click();
    });
    input.addEventListener("change", function () {
      if (input.files && input.files[0]) handleSelectedFile(input.files[0]);
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
      if (e.dataTransfer.files && e.dataTransfer.files[0]) handleSelectedFile(e.dataTransfer.files[0]);
    });
    dropzone.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });
  }

  function bindUploadForm() {
    var form = document.getElementById("jsdCertUploadForm");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (uploading) return;
      var input = document.getElementById("jsdCertFileInput");
      var file = (input._selectedFile || (input.files && input.files[0]));
      var err = validateFile(file);
      var name = (document.getElementById("jsdCertName").value || "").trim();
      if (!name) {
        showUploadError("Certificate name is required.");
        return;
      }
      if (err) {
        showUploadError(err);
        return;
      }
      var fd = new FormData(form);
      fd.set("file", file);
      uploading = true;
      setProgress(true, 0);
      showUploadError("");
      xhrUpload(uploadUrl(), fd, setProgress)
        .then(function (body) {
          notify("success", body.message || "Certificate uploaded successfully.");
          window.location.reload();
        })
        .catch(function (ex) {
          showUploadError(ex.message);
          notify("error", ex.message);
        })
        .finally(function () {
          uploading = false;
          setProgress(false, 0);
        });
    });
  }

  function bindCardActions() {
    document.addEventListener("click", function (e) {
      var viewBtn = e.target.closest(".jsd-cert-view");
      if (viewBtn) {
        openPreview(viewBtn);
        return;
      }
      var editBtn = e.target.closest(".jsd-cert-edit");
      if (editBtn) {
        openEdit(editBtn);
        return;
      }
      var delBtn = e.target.closest(".jsd-cert-delete");
      if (delBtn) {
        openDelete(delBtn);
      }
    });
  }

  function openPreview(btn) {
    if (!previewModal) previewModal = new bootstrap.Modal(document.getElementById("jsdCertPreviewModal"));
    var url = btn.getAttribute("data-preview-url");
    var isPdf = btn.getAttribute("data-is-pdf") === "1";
    var isImage = btn.getAttribute("data-is-image") === "1";
    var title = btn.getAttribute("data-title") || "Certificate";
    document.getElementById("jsdCertPreviewTitle").textContent = title;
    var frame = document.getElementById("jsdCertPreviewFrame");
    var img = document.getElementById("jsdCertPreviewImg");
    frame.hidden = !isPdf;
    img.hidden = !isImage;
    if (isPdf) {
      frame.src = url;
      img.removeAttribute("src");
    } else if (isImage) {
      img.src = url;
      frame.removeAttribute("src");
    }
    previewModal.show();
  }

  function openEdit(btn) {
    if (!editModal) editModal = new bootstrap.Modal(document.getElementById("jsdCertEditModal"));
    document.getElementById("jsdCertEditId").value = btn.getAttribute("data-id");
    document.getElementById("jsdCertEditName").value = btn.getAttribute("data-name") || "";
    document.getElementById("jsdCertEditOrg").value = btn.getAttribute("data-org") || "";
    document.getElementById("jsdCertEditCategory").value = btn.getAttribute("data-category") || "other";
    document.getElementById("jsdCertEditIssue").value = btn.getAttribute("data-issue") || "";
    document.getElementById("jsdCertEditExpiry").value = btn.getAttribute("data-expiry") || "";
    document.getElementById("jsdCertEditCredentialId").value = btn.getAttribute("data-credential-id") || "";
    document.getElementById("jsdCertEditCredentialUrl").value = btn.getAttribute("data-credential-url") || "";
    document.getElementById("jsdCertReplaceInput").value = "";
    showEditError("");
    editModal.show();
    document.getElementById("jsdCertEditForm")._detailUrl = btn.getAttribute("data-detail-url");
  }

  function bindEditForm() {
    var form = document.getElementById("jsdCertEditForm");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var url = form._detailUrl;
      if (!url) return;
      var name = (document.getElementById("jsdCertEditName").value || "").trim();
      if (!name) {
        showEditError("Certificate name is required.");
        return;
      }
      var fd = new FormData();
      fd.append("name", name);
      fd.append("issuing_organization", document.getElementById("jsdCertEditOrg").value || "");
      fd.append("category", document.getElementById("jsdCertEditCategory").value || "other");
      fd.append("issue_date", document.getElementById("jsdCertEditIssue").value || "");
      fd.append("expiry_date", document.getElementById("jsdCertEditExpiry").value || "");
      fd.append("credential_id", document.getElementById("jsdCertEditCredentialId").value || "");
      fd.append("credential_url", document.getElementById("jsdCertEditCredentialUrl").value || "");
      var replaceInput = document.getElementById("jsdCertReplaceInput");
      if (replaceInput.files && replaceInput.files[0]) {
        var err = validateFile(replaceInput.files[0]);
        if (err) {
          showEditError(err);
          return;
        }
        fd.append("file", replaceInput.files[0]);
      }
      showEditError("");
      xhrPatch(url, fd)
        .then(function (body) {
          notify("success", body.message || "Certificate updated successfully.");
          window.location.reload();
        })
        .catch(function (ex) {
          showEditError(ex.message);
          notify("error", ex.message);
        });
    });
  }

  function openDelete(btn) {
    if (!deleteModal) deleteModal = new bootstrap.Modal(document.getElementById("jsdCertDeleteModal"));
    pendingDeleteUrl = btn.getAttribute("data-detail-url");
    document.getElementById("jsdCertDeleteName").textContent = btn.getAttribute("data-name") || "this certificate";
    deleteModal.show();
  }

  function bindDeleteConfirm() {
    var btn = document.getElementById("jsdCertConfirmDelete");
    if (!btn) return;
    btn.addEventListener("click", function () {
      if (!pendingDeleteUrl) return;
      xhrDelete(pendingDeleteUrl)
        .then(function (body) {
          if (deleteModal) deleteModal.hide();
          notify("success", body.message || "Certificate deleted successfully.");
          window.location.reload();
        })
        .catch(function (ex) {
          notify("error", ex.message);
        });
    });
  }

  function bindOpenButtons() {
    var open = document.getElementById("jsdCertOpenUpload");
    var empty = document.getElementById("jsdCertEmptyUpload");
    if (open) open.addEventListener("click", openUploadModal);
    if (empty) empty.addEventListener("click", openUploadModal);
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindDropzone();
    bindUploadForm();
    bindEditForm();
    bindCardActions();
    bindDeleteConfirm();
    bindOpenButtons();
    var previewEl = document.getElementById("jsdCertPreviewModal");
    if (previewEl) {
      previewEl.addEventListener("hidden.bs.modal", function () {
        document.getElementById("jsdCertPreviewFrame").removeAttribute("src");
        document.getElementById("jsdCertPreviewImg").removeAttribute("src");
      });
    }
  });
})();
