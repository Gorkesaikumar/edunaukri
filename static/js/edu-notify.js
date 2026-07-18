/**
 * EduNaukri global dialog + toast system.
 * Native browser dialogs are intentionally not used.
 */
(function () {
  "use strict";

  var ICONS = {
    success: "bi-check-circle-fill",
    error: "bi-x-octagon-fill",
    warning: "bi-exclamation-triangle-fill",
    info: "bi-info-circle-fill",
    question: "bi-patch-question-fill",
    danger: "bi-trash3-fill",
  };

  var DEFAULT_DURATION = {
    success: 2800,
    error: 4600,
    warning: 3800,
    info: 3200,
  };

  var recentKeys = {};
  var toastHost = null;
  var dialogHost = null;
  var activeDialog = null;
  var pendingResolve = null;
  var lastFocused = null;

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function ensureToastHost() {
    if (toastHost) return toastHost;
    toastHost = document.getElementById("eduNotifyHost");
    if (!toastHost) {
      toastHost = document.createElement("div");
      toastHost.id = "eduNotifyHost";
      toastHost.className = "edu-notify-host";
      toastHost.setAttribute("aria-live", "polite");
      toastHost.setAttribute("aria-atomic", "false");
      document.body.appendChild(toastHost);
    }
    return toastHost;
  }

  function ensureDialogHost() {
    if (dialogHost) return dialogHost;
    dialogHost = document.getElementById("eduDialogHost");
    if (!dialogHost) {
      dialogHost = document.createElement("div");
      dialogHost.id = "eduDialogHost";
      dialogHost.className = "edu-dialog-host";
      dialogHost.hidden = true;
      dialogHost.innerHTML =
        '<div class="edu-dialog-backdrop" data-edu-dialog-backdrop></div>' +
        '<section class="edu-dialog" role="dialog" aria-modal="true" aria-labelledby="eduDialogTitle" aria-describedby="eduDialogMessage">' +
        '<button type="button" class="edu-dialog__close" aria-label="Close" data-edu-dialog-close>&times;</button>' +
        '<div class="edu-dialog__icon-wrap edu-dialog__icon-wrap--info" id="eduDialogIconWrap">' +
        '<i class="bi ' +
        ICONS.info +
        '" id="eduDialogIcon" aria-hidden="true"></i>' +
        "</div>" +
        '<h2 class="edu-dialog__title" id="eduDialogTitle">Confirm action</h2>' +
        '<p class="edu-dialog__message" id="eduDialogMessage">Are you sure you want to continue?</p>' +
        '<div class="edu-dialog__input-wrap" id="eduDialogInputWrap" hidden>' +
        '<label class="visually-hidden" for="eduDialogInput">Input</label>' +
        '<input id="eduDialogInput" class="edu-dialog__input" type="text" autocomplete="off" />' +
        "</div>" +
        '<div class="edu-dialog__actions">' +
        '<button type="button" class="edu-btn edu-btn--ghost" id="eduDialogCancel">Cancel</button>' +
        '<button type="button" class="edu-btn edu-btn--primary" id="eduDialogOk">Confirm</button>' +
        "</div>" +
        "</section>";
      document.body.appendChild(dialogHost);
    }

    dialogHost.addEventListener("click", function (event) {
      if (event.target && event.target.hasAttribute("data-edu-dialog-backdrop")) {
        closeDialog({ confirmed: false, value: null });
      }
      if (event.target && event.target.hasAttribute("data-edu-dialog-close")) {
        closeDialog({ confirmed: false, value: null });
      }
    });

    document.getElementById("eduDialogCancel").addEventListener("click", function () {
      closeDialog({ confirmed: false, value: null });
    });

    document.getElementById("eduDialogOk").addEventListener("click", function () {
      var input = document.getElementById("eduDialogInput");
      closeDialog({ confirmed: true, value: input ? input.value : null });
    });

    return dialogHost;
  }

  function isDuplicate(key) {
    if (!key) return false;
    var now = Date.now();
    if (recentKeys[key] && now - recentKeys[key] < 600) return true;
    recentKeys[key] = now;
    return false;
  }

  function normalizeToastOptions(type, message, options) {
    if (typeof message === "object" && message !== null) {
      options = message;
      message = options.message || "";
    }
    options = options || {};
    return {
      type: type || options.type || "info",
      message: message,
      title: options.title || "",
      duration: options.duration != null ? options.duration : DEFAULT_DURATION[type] || 3000,
      actionLabel: options.actionLabel || options.actionText || "",
      onAction: options.onAction || null,
      dedupeKey: options.dedupeKey || type + ":" + message,
    };
  }

  function toast(type, message, options) {
    var opts = normalizeToastOptions(type, message, options);
    if (!opts.message) return null;
    if (isDuplicate(opts.dedupeKey)) return null;

    var host = ensureToastHost();
    var node = document.createElement("div");
    node.className = "edu-notify edu-notify--" + opts.type;
    node.setAttribute("role", opts.type === "error" ? "alert" : "status");

    var titleHtml = opts.title
      ? '<p class="edu-notify__title">' + escapeHtml(opts.title) + "</p>"
      : "";

    var actionHtml = "";
    if (opts.actionLabel && typeof opts.onAction === "function") {
      actionHtml =
        '<div class="edu-notify__actions">' +
        '<button type="button" class="edu-notify__action">' +
        escapeHtml(opts.actionLabel) +
        "</button></div>";
    }

    node.innerHTML =
      '<button type="button" class="edu-notify__close" aria-label="Dismiss">&times;</button>' +
      '<span class="edu-notify__icon"><i class="bi ' +
      (ICONS[opts.type] || ICONS.info) +
      '" aria-hidden="true"></i></span>' +
      '<div class="edu-notify__body">' +
      titleHtml +
      '<p class="edu-notify__text">' +
      escapeHtml(opts.message) +
      "</p>" +
      actionHtml +
      "</div>" +
      '<span class="edu-notify__progress"></span>';

    function dismiss() {
      if (!node.parentNode) return;
      node.classList.add("edu-notify--hide");
      window.setTimeout(function () {
        node.remove();
      }, 240);
    }

    node.querySelector(".edu-notify__close").addEventListener("click", dismiss);

    var actionBtn = node.querySelector(".edu-notify__action");
    if (actionBtn) {
      actionBtn.addEventListener("click", function () {
        opts.onAction();
        dismiss();
      });
    }

    host.appendChild(node);

    if (opts.duration > 0) {
      node.style.setProperty("--edu-notify-duration", opts.duration + "ms");
      window.setTimeout(dismiss, opts.duration);
    } else {
      node.querySelector(".edu-notify__progress").hidden = true;
    }

    return node;
  }

  function openDialog(config) {
    ensureDialogHost();
    if (pendingResolve) {
      pendingResolve({ confirmed: false, value: null });
      pendingResolve = null;
    }

    activeDialog = config || {};
    lastFocused = document.activeElement;

    var title = document.getElementById("eduDialogTitle");
    var message = document.getElementById("eduDialogMessage");
    var cancelBtn = document.getElementById("eduDialogCancel");
    var okBtn = document.getElementById("eduDialogOk");
    var iconWrap = document.getElementById("eduDialogIconWrap");
    var icon = document.getElementById("eduDialogIcon");
    var inputWrap = document.getElementById("eduDialogInputWrap");
    var input = document.getElementById("eduDialogInput");

    var variant = activeDialog.variant || "info";
    var iconName = activeDialog.icon || ICONS[variant] || ICONS.question;
    var mode = activeDialog.mode || "confirm";

    title.textContent = activeDialog.title || "Confirm action";
    message.textContent = activeDialog.message || "Are you sure you want to continue?";
    cancelBtn.textContent = activeDialog.cancelText || "Cancel";
    okBtn.textContent = activeDialog.confirmText || "Confirm";

    iconWrap.className = "edu-dialog__icon-wrap edu-dialog__icon-wrap--" + variant;
    icon.className = "bi " + iconName;

    okBtn.className =
      "edu-btn " +
      (variant === "danger" ? "edu-btn--danger" : variant === "warning" ? "edu-btn--warning" : "edu-btn--primary");

    if (mode === "alert") {
      cancelBtn.hidden = true;
      okBtn.textContent = activeDialog.confirmText || "Close";
    } else {
      cancelBtn.hidden = false;
    }

    if (mode === "prompt") {
      inputWrap.hidden = false;
      input.value = activeDialog.defaultValue || "";
      input.placeholder = activeDialog.placeholder || "";
    } else {
      inputWrap.hidden = true;
      input.value = "";
    }

    document.body.classList.add("edu-dialog-open");
    dialogHost.hidden = false;
    window.requestAnimationFrame(function () {
      dialogHost.classList.add("is-open");
      if (mode === "prompt") input.focus();
      else okBtn.focus();
    });

    return new Promise(function (resolve) {
      pendingResolve = resolve;
    });
  }

  function closeDialog(result) {
    if (!dialogHost || dialogHost.hidden) return;
    var out = result || { confirmed: false, value: null };
    dialogHost.classList.remove("is-open");
    window.setTimeout(function () {
      dialogHost.hidden = true;
      document.body.classList.remove("edu-dialog-open");
      if (lastFocused && typeof lastFocused.focus === "function") lastFocused.focus();
    }, 140);
    if (pendingResolve) {
      var resolve = pendingResolve;
      pendingResolve = null;
      resolve(out);
    }
  }

  function trapDialogKeys(event) {
    if (!activeDialog || !dialogHost || dialogHost.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeDialog({ confirmed: false, value: null });
      return;
    }
    if (event.key === "Enter") {
      if (event.target && event.target.id === "eduDialogInput" && activeDialog.mode === "prompt") {
        event.preventDefault();
        closeDialog({ confirmed: true, value: event.target.value });
        return;
      }
      if (event.target && event.target.id !== "eduDialogCancel") {
        event.preventDefault();
        var input = document.getElementById("eduDialogInput");
        closeDialog({ confirmed: true, value: input ? input.value : null });
        return;
      }
    }
    if (event.key === "Tab") {
      var focusable = dialogHost.querySelectorAll("button:not([hidden]), input:not([hidden])");
      if (!focusable.length) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  function openConfirmationDialog(options) {
    options = options || {};
    return openDialog({
      mode: "confirm",
      title: options.title || "Confirm action",
      message: options.message || "Are you sure you want to continue?",
      confirmText: options.confirmText || options.confirmLabel || "Confirm",
      cancelText: options.cancelText || options.cancelLabel || "Cancel",
      variant: options.variant || "info",
      icon: options.icon,
    }).then(function (res) {
      return !!(res && res.confirmed);
    });
  }

  function openPromptDialog(options) {
    options = options || {};
    return openDialog({
      mode: "prompt",
      title: options.title || "Provide a value",
      message: options.message || "Enter a value to continue.",
      confirmText: options.confirmText || "Continue",
      cancelText: options.cancelText || "Cancel",
      variant: options.variant || "info",
      icon: options.icon || ICONS.question,
      placeholder: options.placeholder || "",
      defaultValue: options.defaultValue || "",
    }).then(function (res) {
      if (!res || !res.confirmed) return null;
      return res.value;
    });
  }

  function showDialog(type, options) {
    options = options || {};
    var variant = options.variant || (type === "error" ? "danger" : type);
    return openDialog({
      mode: "alert",
      title: options.title || (type === "error" ? "Something went wrong" : "Notice"),
      message: options.message || "",
      confirmText: options.confirmText || "Close",
      variant: variant,
      icon: options.icon || ICONS[type] || ICONS.info,
    }).then(function () {
      return true;
    });
  }

  function bindConfirmForms() {
    document.addEventListener("submit", function (event) {
      var form = event.target;
      if (!form || !form.hasAttribute("data-edu-confirm")) return;
      if (form.dataset.eduConfirmApproved === "1") {
        form.dataset.eduConfirmApproved = "";
        return;
      }
      event.preventDefault();
      openConfirmationDialog({
        title: form.getAttribute("data-edu-confirm-title") || "Please confirm",
        message: form.getAttribute("data-edu-confirm-message") || "Are you sure you want to continue?",
        confirmText: form.getAttribute("data-edu-confirm-button") || "Confirm",
        cancelText: form.getAttribute("data-edu-cancel-button") || "Cancel",
        variant: form.getAttribute("data-edu-confirm-variant") || "warning",
        icon: form.getAttribute("data-edu-confirm-icon") || ICONS.warning,
      }).then(function (ok) {
        if (!ok) return;
        form.dataset.eduConfirmApproved = "1";
        form.requestSubmit();
      });
    });
  }

  var EduNotify = {
    toast: toast,
    show: function (options) {
      options = options || {};
      return toast(options.type || "info", options.message || "", options);
    },
    success: function (message, options) {
      return toast("success", message, options);
    },
    error: function (message, options) {
      return toast("error", message, options);
    },
    warning: function (message, options) {
      return toast("warning", message, options);
    },
    info: function (message, options) {
      return toast("info", message, options);
    },
    ask: openConfirmationDialog,
    input: openPromptDialog,
    confirm: openConfirmationDialog,
    prompt: openPromptDialog,
    dialog: showDialog,
    successDialog: function (options) {
      return showDialog("success", options);
    },
    warningDialog: function (options) {
      return showDialog("warning", options);
    },
    errorDialog: function (options) {
      return showDialog("error", options);
    },
    infoDialog: function (options) {
      return showDialog("info", options);
    },
  };

  window.EduNotify = EduNotify;
  window.showToast = function (message, isError) {
    if (isError) EduNotify.error(message);
    else EduNotify.success(message);
  };

  document.addEventListener("keydown", trapDialogKeys);
  bindConfirmForms();
})();
